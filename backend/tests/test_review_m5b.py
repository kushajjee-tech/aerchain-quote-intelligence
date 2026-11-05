"""M5b: decision-sensitive review queue (REV-1/2, DL-28), provenance drawer (REV-3), deterministic
clarification pack with the DL-20 reference section (DL-32), approve → outbox, reference terms confirmation."""
import pytest

from app.db.models import LlmCall, OutboxMessage, Reference
from tests.test_slice_t_slice_01 import SRC, RoutedModel, _delivered

pytestmark = pytest.mark.skipif(not (SRC / "inbox/03_V1_quotation.eml").exists(), reason="M1a dataset not generated")
SENTENCE = "₹42/kg for the 5-ply, 38 for the 3-ply, rest same as last year, freight extra."


@pytest.fixture()
def processed(tmp_path):
    c, app, model, rid = _delivered(tmp_path, RoutedModel)
    assert c.post(f"/rfx/{rid}/process").json()["failed"] == {}
    vendors = {v["name"]: v["vendor_id"] for v in c.get(f"/rfx/{rid}/comparison").json()["vendors"]}
    return c, app, rid, vendors["Deccan Kraft & Board Pvt. Ltd."], vendors["Sahyadri Paper Mills"]


def test_review_queue_is_decision_sensitive_first(processed):
    c, app, rid, v1, v5 = processed
    items = c.get(f"/rfx/{rid}/review").json()["items"]
    kinds = {i["kind"] for i in items}
    assert {"CELL", "FREIGHT_ESTIMATE"} <= kinds
    flags = [i["decision_sensitive"] for i in items]
    assert flags == sorted(flags, reverse=True)                     # sensitive items lead the queue
    fe = [i for i in items if i["kind"] == "FREIGHT_ESTIMATE"]
    assert fe and all(i["vendor_id"] == v5 and i["break_even"] for i in fe)
    ref_items = [i for i in items if "REFERENCE_AMBIGUOUS" in (i.get("reasons") or [])]
    assert ref_items and all(i["severity"] == "blocking" for i in ref_items)


def test_provenance_drawer_cites_the_sentence(processed):
    c, app, rid, v1, v5 = processed
    p = c.get(f"/rfx/{rid}/cells/{v5}/1").json()  # 3-ply: "38" inherits the unit
    assert p["cell"]["status"] == "ASSUMED" and p["cell"]["weight_source"] == "SKU_REFERENCE"
    cites = {x["role"]: x for x in p["source"]["cites"]}
    assert cites["price"]["units"][0] == {"id": "D1:l1", "text": SENTENCE, "document": "(email body)"}
    assert "unit (inherited)" in cites and "group scope" in cites
    steps = [t["step"] for t in p["trace"]]
    assert "weight_conversion" in steps and "gst" in steps
    assert "plausibility" not in [t["step"] for t in p["phase_a"]["trace"]]  # the stored Phase A read, before Phase B
    assert "plausibility" in steps
    v1cell = c.get(f"/rfx/{rid}/cells/{v1}/1").json()
    assert v1cell["source"]["cites"][0]["units"][0]["document"] == "DKB_Quotation_1187.xlsx"


def test_clarification_pack_is_deterministic_and_complete(processed):
    c, app, rid, v1, v5 = processed
    with app.state.session_factory() as s:
        calls = s.query(LlmCall).count()
    a = c.post(f"/rfx/{rid}/vendors/{v5}/clarification-pack").json()
    b = c.post(f"/rfx/{rid}/vendors/{v5}/clarification-pack").json()
    assert a["body"] == b["body"] and a["content_hash"] == b["content_hash"]  # byte-identical
    with app.state.session_factory() as s:
        assert s.query(LlmCall).count() == calls                             # no AI involved
    kinds = [i["kind"] for i in a["items"]]
    assert "REFERENCE" in kinds and "FREIGHT" in kinds
    ranks = [i["sensitivity_rank"] for i in a["items"]]
    assert ranks == list(range(1, len(ranks) + 1))
    sens = [i["decision_sensitive"] for i in a["items"]]
    assert sens == sorted(sens, reverse=True)
    body = a["body"]
    assert '"rest same as last year"' in body
    assert "(A) Prices" in body and "(B) Commercial terms" in body
    assert "last year ₹" in body                                    # same-vendor, same-spec candidates shown
    assert "specification has changed" in body                      # BASELINE_SPEC_CHANGED line
    assert "no last-year price from you" in body                    # BASELINE_NOT_FOR_VENDOR line
    assert "Payment: 45 days" in body and "MOQ:" in body             # reading-B term candidates
    assert kinds.count("FREIGHT") == 1                              # one freight question listing the lines
    fr = next(i for i in a["items"] if i["kind"] == "FREIGHT")
    assert len(fr["lines"]) > 1 and "our decision changes if freight exceeds ₹" in body
    assert "Freight is never taken from last year" in body          # DL-8
    assert "prices, terms, both, or neither" in body


def test_pack_edit_approve_outbox_and_lock(processed):
    c, app, rid, v1, v5 = processed
    p = c.post(f"/rfx/{rid}/vendors/{v5}/clarification-pack").json()
    edited = p["body"].replace("Regards,", "Many thanks,")
    assert c.put(f"/clarification-packs/{p['pack_id']}", json={"body": edited}).status_code == 200
    r = c.post(f"/clarification-packs/{p['pack_id']}/approve", json={"actor": "priya"}).json()
    assert r["status"] == "in_outbox"
    with app.state.session_factory() as s:
        om = s.get(OutboxMessage, r["outbox_message_id"])
        assert om.kind == "CLARIFICATION" and "Many thanks," in om.body and om.subject.startswith("Clarification requested")
    assert c.put(f"/clarification-packs/{p['pack_id']}", json={"body": "x"}).status_code == 409
    assert c.post(f"/clarification-packs/{p['pack_id']}/approve", json={"actor": "priya"}).status_code == 409
    actions = [e["action"] for e in c.get(f"/rfx/{rid}/audit").json()]
    assert {"CLARIFICATION_PACK_GENERATED", "CLARIFICATION_PACK_EDITED", "CLARIFICATION_PACK_APPROVED"} <= set(actions)


def test_reference_confirmation_terms_marks_reading_b(processed):
    c, app, rid, v1, v5 = processed
    with app.state.session_factory() as s:
        ref = s.query(Reference).filter_by(vendor_id=v5).one()
        assert ref.interpretation == "AMBIGUOUS"
        assert all(not x.get("applied") for x in ref.candidates)
    c.post(f"/rfx/{rid}/resolutions", json={"vendor_id": v5, "type": "REFERENCE_CONFIRMATION", "choice": "terms",
                                            "reason": "vendor phone call 4 Nov"})
    with app.state.session_factory() as s:
        ref = s.query(Reference).filter_by(vendor_id=v5).one()
        assert ref.interpretation == "CONFIRMED_TERMS"
        b = [x for x in ref.candidates if x["reading"] == "B_terms"]
        assert b and all(x["applied"] and x["status"] == "ASSUMED" for x in b)
        assert all(x["term_type"] != "FREIGHT" for x in b)
    grid = c.get(f"/rfx/{rid}/comparison").json()  # 'terms' never prices a line
    assert all(r["cells"][str(v5)]["status"] != "ASSUMED" or "BASELINE_REFERENCE" not in r["cells"][str(v5)]["reasons"]
               for r in grid["rows"])
    # the pack no longer asks about the closed reference
    p = c.post(f"/rfx/{rid}/vendors/{v5}/clarification-pack").json()
    assert "REFERENCE" not in [i["kind"] for i in p["items"]]


def test_documents_list_and_open_originals(processed):
    c, app, rid, v1, v5 = processed
    docs = c.get(f"/rfx/{rid}/vendors/{v5}/documents").json()
    names = [d["filename"] for d in docs]
    assert "Sahyadri_ISO9001.pdf" in names and "(email body)" in names
    pdf = c.get(next(d["url"] for d in docs if d["filename"] == "Sahyadri_ISO9001.pdf").removeprefix("/api"))
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")
    body = c.get(f"/rfx/{rid}/vendors/{v5}/file?name=(email body)")
    assert SENTENCE in body.text
    assert c.get(f"/rfx/{rid}/vendors/{v5}/file?name=nope.pdf").status_code == 404
