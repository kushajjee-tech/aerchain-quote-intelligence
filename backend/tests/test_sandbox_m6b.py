"""M6b: seeded fallback (RFX-8), sandbox isolation (DL-17), upload to an existing or new vendor (J8), RFx
provenance header (RFX-11), cited RFx terms (RFX-9)."""
import base64
import hashlib
import shutil

import anthropic
import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient

from app.db.models import ProcessingSet
from app.llm.gateway import LLMGateway
from app.main import create_app
from tests.test_rfx_m6a import MAPPING
from tests.test_slice_t_slice_01 import SRC, RoutedModel, _delivered, parse_message

pytestmark = pytest.mark.skipif(not (SRC / "inbox/03_V1_quotation.eml").exists(), reason="M1a dataset not generated")


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _v1_xlsx() -> bytes:
    _, docs = parse_message((SRC / "inbox/03_V1_quotation.eml").read_bytes())
    return docs[1].data


def test_seeded_fallback_is_labelled_conforming_and_flows(tmp_path):
    data = tmp_path / "app_data"
    shutil.copytree(SRC / "seed", data / "seed"); shutil.copytree(SRC / "inbox", data / "inbox")
    canon_sha = _sha(data / "seed/canonical_rfx.json")
    app = create_app(env={"APP_DATA_ROOT": str(data), "APP_EVAL_ROOT_HINT": str(tmp_path / "eval")})
    model = RoutedModel(data)
    client = anthropic.Anthropic(api_key="k", http_client=httpx.Client(transport=httpx.MockTransport(model)))
    app.state.gateway_factory = lambda: LLMGateway(app.state.session_factory, client=client)
    c = TestClient(app)
    h = c.post("/rfx/seeded-fallback", json={}).json()
    assert h["origin"] == "SEEDED_FALLBACK" and h["label"] == "Seeded fallback (canonical spec)"
    assert h["conformance"]["conforms"] is True and len(h["terms"]) == 3
    rid = h["rfx_id"]
    n_vendors = len(__import__("json").loads((data / "seed/vendors.json").read_text()))
    assert c.post(f"/rfx/{rid}/approve").status_code == 200 and c.post(f"/rfx/{rid}/send").json()["sent"] == n_vendors
    while c.post(f"/rfx/{rid}/deliver-next").json()["delivered"]:
        pass
    assert c.post(f"/rfx/{rid}/process").json()["failed"] == {}
    assert len(c.get(f"/rfx/{rid}/comparison").json()["rows"]) == 30
    assert _sha(data / "seed/canonical_rfx.json") == canon_sha  # never changed


def test_sandbox_is_isolated_and_takes_uploads(tmp_path):
    c, app, model, rid = _delivered(tmp_path, RoutedModel)  # the primary RFx, delivered
    assert c.post(f"/rfx/{rid}/process").json()["failed"] == {}
    sf = app.state.session_factory
    data = tmp_path / "app_data"
    canon_sha, inbox_sha = _sha(data / "seed/canonical_rfx.json"), sorted(_sha(p) for p in (data / "inbox").iterdir())
    with sf() as s:
        primary_snap = s.query(ProcessingSet).filter_by(rfx_id=rid).one().snapshot_hash

    sb = c.post("/rfx/primary", json={"title": "Sandbox", "sandbox": True}).json()["rfx_id"]
    assert c.get(f"/rfx/{sb}").json()["origin"] == "SANDBOX"
    c.post(f"/rfx/{sb}/mapping/confirm", json={"mapping": MAPPING})
    assert c.post(f"/rfx/{sb}/approve").status_code == 200        # free-form drafting: no conformance gate
    c.post(f"/rfx/{sb}/send")
    assert c.post(f"/rfx/{sb}/deliver-next").status_code == 409   # never the prepared inbox (DL-17)
    up = c.post(f"/rfx/{sb}/upload", json={"vendor_name": "Deccan Kraft & Board Pvt. Ltd.", "vendor_email": "new.contact@dkb.example",
                                            "filename": "DKB quote (copy).xlsx",
                                            "content_b64": base64.b64encode(_v1_xlsx()).decode()})
    assert up.status_code == 200 and up.json()["path"].startswith(f"uploads/rfx{sb}/")
    proc = c.post(f"/rfx/{sb}/process").json()
    assert proc["failed"] == {} and proc["processed_vendors"] == ["Deccan Kraft & Board Pvt. Ltd."]
    sgrid = c.get(f"/rfx/{sb}/comparison").json()
    assert any(r["cells"][str(up.json()["vendor_id"])]["value"] for r in sgrid["rows"])  # same pipeline after upload

    with sf() as s:
        assert s.query(ProcessingSet).filter_by(rfx_id=rid).one().snapshot_hash == primary_snap  # primary untouched
    assert _sha(data / "seed/canonical_rfx.json") == canon_sha
    assert sorted(_sha(p) for p in (data / "inbox").iterdir()) == inbox_sha


def test_upload_rules_and_header(tmp_path):
    c, app, model, rid = _delivered(tmp_path, RoutedModel)
    v1 = next(v for v in c.get(f"/rfx/{rid}/comparison").json()["vendors"] if v["name"].startswith("Deccan"))
    r = c.post(f"/rfx/{rid}/upload", json={"vendor_name": v1["name"], "vendor_email": "sales@deccankraft.example",
                                           "filename": "revised.xlsx", "content_b64": base64.b64encode(_v1_xlsx()).decode()})
    assert r.status_code == 200 and r.json()["vendor_id"] == v1["vendor_id"]
    assert r.json()["submissions"] == 2                           # added to the existing vendor's response (DL-23)
    assert c.post(f"/rfx/{rid}/upload", json={"vendor_name": "x", "vendor_email": "x@x", "filename": "a.pdf",
                                              "content_b64": "%%%"}).status_code == 422
    draft = c.post("/rfx/seeded-fallback", json={}).json()["rfx_id"]
    assert c.post(f"/rfx/{draft}/upload", json={"vendor_name": "x", "vendor_email": "x@x", "filename": "a.pdf",
                                                "content_b64": base64.b64encode(b"x").decode()}).status_code == 409  # not sent
    h = c.get(f"/rfx/{rid}").json()
    assert h["origin"] == "COPILOT_LIVE" and h["label"] == "Drafted live by the co-pilot"
    acts = [p["action"] for p in h["patches"]]
    assert acts.index("MAPPING_CONFIRMED_AND_IMPORTED") < acts.index("QUESTIONNAIRE_APPLIED") < acts.index("RFX_SENT")
    assert {t["type"] for t in h["terms"]} == {"PAYMENT", "LEAD_TIME", "GST_REGISTRATION"}
    assert all(t["source"]["unit_ids"] for t in h["terms"])      # every term cites the policy
    assert [x["rfx_id"] for x in c.get("/rfx").json()] == [rid, draft]


def test_inbox_delivery_is_per_rfx(tmp_path):
    c, app, model, rid = _delivered(tmp_path, RoutedModel)  # inbox already delivered to the live primary RFx
    fb = c.post("/rfx/seeded-fallback", json={}).json()["rfx_id"]
    c.post(f"/rfx/{fb}/approve"); c.post(f"/rfx/{fb}/send")
    got = []
    while (d := c.post(f"/rfx/{fb}/deliver-next").json()["delivered"]):
        got.append(d["path"])
    assert len(got) == len(list((SRC / "inbox").glob("*.eml")))
