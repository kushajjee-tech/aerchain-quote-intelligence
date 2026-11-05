"""M5a: comparison grid API — numbers only from stored cells, excluded statuses never shown as
numbers, landed basis respects unknown freight, awaiting vendors, best price under the formal policy."""
from fastapi.testclient import TestClient

from app.db.models import Invitation, NormalizedQuote, ProcessingSet, Response, Rfx, RfxLine, Vendor
from app.main import create_app


def _q(line_id, vendor_id, price, status, landed=None, landed_status=None, freight="UNKNOWN", flags=None):
    return NormalizedQuote(rfx_line_id=line_id, vendor_id=vendor_id, unit_price_inr_ex_gst=price, unit_status=status,
                           unit_reasons=[], landed_inr_ex_gst=landed, landed_status=landed_status or ("NOT_CONVERTIBLE" if landed is None else status),
                           freight_basis=freight, flags=flags or [], trace=[{"step": "as_quoted", "value": "x"}], fingerprint="f")


def setup(tmp_path, final=False):
    data = tmp_path / "app_data"; data.mkdir()
    app = create_app(env={"APP_DATA_ROOT": str(data), "APP_EVAL_ROOT_HINT": str(tmp_path / "eval")})
    sf = app.state.session_factory
    with sf.begin() as s:
        r = Rfx(title="Test RFx", kind="primary", origin="COPILOT_LIVE", status="sent", response_basis={}); s.add(r); s.flush()
        lines = []
        for n in (1, 2, 3):
            l = RfxLine(rfx_id=r.id, line_no=n, sku_code=f"S{n}", description="box", item_type="RSC", dims_mm={}, ply=3,
                        flute_profile="B", layers=[], annual_qty=1000); s.add(l); s.flush(); lines.append(l.id)
        vs = []
        for name in ("V1", "V5", "V2"):
            v = Vendor(name=name, contact_email=f"{name}@x"); s.add(v); s.flush(); vs.append(v.id)
            s.add(Invitation(rfx_id=r.id, vendor_id=v.id, status="AWAITING_RESPONSE" if name == "V2" else "RESPONDED"))
        for vid in vs[:2]:
            s.add(Response(rfx_id=r.id, vendor_id=vid, submissions=[]))
        v1, v5, _ = vs
        s.add_all([
            _q(lines[0], v1, "10.0000", "VERIFIED", landed="10.0000", freight="INCLUDED"),
            _q(lines[0], v5, "8.0000", "ASSUMED"),                        # cheaper on unit, freight unknown
            _q(lines[1], v1, "12.0000", "EXTRACTED", landed="12.0000", freight="INCLUDED"),
            _q(lines[1], v5, "5.0000", "NEEDS_REVIEW"),                   # excluded from best under formal policy
            _q(lines[2], v1, None, "MISSING"),
            _q(lines[2], v5, None, "UNRESOLVED"),
        ])
        if final:
            s.add(ProcessingSet(rfx_id=r.id, phase_b_status="final", snapshot_hash="h"))
        return TestClient(app), r.id, v1, v5, vs[2]


def test_unit_basis_values_statuses_best(tmp_path):
    c, rid, v1, v5, v2 = setup(tmp_path)
    d = c.get(f"/rfx/{rid}/comparison").json()
    assert d["provisional"] is True
    rows = {r["line_no"]: r for r in d["rows"]}
    assert rows[1]["best_vendor_id"] == v5                     # ASSUMED is includable
    assert rows[2]["best_vendor_id"] == v1                     # NEEDS_REVIEW not highlighted (DL-16)
    assert rows[3]["cells"][str(v1)] == {**rows[3]["cells"][str(v1)], "value": None, "status": "MISSING"}
    assert rows[3]["cells"][str(v5)]["value"] is None and rows[3]["best_vendor_id"] is None
    awaiting = next(v for v in d["vendors"] if v["vendor_id"] == v2)
    assert awaiting["state"] == "AWAITING_RESPONSE"
    assert all(r["cells"][str(v2)] == {"state": "AWAITING_RESPONSE", "value": None, "status": None} for r in d["rows"])


def test_landed_basis_never_shows_unknown_freight(tmp_path):
    c, rid, v1, v5, _ = setup(tmp_path, final=True)
    d = c.get(f"/rfx/{rid}/comparison?basis=landed").json()
    assert d["provisional"] is False
    row1 = next(r for r in d["rows"] if r["line_no"] == 1)
    assert row1["cells"][str(v5)]["value"] is None and row1["cells"][str(v5)]["status"] == "NOT_CONVERTIBLE"
    assert row1["best_vendor_id"] == v1


def test_bad_basis_and_unknown_rfx(tmp_path):
    c, rid, *_ = setup(tmp_path)
    assert c.get(f"/rfx/{rid}/comparison?basis=cheapest").status_code == 422
    assert c.get("/rfx/999/comparison").status_code == 404
