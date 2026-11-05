"""M6a: deterministic item-master import with AI column mapping (T-IMP-01), gap answers, line-level
conformance, approve/send/deliver with DL-23 submission linking — through the API, model mocked."""
import json
import shutil
from io import BytesIO
from pathlib import Path

import anthropic
import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app.db.models import LlmCall, Response, RfxLine
from app.llm.gateway import LLMGateway
from app.main import create_app
from app.rfx.item_master import import_rows, read_item_master
from app.rfx.service import _line_view

SRC = Path(__file__).resolve().parents[2] / "app_data"
pytestmark = pytest.mark.skipif(not (SRC / "seed/brief_pack/Item_Master_IM-2026.xlsx").exists(), reason="M1a dataset not generated")

MAPPING = {"Mat. Code": "sku_code", "Material Description": "description", "Pack Type": "item_type", "L": "dim_L", "W": "dim_W",
           "H": "dim_H", "Blank L": "blank_L", "Blank W": "blank_W", "Ply": "ply", "Flute": "flute_profile",
           **{f"GSM-L{i}": f"gsm_layer_{i}" for i in range(1, 8)}, "BF Liner": "bf_liner", "BF Fluting": "bf_medium",
           "Print": "printing", "Annual Req. (nos)": "annual_qty", "Std. Wt (g)": "reference_unit_weight_g",
           "Wt. Ref": "reference_weight_source", "Food Contact": "food_contact"}
BUYER = ("We are buying our 30 corrugated packaging SKUs for the next year. Deliver to the Chakan plant, Pune. "
         "All dimensions are internal. Quotes valid 90 days. Prices exclusive of GST.")
GAP_PATCH = {"scope": {"value": "Our 30 corrugated packaging SKUs for the next year",
                       "quote": "buying our 30 corrugated packaging SKUs for the next year"},
             "delivery_location": {"value": "Chakan plant, Pune", "quote": "Chakan plant, Pune"},
             "dimension_convention": {"value": "internal", "quote": "All dimensions are internal"},
             "validity_days": {"value": "90", "quote": "valid 90 days"},
             "gst_treatment": {"value": "prices exclusive of GST", "quote": "Prices exclusive of GST"}}


def questionnaire_output(data: Path) -> dict:
    """What a correct model draft looks like: one question per requirement, cited to the brief pack."""
    from app.rfx.questionnaire import brief_units
    from app.storage import Storage
    units, _ = brief_units(Storage(data))
    out = []
    for q in json.loads((data / "seed/canonical_rfx.json").read_text())["questionnaire"]:
        u = next(u for u in units.values() if q["requirement_key"] in u.text)
        rule = q["pass_rule"] or {"op": "present"}
        out.append({"no": q["no"], "requirement_key": q["requirement_key"], "section": q["section"],
                    "applicability": q["applicability"], "text": q["text"], "answer_type": q["answer_type"],
                    "mandatory": q["mandatory"], "pass_op": rule["op"],
                    "pass_value": None if "value" not in rule else str(rule["value"]),
                    "evidence_required": q["evidence_required"], "evidence_doc_type": q["evidence_doc_type"],
                    "source": {"unit_ids": [u.id], "quote": u.text}})
    terms = []
    for key, kind in (("CP-01", "PAYMENT"), ("CP-02", "LEAD_TIME"), ("CP-03", "GST_REGISTRATION")):
        u = next(u for u in units.values() if key in u.text)
        terms.append({"type": kind, "text": u.text.split("— ", 1)[-1], "source": {"unit_ids": [u.id], "quote": u.text}})
    return {"questions": out, "terms": terms}


def add_questionnaire(c, model, rfx_id, data):
    if model is not None:
        model.outputs.append(questionnaire_output(data))
    prop = c.post(f"/rfx/{rfx_id}/questionnaire/propose").json()
    assert all(v["ok"] for v in prop["validation"]), prop["validation"]
    assert len(prop["draft"]["terms"]) == 3
    r = c.post(f"/rfx/{rfx_id}/questionnaire/apply", json={"draft": prop["draft"]})
    assert r.status_code == 200 and r.json()["applied"] == 8
    return prop


class Model:
    def __init__(self):
        self.outputs, self.requests = [], []

    def __call__(self, req):
        self.requests.append(json.loads(req.content))
        out = self.outputs.pop(0)
        return httpx.Response(200, json={"id": "m", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
                                         "content": [{"type": "text", "text": json.dumps(out)}], "stop_reason": "end_turn",
                                         "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}})


@pytest.fixture()
def env(tmp_path):
    data = tmp_path / "app_data"
    shutil.copytree(SRC / "seed", data / "seed")
    shutil.copytree(SRC / "inbox", data / "inbox")
    app = create_app(env={"APP_DATA_ROOT": str(data), "APP_EVAL_ROOT_HINT": str(tmp_path / "eval")})
    model = Model()
    client = anthropic.Anthropic(api_key="k", http_client=httpx.Client(transport=httpx.MockTransport(model)))
    app.state.gateway_factory = lambda: LLMGateway(app.state.session_factory, client=client)
    return TestClient(app), app, model, data


def _start(c, model):
    model.outputs.append({"mappings": [{"column": h, "field": f, "confidence": "HIGH"} for h, f in MAPPING.items()]})
    r = c.post("/rfx/primary", json={})
    assert r.status_code == 200
    return r.json()


def test_mapping_call_sees_only_header_and_three_rows(env):
    c, app, model, _ = env
    body = _start(c, model)
    assert len(body["mapping_proposal"]["mappings"]) == len(MAPPING)
    sent = model.requests[0]["messages"][0]["content"]
    assert all(s in sent for s in ("PK-C101", "PK-C102", "PK-C103")) and "PK-C104" not in sent and "PK-S602" not in sent
    with app.state.session_factory() as s:
        assert s.query(LlmCall).one().route == "copilot_mapping"


def test_import_is_exact_t_imp_01(env):
    c, app, model, data = env
    rfx_id = _start(c, model)["rfx_id"]
    r = c.post(f"/rfx/{rfx_id}/mapping/confirm", json={"mapping": MAPPING}).json()
    assert r["lines"] == 30 and r["line_gaps"] == {}
    assert set(r["rfx_gaps"]) >= {"scope", "delivery_location", "dimension_convention", "validity_days", "gst_treatment"}
    canon = {l["sku_code"]: l for l in json.loads((data / "seed/canonical_rfx.json").read_text())["lines"]}
    with app.state.session_factory() as s:
        rows = s.query(RfxLine).filter_by(rfx_id=rfx_id).all()
    assert len(rows) == 30
    for l in rows:
        mine = {"item_type": l.item_type, "dims_mm": l.dims_mm, "blank_size_mm": l.blank_size_mm, "ply": l.ply,
                "flute_profile": l.flute_profile, "annual_qty": l.annual_qty, "layers": l.layers, "printing": l.printing,
                "reference_unit_weight_g": l.reference_unit_weight_g, "food_contact": l.food_contact}
        assert _line_view(mine) == _line_view(canon[l.sku_code]), l.sku_code
        assert l.source_evidence == [{"sheet": "item master", "row": l.line_no + 1}]
    # no model output contained line values: only one call (the mapping), returning mappings only
    assert len(model.requests) == 1


def test_header_variant_and_unknown_values(env):
    *_, data = env
    wb = load_workbook(data / "seed/brief_pack/Item_Master_IM-2026.xlsx")
    ws = wb.active
    ws.cell(1, 1, "SKU"); ws.cell(1, 21, "Yearly volume")  # renamed headers
    ws.cell(5, 3, "Mystery pack")  # unrecognised item type on data row 4
    bio = BytesIO(); wb.save(bio)
    sheet = read_item_master(bio.getvalue())
    mapping = {("SKU" if h == "Mat. Code" else "Yearly volume" if h == "Annual Req. (nos)" else h): f for h, f in MAPPING.items()}
    res = import_rows(sheet, mapping)
    assert len(res.lines) == 30 and res.lines[0]["sku_code"] == "PK-C101"
    assert any("not recognised" in g for g in res.line_gaps[4])  # a gap, never a guess
    with pytest.raises(ValueError):
        import_rows(sheet, {"SKU": "sku_code"})  # required fields unmapped


def test_full_flow_conformance_send_deliver(env):
    c, app, model, data = env
    rfx_id = _start(c, model)["rfx_id"]
    c.post(f"/rfx/{rfx_id}/mapping/confirm", json={"mapping": MAPPING})
    assert c.post(f"/rfx/{rfx_id}/approve").status_code == 409  # not conformance-checked
    assert c.post(f"/rfx/{rfx_id}/conformance").json()["conforms"] is False  # gaps still open
    model.outputs.append(GAP_PATCH)
    patch = c.post(f"/rfx/{rfx_id}/gaps/propose", json={"text": BUYER}).json()
    applied = c.post(f"/rfx/{rfx_id}/gaps/apply", json={"patch": patch, "source_text": BUYER}).json()
    assert applied["rejected"] == [] and not {"scope", "delivery_location", "gst_treatment"} & set(applied["remaining_gaps"])
    conf = c.post(f"/rfx/{rfx_id}/conformance").json()
    assert conf["conforms"] is False and {d.get("question") for d in conf["differences"]} >= {"QC-01", "CP-03"}
    add_questionnaire(c, model, rfx_id, data)
    conf = c.post(f"/rfx/{rfx_id}/conformance").json()
    assert conf["conforms"] is True, conf["differences"]
    assert c.post(f"/rfx/{rfx_id}/deliver-next").status_code == 409  # not sent yet
    assert c.post(f"/rfx/{rfx_id}/approve").status_code == 200
    n_vendors = len(json.loads((data / "seed/vendors.json").read_text()))
    n_msgs = len(list((data / "inbox").glob("*.eml")))
    assert c.post(f"/rfx/{rfx_id}/send").json() == {"sent": n_vendors}
    delivered = []
    while (d := c.post(f"/rfx/{rfx_id}/deliver-next").json()["delivered"]):
        delivered.append(d)
    assert len(delivered) == n_msgs
    d1, d2, d3 = delivered[:3]
    assert d1["path"].endswith("01_V5_quote.eml") and d2["submissions"] == 2 and d3["vendor"].startswith("Deccan")
    with app.state.session_factory() as s:
        resps = s.query(Response).all()
        # V5's two messages land in one Response (DL-23); every other vendor sent one message
        assert len(resps) == n_msgs - 1 and sorted(len(r.submissions) for r in resps) == [1] * (n_msgs - 2) + [2]


def test_quote_not_in_source_is_rejected_and_diff_reported(env):
    c, app, model, data = env
    rfx_id = _start(c, model)["rfx_id"]
    c.post(f"/rfx/{rfx_id}/mapping/confirm", json={"mapping": MAPPING})
    bad = dict(GAP_PATCH, validity_days={"value": "120", "quote": "valid 120 days"})
    r = c.post(f"/rfx/{rfx_id}/gaps/apply", json={"patch": bad, "source_text": BUYER}).json()
    assert r["rejected"] == ["validity_days"]
    c.post(f"/rfx/{rfx_id}/gaps/apply", json={"patch": GAP_PATCH, "source_text": BUYER})
    add_questionnaire(c, model, rfx_id, data)
    with app.state.session_factory.begin() as s:
        line = s.query(RfxLine).filter_by(rfx_id=rfx_id, line_no=7).one()
        layers = [dict(x) for x in line.layers]; layers[0]["gsm"] = 150; line.layers = layers
    diffs = c.post(f"/rfx/{rfx_id}/conformance").json()["differences"]
    assert diffs == [{"sku": "PK-C201", "field": "gsm", "draft": [150, 120, 150, 120, 180], "canonical": [180, 120, 150, 120, 180]}]


def test_scope_is_drafted_from_the_buyers_words_fn_02(env):
    c, app, model, _ = env
    rfx_id = _start(c, model)["rfx_id"]
    c.post(f"/rfx/{rfx_id}/mapping/confirm", json={"mapping": MAPPING})
    invented = dict(GAP_PATCH, scope={"value": "Packaging for three years", "quote": "for the next three years"})
    assert c.post(f"/rfx/{rfx_id}/gaps/apply", json={"patch": invented, "source_text": BUYER}).json()["rejected"] == ["scope"]
    assert c.get(f"/rfx/{rfx_id}").json()["scope"] is None
    c.post(f"/rfx/{rfx_id}/gaps/apply", json={"patch": GAP_PATCH, "source_text": BUYER})
    assert c.get(f"/rfx/{rfx_id}").json()["scope"] == "Our 30 corrugated packaging SKUs for the next year"
    fb = c.post("/rfx/seeded-fallback", json={}).json()
    assert fb["scope"].startswith("Supply of 30 corrugated packaging SKUs")
