"""`make live-slice`: the vertical slice against the LIVE model, on a throwaway copy of app_data.

Runs: co-pilot mapping (proposal accepted as-is) → scripted buyer answers → co-pilot questionnaire/terms →
conformance → approve → send → deliver → live extraction → comparison → three analyst questions. Writes one
JSON file of what the app produced (outside the repo). It never reads evaluation material: the comparison
with the answer key happens in the eval workspace (`make eval-live`)."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import DEFAULT_DATA_ROOT
from app.main import create_app

BUYER = ("We are buying our 30 corrugated packaging SKUs for the next year. Deliver to the Chakan plant, Pune. "
         "All dimensions are internal. Quotes valid 90 days. Prices exclusive of GST.")
QUESTIONS = [
    "What if we split it, cheapest per line, but only among vendors who cleared the quality questionnaire?",
    "Whose ISO 9001 certificate is valid, and until when?",
    "Show unit price per box by vendor for lines 1 to 6 as a chart.",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--in-place", action="store_true", help="run on the real app_data (demo preparation) instead of a copy")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("FAIL: ANTHROPIC_API_KEY is not set (put it in .env and run via make).")
        return 1
    if args.in_place:
        work = DEFAULT_DATA_ROOT
    else:
        work = Path(tempfile.mkdtemp(prefix="live-slice-")) / "app_data"
        shutil.copytree(DEFAULT_DATA_ROOT / "seed", work / "seed")
        shutil.copytree(DEFAULT_DATA_ROOT / "inbox", work / "inbox")
    app = create_app(env={**os.environ, "APP_DATA_ROOT": str(work)})
    c = TestClient(app)
    log, t0 = {}, time.monotonic()

    def step(name, fn):
        t = time.monotonic()
        r = fn()
        log[name] = {"status": r.status_code, "ms": int((time.monotonic() - t) * 1000)}
        print(f"  {name}: HTTP {r.status_code} ({log[name]['ms']} ms)")
        return r.json() if r.headers.get("content-type", "").startswith("application/json") else None

    print(f"live slice on {work}")
    start = step("copilot_mapping", lambda: c.post("/rfx/primary", json={"title": "Annual corrugated packaging RFx (live run)"}))
    rid = start["rfx_id"]
    mapping = {m["column"]: m["field"] for m in start["mapping_proposal"]["mappings"] if m.get("field")}
    low = [m["column"] for m in start["mapping_proposal"]["mappings"] if m.get("confidence") != "HIGH"]
    imp = step("import", lambda: c.post(f"/rfx/{rid}/mapping/confirm", json={"mapping": mapping}))
    patch = step("copilot_gaps", lambda: c.post(f"/rfx/{rid}/gaps/propose", json={"text": BUYER}))
    gaps = step("apply_gaps", lambda: c.post(f"/rfx/{rid}/gaps/apply", json={"patch": patch, "source_text": BUYER}))
    q = step("copilot_questionnaire", lambda: c.post(f"/rfx/{rid}/questionnaire/propose"))
    qa = step("apply_questionnaire", lambda: c.post(f"/rfx/{rid}/questionnaire/apply", json={"draft": q["draft"]}))
    conf = step("conformance", lambda: c.post(f"/rfx/{rid}/conformance"))
    result = {"rfx_id": rid, "mapping_low_confidence": low, "import": imp, "gaps": gaps,
              "questionnaire_validation": q["validation"] if q else None, "questionnaire_applied": qa,
              "conformance": conf, "header": c.get(f"/rfx/{rid}").json()}
    if conf and conf.get("conforms"):
        step("approve", lambda: c.post(f"/rfx/{rid}/approve"))
        step("send", lambda: c.post(f"/rfx/{rid}/send"))
        while c.post(f"/rfx/{rid}/deliver-next").json().get("delivered"):
            pass
        # buyer sets the comparison FX rate from the rate the USD vendor states on its quote (runbook; DL-15/30)
        step("set_fx", lambda: c.put("/settings/fx/USD", json={"rate_to_inr": "95.25", "as_of": "2026-10-30",
                                                                "source": "RBI reference rate stated on the vendor's quote"}))
        result["process"] = step("live_extraction", lambda: c.post(f"/rfx/{rid}/process"))
        grid = c.get(f"/rfx/{rid}/comparison").json()
        result["comparison"] = grid
        result["eligibility"] = {v["name"]: c.get(f"/rfx/{rid}/vendors/{v['vendor_id']}/eligibility").json()
                                 for v in grid["vendors"] if v["state"] == "RESPONDED"}
        result["review_queue_size"] = len(c.get(f"/rfx/{rid}/review").json()["items"])
        session, answers = None, []
        for i, question in enumerate(QUESTIONS):
            a = step(f"analyst_q{i + 1}", lambda: c.post("/analyst/ask", json={"rfx_id": rid, "question": question,
                                                                               "session_id": session}))
            session = (a or {}).get("session_id", session)
            answers.append({"question": question, "answer": a})
        result["analyst"] = answers
    else:
        print("  conformance failed: the prepared responses are not delivered (DL-19). Differences are in the output.")
    with app.state.session_factory() as s:
        from app.db.models import LlmCall
        calls = s.query(LlmCall).all()
        result["llm_calls"] = [{"route": x.route, "status": x.status, "model": x.model, "effort": x.effort,
                                "stop_reason": x.stop_reason, "input_tokens": x.input_tokens, "output_tokens": x.output_tokens,
                                "latency_ms": x.latency_ms, "error": x.error} for x in calls]
    result["timings"], result["total_seconds"] = log, round(time.monotonic() - t0, 1)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str))
    ok = sum(1 for x in calls if x.status == "ok")
    print(f"done in {result['total_seconds']} s · model calls ok {ok}/{len(calls)} · wrote {out}")
    print(f"working copy kept for inspection: {work}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
