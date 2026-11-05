"""T-SLICE-01 (deterministic part): one primary RFx end to end through the API —
item-master import (AI mapping) → gaps → conformance → approve → send → V5 email + V5 questionnaire
submission + V1 xlsx delivered → extraction → Phase A/B → grid → VP-style question via run_scenario
→ draft memo. The model is mocked from the real request content; the live part needs an API key."""
import json
import shutil
from decimal import Decimal as D
from pathlib import Path

import anthropic
import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient

from app.ingest.parsers import parse_message
from app.ingest.wire import to_wire
from tests.llm_mock import respond
from app.llm.gateway import LLMGateway
from app.main import create_app
from tests.test_rfx_m6a import BUYER, GAP_PATCH, MAPPING, add_questionnaire, questionnaire_output

SRC = Path(__file__).resolve().parents[2] / "app_data"
pytestmark = pytest.mark.skipif(not (SRC / "inbox/03_V1_quotation.eml").exists(), reason="M1a dataset not generated")


def _ev(uid, quote):
    return {"unit_ids": [uid], "quote": quote}


def v5_extraction():
    u = "D1:l1"
    return {"line_quotes": [
        {"vendor_line_ref": "5-ply", "description_as_stated": "5-ply", "unit_class": "PER_KG", "unit_source": "STATED", "unit_as_stated": "/kg",
         "price": {"value_as_stated": "42", "value": 42, "currency_as_stated": "₹", "currency_source": "STATED", "evidence": _ev(u, "₹42/kg")},
         "applies_to_group": {"attribute": "ply", "value": 5, "evidence": _ev(u, "5-ply")}},
        {"vendor_line_ref": "3-ply", "description_as_stated": "3-ply", "unit_class": "PER_KG", "unit_source": "INHERITED_FROM_CONTEXT",
         "unit_inherited_from": _ev(u, "₹42/kg"),
         "price": {"value_as_stated": "38", "value": 38, "currency_source": "INHERITED_FROM_CONTEXT", "evidence": _ev(u, "38 for the 3-ply")},
         "applies_to_group": {"attribute": "ply", "value": 3, "evidence": _ev(u, "3-ply")}}],
        "document_terms": [{"type": "FREIGHT", "scope": "all", "text": "freight extra", "evidence": _ev(u, "freight extra")}],
        "references": [{"type": "PRIOR_UNSPECIFIED", "scope_text": "rest", "evidence": _ev(u, "rest same as last year")}],
        "questionnaire_answers": [], "gst_statement": "SILENT"}


def v1_extraction():
    _, docs = parse_message((SRC / "inbox/03_V1_quotation.eml").read_bytes())
    return v1_extraction_from(docs)


def v1_extraction_from(docs):
    """What a correct model reads from V1's sheet, cell by cell (row positions are irrelevant)."""
    grid = {(u.locator["sheet"], u.locator["cell"]): u for u in docs[1].units}
    quotes = []
    for (sheet, _), u in grid.items():
        if sheet != "Quotation" or u.locator["col"] != 3 or not u.text.startswith("PK-"):
            continue
        row = u.locator["row"]
        slabs = []
        for (lo, hi), col in zip([(None, 10000), (10001, 50000), (50001, None)], "HIJ"):
            c = grid[("Quotation", f"{col}{row}")]
            slabs.append({"min_qty": lo, "max_qty": hi, "price": {"value_as_stated": c.text, "value": float(c.text),
                                                                   "currency_source": "STATED", "evidence": _ev(c.id, c.text)}})
        is_set = grid.get(("Quotation", f"K{row}")) is not None and grid[("Quotation", f"K{row}")].text == "Set price"
        quotes.append({"vendor_line_ref": str(row), "description_as_stated": grid[("Quotation", f"D{row}")].text, "item_code": u.text,
                       "slabs": slabs, "unit_class": "PER_SET" if is_set else "PER_BOX", "unit_source": "STATED",
                       "unit_as_stated": "per set" if is_set else "per pc"})
    notes = {u.text: u for u in docs[1].units if u.text[:2] in ("1.", "2.")}
    fr, gst = next(t for t in notes if "freight" in t), next(t for t in notes if "GST" in t)
    answers, attached = questionnaire_and_documents(docs)
    return {"line_quotes": quotes, "gst_statement": "STATED", "references": [], "questionnaire_answers": answers,
            "attached_documents": attached, "document_terms": [
        {"type": "FREIGHT", "scope": "all", "text": fr, "evidence": _ev(notes[fr].id, "freight included")},
        {"type": "GST", "scope": "all", "text": gst, "evidence": _ev(notes[gst].id, "exclusive of GST")}]}


def questionnaire_and_documents(docs):
    """What a correct model reads from a questionnaire sheet and the attached certificates."""
    answers = []
    for d in docs:
        cells = {(u.locator.get("sheet"), u.locator.get("cell")): u for u in d.units if d.kind == "xlsx"}
        for (sheet, cell), u in cells.items():
            if not (sheet and "Questionnaire" in sheet and cell.startswith("A") and u.text.startswith("Q")):
                continue
            row = cell[1:]
            a, rem = cells.get((sheet, f"C{row}")), cells.get((sheet, f"D{row}"))
            answers.append({"question_no": u.text, "answer_value": a.text, "answer_text": " ".join(x.text for x in (a, rem) if x),
                            "evidence": _ev(a.id, a.text),
                            "attachment_refs": [rem.text] if rem and rem.text.lower().endswith(".pdf") else []})
    attached = []
    for d in docs:
        if d.kind != "pdf":
            continue
        t = [u for u in d.units]
        name = d.filename.lower()
        kind = ("ISO_9001_CERTIFICATE" if "iso" in name else "BCT_ECT_TEST_REPORT" if "bct" in name else "FOOD_CONTACT_DECLARATION")
        if kind == "ISO_9001_CERTIFICATE":
            ent_u = t[next(i for i, u in enumerate(t) if u.text.startswith("This is to certify")) + 1]; entity = ent_u.text
        elif kind == "BCT_ECT_TEST_REPORT":
            ent_u = next(u for u in t if u.text.startswith("Customer ")); entity = ent_u.text[len("Customer "):]
        else:
            ent_u = next(u for u in t if u.text.startswith("We, ")); entity = ent_u.text[4:].split(", declare")[0]
        date_u = next(u for u in t if u.text.startswith("Date"))
        valid_u = next(u for u in t if u.text.startswith("Valid until"))
        import re
        attached.append({"document_ref": d.ref, "doc_type": kind, "entity_name": entity,
                         "issue_date_as_stated": re.search(r"\d{4}-\d{2}-\d{2}", date_u.text).group(0),
                         "expiry_as_stated": valid_u.text[len("Valid until "):],
                         "evidence": {"unit_ids": [ent_u.id, date_u.id, valid_u.id], "quote": ent_u.text}})
    return answers, attached


def v5_questionnaire_extraction():
    _, docs = parse_message((SRC / "inbox/02_V5_questionnaire.eml").read_bytes())
    answers, attached = questionnaire_and_documents(docs)
    return {**EMPTY, "questionnaire_answers": answers, "attached_documents": attached}


EMPTY = {"line_quotes": [], "document_terms": [], "references": [], "questionnaire_answers": [], "gst_statement": "SILENT"}


class RoutedModel:
    """Answers by request content, like a real model would see it."""

    def __init__(self, data=None):
        self.calls, self.data = [], data

    def __call__(self, req):
        body = json.loads(req.content)
        self._req = req
        self.calls.append(body)
        msgs = body["messages"]
        last = msgs[-1]["content"]
        if "tools" in body:  # analyst
            if isinstance(last, str):
                out = [{"type": "tool_use", "id": "t1", "name": "run_scenario", "input": {
                    "strategy": "cheapest_per_line", "vendor_id": None, "context": "formal", "include_needs_review": False,
                    "exclude_vendor_ids": []}}]
                return self._reply(out, "tool_use")
            res = json.loads(last[0]["content"])
            spend = ", ".join(f"{v} ₹{int(D(a)):,}" for v, a in res["per_vendor_spend_inr"].items())
            txt = (f"On the unit basis the cheapest-per-line split costs ₹{int(D(res['total_annual_spend_inr'])):,} a year ({spend}). "
                   f"{len(res['uncovered_lines'])} lines have no includable quote.")
            return self._reply([{"type": "text", "text": txt}])
        text = last if isinstance(last, str) else json.dumps(last)
        if text.startswith("Columns:"):
            out = {"mappings": [{"column": h, "field": f, "confidence": "HIGH"} for h, f in MAPPING.items()]}
        elif text.startswith("Open fields"):
            out = GAP_PATCH
        elif text.startswith("Buyer requirement documents"):
            out = questionnaire_output(self.data)
        elif "₹42/kg for the 5-ply" in text:
            out = v5_extraction()
        elif "Quotation No. DKB" in text:
            out = v1_extraction()
        elif "Supplier questionnaire" in text and "Sahyadri Paper Mills" in text and "Questionnaire!A1" in text:
            out = v5_questionnaire_extraction()
        else:
            out = EMPTY
        if "line_quotes" in out:  # extraction calls use the flat wire schema (structured-output limits)
            out = to_wire(out)
        return self._reply([{"type": "text", "text": json.dumps(out)}])

    def _reply(self, content, stop="end_turn"):
        return respond(self._req, content, stop)


def test_vertical_slice(tmp_path):
    data = tmp_path / "app_data"
    shutil.copytree(SRC / "seed", data / "seed")
    shutil.copytree(SRC / "inbox", data / "inbox")
    app = create_app(env={"APP_DATA_ROOT": str(data), "APP_EVAL_ROOT_HINT": str(tmp_path / "eval")})
    model = RoutedModel(data)
    client = anthropic.Anthropic(api_key="k", http_client=httpx.Client(transport=httpx.MockTransport(model)))
    app.state.gateway_factory = lambda: LLMGateway(app.state.session_factory, client=client)
    c = TestClient(app)

    rid = c.post("/rfx/primary", json={"title": "Annual corrugated packaging — Chakan"}).json()["rfx_id"]
    assert c.post(f"/rfx/{rid}/mapping/confirm", json={"mapping": MAPPING}).json()["lines"] == 30
    patch = c.post(f"/rfx/{rid}/gaps/propose", json={"text": BUYER}).json()
    c.post(f"/rfx/{rid}/gaps/apply", json={"patch": patch, "source_text": BUYER})
    add_questionnaire(c, None, rid, data)
    assert c.post(f"/rfx/{rid}/conformance").json()["conforms"] is True
    n_vendors = len(json.loads((data / "seed/vendors.json").read_text()))
    assert c.post(f"/rfx/{rid}/approve").status_code == 200 and c.post(f"/rfx/{rid}/send").json()["sent"] == n_vendors
    while c.post(f"/rfx/{rid}/deliver-next").json()["delivered"]:
        pass

    proc = c.post(f"/rfx/{rid}/process").json()
    # the mock reads V1 and V5 like a correct model; V2/V3 are read live in `make live-slice` (this mock returns nothing for them)
    assert proc["failed"] == {} and {"Deccan Kraft & Board Pvt. Ltd.", "Sahyadri Paper Mills"} <= set(proc["processed_vendors"])
    assert proc["snapshot_hash"]

    grid = c.get(f"/rfx/{rid}/comparison").json()
    assert grid["provisional"] is False
    v1 = next(v["vendor_id"] for v in grid["vendors"] if v["name"].startswith("Deccan"))
    v5 = next(v["vendor_id"] for v in grid["vendors"] if v["name"].startswith("Sahyadri"))
    rows = {r["line_no"]: r for r in grid["rows"]}
    assert rows[19]["cells"][str(v1)]["status"] == "MISSING" and rows[25]["cells"][str(v5)]["status"] == "NOT_CONVERTIBLE"
    assert rows[15]["cells"][str(v5)]["status"] == "UNRESOLVED" and rows[15]["cells"][str(v5)]["value"] is None
    assert rows[7]["cells"][str(v5)]["status"] == "ASSUMED" and "REFERENCE_WEIGHT" in rows[7]["cells"][str(v5)]["reasons"]
    assert rows[1]["cells"][str(v1)]["status"] in ("VERIFIED", "EXTRACTED", "NEEDS_REVIEW")
    for n in (1, 7, 14):  # V5 ex-works vs V1 delivered: landed basis shows nothing for V5
        assert c.get(f"/rfx/{rid}/comparison?basis=landed").json()["rows"][n - 1]["cells"][str(v5)]["value"] is None

    ans = c.post("/analyst/ask", json={"rfx_id": rid, "question": "What if we split it, cheapest per line?"}).json()
    assert ans["grounded"] is True and ans["tool_calls"][0]["tool"] == "run_scenario"
    assert ans["caveats"]["freight_dependent"]  # V5 wins some lines on unit price with freight unknown (DL-25)
    assert "Deccan Kraft & Board Pvt. Ltd.: 28/30, missing lines 19, 20" in ans["caveats"]["coverage"]  # EDGE-07 disclosure

    # M6b: eligibility from the questionnaires + certificates (deterministic rules over verified facts)
    e5 = c.get(f"/rfx/{rid}/vendors/{v5}/eligibility").json()
    assert e5["quality"]["label"] == "Passed" and e5["commercial"]["label"] == "Failed"  # 30-day credit only (DL-14)
    assert [q["key"] for q in e5["commercial"]["questions"] if q["state"] == "FAIL"] == ["CP-01"]
    assert e5["line_level"][0]["key"] == "QC-03" and e5["line_level"][0]["state"] == "PASS"
    iso = next(q for q in e5["quality"]["questions"] if q["key"] == "QC-01")
    assert iso["provenance"]["documents"][0]["expiry"] == "2027-08-18"
    bct = next(q for q in e5["quality"]["questions"] if q["key"] == "QC-02")
    assert bct["provenance"]["documents"][0]["expiry"] == "2027-07-09"  # "12 months from date tested"
    e1 = c.get(f"/rfx/{rid}/vendors/{v1}/eligibility").json()
    assert e1["quality"]["label"] == "Passed"

    sc = c.post(f"/rfx/{rid}/scenarios", json={"name": "VP split"}).json()
    assert sum(D(v) for v in sc["per_vendor_spend_inr"].values()) == D(sc["total_annual_spend_inr"])
    awarded = {a["line_no"] for a in sc["awards"]}
    uncovered = {u["line_no"] for u in sc["uncovered_lines"]}
    assert {19, 20} <= uncovered and awarded | uncovered == set(range(1, 31))
    memo = c.post(f"/scenarios/{sc['scenario_id']}/memo?title=Slice").json()["memo_markdown"]
    assert "DRAFT" in memo and "Line 19 (PK-D401): no includable quote." in memo


class FlakyModel(RoutedModel):
    """Fails V1's extraction while `fail_v1` is set; can change V5's stated ₹/kg to simulate a different read."""

    def __init__(self, data):
        super().__init__(data)
        self.fail_v1, self.v5_rate = True, None

    def __call__(self, req):
        body = json.loads(req.content)
        self._req = req
        text = json.dumps(body["messages"][-1]["content"], ensure_ascii=False)
        if self.fail_v1 and "Quotation No. DKB" in text:
            return httpx.Response(400, json={"type": "error", "error": {"type": "invalid_request_error", "message": "injected"}})
        resp = super().__call__(req)
        if self.v5_rate and "₹42/kg for the 5-ply" in text:
            out = v5_extraction()
            for lq in out["line_quotes"]:  # a different read of the same evidence (numbers come from the text as written)
                lq["price"]["value_as_stated"] = str(self.v5_rate)
            resp = self._reply([{"type": "text", "text": json.dumps(to_wire(out))}])
        return resp


def _delivered(tmp_path, model_cls):
    data = tmp_path / "app_data"
    shutil.copytree(SRC / "seed", data / "seed")
    shutil.copytree(SRC / "inbox", data / "inbox")
    app = create_app(env={"APP_DATA_ROOT": str(data), "APP_EVAL_ROOT_HINT": str(tmp_path / "eval")})
    model = model_cls(data)
    client = anthropic.Anthropic(api_key="k", max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(model)))
    app.state.gateway_factory = lambda: LLMGateway(app.state.session_factory, client=client)
    c = TestClient(app)
    rid = c.post("/rfx/primary", json={}).json()["rfx_id"]
    c.post(f"/rfx/{rid}/mapping/confirm", json={"mapping": MAPPING})
    patch = c.post(f"/rfx/{rid}/gaps/propose", json={"text": BUYER}).json()
    c.post(f"/rfx/{rid}/gaps/apply", json={"patch": patch, "source_text": BUYER})
    add_questionnaire(c, None, rid, data)
    assert c.post(f"/rfx/{rid}/conformance").json()["conforms"] is True
    c.post(f"/rfx/{rid}/approve"); c.post(f"/rfx/{rid}/send")
    while c.post(f"/rfx/{rid}/deliver-next").json()["delivered"]:
        pass
    return c, app, model, rid


def test_failure_injection_rerun_and_carry_forward(tmp_path):
    c, app, model, rid = _delivered(tmp_path, FlakyModel)
    proc = c.post(f"/rfx/{rid}/process").json()
    assert list(proc["failed"]) == ["Deccan Kraft & Board Pvt. Ltd."] and "Sahyadri Paper Mills" in proc["processed_vendors"], proc
    grid = c.get(f"/rfx/{rid}/comparison").json()
    v1 = next(v["vendor_id"] for v in grid["vendors"] if v["name"].startswith("Deccan"))
    v5 = next(v["vendor_id"] for v in grid["vendors"] if v["name"].startswith("Sahyadri"))
    assert grid["provisional"] is True  # Phase B over an incomplete set is reported, not hidden
    assert all(r["cells"][str(v1)]["state"] == "PENDING_PROCESSING" for r in grid["rows"])  # no partial rows

    # a buyer resolution on a V5 cell before any re-run
    cell = next(r for r in grid["rows"] if r["cells"][str(v5)].get("status") == "ASSUMED")
    n = cell["line_no"]
    assert c.post(f"/rfx/{rid}/resolutions", json={"vendor_id": v5, "line_no": n, "type": "ACCEPT"}).status_code == 200

    model.fail_v1 = False
    r1 = c.post(f"/rfx/{rid}/responses/{v1}/rerun").json()
    assert r1["status"] == "ok" and c.get(f"/rfx/{rid}/comparison").json()["provisional"] is False

    same = c.post(f"/rfx/{rid}/responses/{v5}/rerun").json()  # identical read → carried forward
    assert same["stale_resolutions"] == []
    assert {r["line_no"]: r for r in c.get(f"/rfx/{rid}/comparison").json()["rows"]}[n]["cells"][str(v5)]["status"] in ("VERIFIED", "ASSUMED")

    model.v5_rate = 44  # the re-run reads a different number → STALE_SOURCE_CHANGED, item reopens
    changed = c.post(f"/rfx/{rid}/responses/{v5}/rerun").json()
    assert len(changed["stale_resolutions"]) == 1
    audit = c.get(f"/rfx/{rid}/audit").json()
    assert [e["action"] for e in audit].count("RERUN_REQUESTED") == 3
    assert any(e["action"] == "RESOLUTION_STALE" and e["reason"] == "STALE_SOURCE_CHANGED" for e in audit)


def test_read_responses_only_processes_new_arrivals(tmp_path):
    """EX-02 staggered arrival: a later 'Read responses' re-reads only what arrived since, never everyone again."""
    c, app, model, rid = _delivered(tmp_path, RoutedModel)
    c.post(f"/rfx/{rid}/process")
    n_calls = len(model.calls)
    again = c.post(f"/rfx/{rid}/process").json()
    assert len(model.calls) == n_calls and again["failed"] == {} and len(again["processed_vendors"]) >= 4
