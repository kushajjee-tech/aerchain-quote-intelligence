"""LLM gateway (architecture §7.1).

- Model `claude-opus-5-5`, adaptive thinking, and an **explicit effort on every route**
  (this model defaults to `medium`, so nothing relies on the default).
- Structured outputs via `messages.parse(output_format=<pydantic model>)`.
- Server-side refusal fallback (`fallbacks="default"`) is enabled by default.
- `stop_reason` is checked on every response: `refusal` / `max_tokens` raise; nothing is half-applied.
- Transport retries are the SDK's own (max 2), which resend the identical request body.
- Conversations are append-only: a turn is stored only after it succeeds.
- Every call is logged to `llm_call` (route, model, effort, input hash, summary, tokens, latency,
  stop reason, status).
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, TypeVar

import anthropic
import pydantic
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import LlmCall
from app.llm.conversation import ConversationStore

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"

# Explicit effort per route (architecture §7.1). Unknown routes are rejected.
ROUTE_EFFORT: dict[str, str] = {
    "extract_text": "high",
    "extract_ocr": "high",
    "extract_vision": "high",
    "match": "high",
    "copilot": "medium",
    "copilot_mapping": "medium",
    "analyst": "medium",
    "memo": "medium",
    "smoke": "low",
}


class LLMError(RuntimeError):
    """Base class: the stage must be marked FAILED (PRD AI-10)."""


class LLMRefusal(LLMError):
    pass


class LLMTruncated(LLMError):
    pass


class LLMSchemaError(LLMError):
    pass


class LLMUnavailable(LLMError):
    """No credentials or no model access: reported, never a crash (the seeded fallback stays usable)."""


class LLMTransportError(LLMError):
    pass


def _sha256(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _summary(system: str | None, messages: list[dict[str, Any]], limit: int = 2000) -> str:
    """Plain-text summary of what was sent (used by request-inspection tests, e.g. DL-11)."""
    parts: list[str] = []
    if system:
        parts.append(f"[system] {system}")
    for m in messages:
        content = m["content"]
        if isinstance(content, str):
            parts.append(f"[{m['role']}] {content}")
            continue
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(f"[{m['role']}] {block.get('text', '')}")
                else:
                    parts.append(f"[{m['role']}] <{block.get('type')}>")
    text = "\n".join(parts)
    return text if len(text) <= limit else text[:limit] + "…"


@dataclass
class TurnResult:
    content: list[dict[str, Any]]
    stop_reason: str | None
    assistant_seq: int


NON_STREAMING_MAX = 21000  # above this max_tokens, structured calls stream


class LLMGateway:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        client: anthropic.Anthropic | None = None,
        model: str = DEFAULT_MODEL,
        use_fallbacks: bool = True,
        max_retries: int = 2,
    ):
        self._sf = session_factory
        self._client = client or anthropic.Anthropic(max_retries=max_retries)
        self.model = model
        self.use_fallbacks = use_fallbacks
        self.conversations = ConversationStore(session_factory)

    # -- helpers ----------------------------------------------------------------------------
    def _effort(self, route: str) -> str:
        if route not in ROUTE_EFFORT:
            raise ValueError(f"unknown LLM route '{route}' (effort must be explicit per route)")
        return ROUTE_EFFORT[route]

    def _log(self, **fields: Any) -> None:
        with self._sf.begin() as s:
            s.add(LlmCall(**fields))

    @staticmethod
    def _check_stop(resp: Any) -> None:
        if resp.stop_reason == "refusal":
            category = getattr(getattr(resp, "stop_details", None), "category", None)
            raise LLMRefusal(f"model refused (category={category})")
        if resp.stop_reason == "max_tokens":
            raise LLMTruncated("response truncated at max_tokens")

    def _call(self, kind: str, kwargs: dict[str, Any]) -> Any:
        target = self._client.beta.messages if self.use_fallbacks else self._client.messages
        if self.use_fallbacks:
            kwargs = {**kwargs, "betas": [FALLBACK_BETA], "fallbacks": "default"}
        try:
            if kind == "stream":  # large outputs must stream (SDK refuses long non-streaming requests)
                with target.stream(**kwargs) as stream:
                    return stream.get_final_message()
            return getattr(target, kind)(**kwargs)
        except TypeError as e:  # the SDK raises TypeError when no credentials are configured
            if "authentication" in str(e).lower():
                raise LLMUnavailable("model unavailable: no API credentials configured (set ANTHROPIC_API_KEY)") from e
            raise

    # -- single-shot structured call (extraction, mapping, matching) ------------------------
    def structured(
        self,
        route: str,
        schema: type[T],
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_tokens: int = 16000,
        prompt_version: str = "",
    ) -> T:
        effort = self._effort(route)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": effort},
            "output_format": schema,
        }
        if system:
            kwargs["system"] = system
        log = {
            "route": route, "model": self.model, "effort": effort, "prompt_version": prompt_version,
            "input_sha256": _sha256({"system": system, "messages": messages, "schema": schema.__name__}),
            "request_summary": _summary(system, messages),
        }
        t0 = time.monotonic()
        try:
            resp = self._call("stream" if max_tokens > NON_STREAMING_MAX else "parse", kwargs)
        except LLMUnavailable as e:
            self._log(**log, status="error", error=f"LLMUnavailable: {e}", latency_ms=0)
            raise
        except pydantic.ValidationError as e:  # the SDK parses inside the call: a cut-off or invalid reply lands here
            truncated = "EOF while parsing" in str(e)
            err = LLMTruncated("response cut off before the JSON was complete (raise max_tokens or split the call)") \
                if truncated else LLMSchemaError(f"reply did not match the schema: {str(e)[:300]}")
            self._log(**log, status="error", error=f"{type(err).__name__}: {err}",
                      latency_ms=int((time.monotonic() - t0) * 1000))
            raise err from e
        except anthropic.APIError as e:
            self._log(**log, status="error", error=f"{type(e).__name__}: {e}",
                      latency_ms=int((time.monotonic() - t0) * 1000))
            raise LLMTransportError(str(e)) from e
        usage = getattr(resp, "usage", None)
        base = {**log, "stop_reason": resp.stop_reason,
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                "latency_ms": int((time.monotonic() - t0) * 1000)}
        try:
            self._check_stop(resp)
            parsed = resp.parsed_output
            if parsed is None:
                raise LLMSchemaError("no schema-valid output")
        except LLMError as e:
            self._log(**base, status="error", error=f"{type(e).__name__}: {e}")
            raise
        self._log(**base, status="ok")
        return parsed

    # -- append-only conversation turn (co-pilot, analyst) -----------------------------------
    def converse(
        self,
        conversation_id: str,
        route: str,
        user_content: str | list[dict[str, Any]],
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 16000,
        prompt_version: str = "",
        extra_messages: list[dict[str, Any]] | None = None,
    ) -> TurnResult:
        """Run one turn. On success the user message (and any extra messages, e.g. a regeneration
        feedback message sent as a *user* turn after the rejected answer) and the exact assistant
        content are appended atomically. On failure nothing is appended."""
        effort = self._effort(route)
        history = self.conversations.history(conversation_id)
        new_msgs: list[dict[str, Any]] = list(extra_messages or [])
        new_msgs.append({"role": "user", "content": user_content})
        messages = history + new_msgs
        kwargs: dict[str, Any] = {
            "model": self.model, "max_tokens": max_tokens, "messages": messages,
            "thinking": {"type": "adaptive"}, "output_config": {"effort": effort},
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        log = {
            "route": route, "model": self.model, "effort": effort, "prompt_version": prompt_version,
            "input_sha256": _sha256({"system": system, "messages": messages}),
            "request_summary": _summary(system, new_msgs),
        }
        t0 = time.monotonic()
        try:
            resp = self._call("create", kwargs)
        except anthropic.APIError as e:
            self._log(**log, status="error", error=f"{type(e).__name__}: {e}",
                      latency_ms=int((time.monotonic() - t0) * 1000))
            raise LLMTransportError(str(e)) from e
        usage = getattr(resp, "usage", None)
        base = {**log, "stop_reason": resp.stop_reason,
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                "latency_ms": int((time.monotonic() - t0) * 1000)}
        try:
            self._check_stop(resp)
        except LLMError as e:
            self._log(**base, status="error", error=f"{type(e).__name__}: {e}")
            raise
        content = [block.to_dict() for block in resp.content]
        seqs = self.conversations.append(
            conversation_id, new_msgs + [{"role": "assistant", "content": content}]
        )
        self._log(**base, status="ok")
        return TurnResult(content=content, stop_reason=resp.stop_reason, assistant_seq=seqs[-1])
