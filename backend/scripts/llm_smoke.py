"""`make llm-smoke`: one minimal live call through the real gateway (route `smoke`, effort low).
Prints the model, stop reason, token counts and latency. Never prints the key."""
from __future__ import annotations

import os
import sys
import time

from pydantic import BaseModel

from app.db.session import init_db, make_engine, make_session_factory
from app.llm.gateway import LLMError, LLMGateway


class Pong(BaseModel):
    reply: str


def main() -> int:
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("FAIL: ANTHROPIC_API_KEY is not set in this environment (put it in .env, then run `make llm-smoke`).")
        return 1
    engine = make_engine("sqlite://")  # in-memory: the smoke test leaves nothing behind
    init_db(engine)
    sf = make_session_factory(engine)
    gw = LLMGateway(sf)
    t0 = time.monotonic()
    try:
        out = gw.structured("smoke", Pong, [{"role": "user", "content": "Reply with the single word: pong"}],
                            system="You are a connectivity check.", max_tokens=200, prompt_version="smoke_v1")
    except LLMError as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        return 1
    from app.db.models import LlmCall
    with sf() as s:
        call = s.query(LlmCall).one()
    print(f"OK: model={call.model} route=smoke stop={call.stop_reason} tokens in/out={call.input_tokens}/{call.output_tokens} "
          f"latency={int((time.monotonic() - t0) * 1000)} ms reply={out.reply!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
