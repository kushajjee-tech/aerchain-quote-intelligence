"""M0: LLM gateway behaviour against a mocked HTTP transport (no network, no API key needed)."""
from __future__ import annotations

import json

import anthropic
import httpx2 as httpx
import pytest
from pydantic import BaseModel

from app.db.models import LlmCall
from app.llm.gateway import (
    FALLBACK_BETA, LLMGateway, LLMRefusal, LLMTransportError, LLMTruncated,
)

THINKING = {"type": "thinking", "thinking": "", "signature": "c2lnbmF0dXJl"}


class Echo(BaseModel):
    vendor: str
    price: float


def _message(content, stop_reason="end_turn"):
    return {
        "id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
        "content": content, "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": 11, "output_tokens": 7},
    }


class Recorder:
    """httpx transport returning queued responses and recording request bodies."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status, body = self.responses.pop(0)
        headers = {"retry-after-ms": "1"} if status >= 500 or status == 429 else {}
        return httpx.Response(status, json=body, headers=headers)

    def bodies(self):
        return [json.loads(r.content) for r in self.requests]


def _gateway(session_factory, rec, max_retries=2, use_fallbacks=True):
    client = anthropic.Anthropic(
        api_key="test-key", max_retries=max_retries,
        http_client=httpx.Client(transport=httpx.MockTransport(rec)),
    )
    return LLMGateway(session_factory, client=client, use_fallbacks=use_fallbacks)


def _calls(sf):
    with sf() as s:
        return s.query(LlmCall).order_by(LlmCall.id).all()


def test_structured_call_shape_and_log(session_factory):
    rec = Recorder([(200, _message([THINKING, {"type": "text", "text": '{"vendor":"V5","price":42.0}'}]))])
    gw = _gateway(session_factory, rec)
    out = gw.structured("extract_text", Echo, [{"role": "user", "content": "₹42/kg"}], system="extract")
    assert out == Echo(vendor="V5", price=42.0)
    body = rec.bodies()[0]
    assert body["model"] == "claude-opus-5-5"
    assert body["thinking"] == {"type": "adaptive"}
    assert body["output_config"]["effort"] == "high"
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["fallbacks"] == "default"
    assert FALLBACK_BETA in rec.requests[0].headers.get("anthropic-beta", "")
    assert "temperature" not in body
    (call,) = _calls(session_factory)
    assert call.status == "ok" and call.route == "extract_text" and call.effort == "high"
    assert call.input_tokens == 11 and "₹42/kg" in call.request_summary


def test_unknown_route_rejected(session_factory):
    gw = _gateway(session_factory, Recorder([]))
    with pytest.raises(ValueError):
        gw.structured("no_such_route", Echo, [{"role": "user", "content": "x"}])


@pytest.mark.parametrize("stop,exc", [("refusal", LLMRefusal), ("max_tokens", LLMTruncated)])
def test_bad_stop_reasons_raise_and_log(session_factory, stop, exc):
    rec = Recorder([(200, _message([{"type": "text", "text": '{"vendor":"V","price":1}'}], stop_reason=stop))])
    gw = _gateway(session_factory, rec)
    with pytest.raises(exc):
        gw.structured("extract_text", Echo, [{"role": "user", "content": "x"}])
    assert _calls(session_factory)[-1].status == "error"


def test_transport_retry_resends_identical_body(session_factory):
    ok = (200, _message([{"type": "text", "text": '{"vendor":"V","price":1}'}]))
    rec = Recorder([(529, {"type": "error", "error": {"type": "overloaded_error", "message": "busy"}}), ok])
    gw = _gateway(session_factory, rec, max_retries=2)
    gw.structured("extract_text", Echo, [{"role": "user", "content": "x"}])
    assert len(rec.requests) == 2
    assert rec.requests[0].content == rec.requests[1].content  # byte-identical body


def test_converse_appends_exact_content_and_replays_it(session_factory):
    first = [THINKING, {"type": "text", "text": "Draft ready."}]
    rec = Recorder([(200, _message(first)), (200, _message([{"type": "text", "text": "Done."}]))])
    gw = _gateway(session_factory, rec, use_fallbacks=False)
    gw.converse("conv", "copilot", "Draft the RFx")
    gw.converse("conv", "copilot", "Make lines 12-15 BC flute")
    second_body = rec.bodies()[1]
    stored = gw.conversations.history("conv")
    # the stored assistant turn is replayed exactly, thinking block and signature unchanged
    assert second_body["messages"][1] == stored[1]
    assert stored[1]["content"][0] == THINKING
    assert stored[1]["content"][1]["text"] == "Draft ready."
    assert second_body["output_config"] == {"effort": "medium"}
    hist = gw.conversations.history("conv")
    assert [m["role"] for m in hist] == ["user", "assistant", "user", "assistant"]


def test_failed_turn_is_not_appended(session_factory):
    err = (500, {"type": "error", "error": {"type": "api_error", "message": "boom"}})
    rec = Recorder([(200, _message([{"type": "text", "text": "ok"}])), err])
    gw = _gateway(session_factory, rec, max_retries=0, use_fallbacks=False)
    gw.converse("conv", "analyst", "q1")
    before = gw.conversations.history("conv")
    with pytest.raises(LLMTransportError):
        gw.converse("conv", "analyst", "q2")
    assert gw.conversations.history("conv") == before
    assert _calls(session_factory)[-1].status == "error"


def test_refused_turn_is_not_appended(session_factory):
    rec = Recorder([(200, _message([{"type": "text", "text": "no"}], stop_reason="refusal"))])
    gw = _gateway(session_factory, rec, use_fallbacks=False)
    with pytest.raises(LLMRefusal):
        gw.converse("conv", "analyst", "q1")
    assert gw.conversations.history("conv") == []


def test_missing_credentials_is_reported_not_crashed(session_factory, monkeypatch):
    from app.llm.gateway import LLMUnavailable
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    gw = LLMGateway(session_factory, client=anthropic.Anthropic(api_key=None, http_client=httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(500)))))
    with pytest.raises(LLMUnavailable):
        gw.structured("extract_text", Echo, [{"role": "user", "content": "x"}])
    assert _calls(session_factory)[-1].status == "error"


def test_cut_off_json_is_a_clean_failure_not_a_crash(session_factory):
    """Live finding: a reply cut off mid-JSON raised a raw pydantic error that crashed the run."""
    rec = Recorder([(200, _message([{"type": "text", "text": '{"vendor":"V5","pri'}]))])
    gw = _gateway(session_factory, rec)
    with pytest.raises(LLMTruncated):
        gw.structured("extract_text", Echo, [{"role": "user", "content": "x"}])
    assert _calls(session_factory)[-1].status == "error"
