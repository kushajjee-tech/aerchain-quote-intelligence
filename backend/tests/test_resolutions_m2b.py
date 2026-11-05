"""M2b: buyer resolutions, audit and sticky global recompute (PRD §6.5, VAL-5, REV-1/2/4, DL-7, DL-9, DL-20)."""
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import AuditEvent, Invitation, Resolution, Response, Rfx, RfxLine, Vendor
from app.main import create_app
from app.normalize.engine import QuoteInput, ResponseContext, normalize_cell
from app.process.recompute import store_phase_a
from app.process.run import recompute_rfx

CTX = ResponseContext(gst_statement="STATED", gst_stated_exclusive=True)
LINE = {"line_no": 0, "item_type": "RSC", "annual_qty": 1000, "ply": 3}

# line → vendor → per-box price (None = reference cell with a same-vendor, same-spec candidate of 9)
PRICES = {
    1: {"V1": "10", "V2": "10.5", "V5": "1000"},   # V5: UNIT_SUSPECT (≥20× peers)
    2: {"V1": "9.5", "V2": "9.8", "V5": None},     # V5: "rest same as last year"
    3: {"V1": "10", "V2": "10", "V5": "10"},
    4: {"V1": "25", "V2": "10", "V5": "10"},       # V1: OUTLIER (2.5× peers)
}


def _cell(price):
    if price is None:
        q = QuoteInput(reference=True, reference_reason="REFERENCE_AMBIGUOUS", reference_candidate=Decimal("9"),
                       baseline_freight_basis="INCLUDED")
    else:
        q = QuoteInput(value=Decimal(price), unit_class="PER_BOX")
    return normalize_cell({**LINE}, q, CTX)


def _cells(prices, vid):
    out = {}
    for n, per in prices.items():
        for name, p in per.items():
            out.setdefault(str(vid[name]), {})[n] = _cell(p)
    return out


def setup(tmp_path):
    data = tmp_path / "app_data"; data.mkdir()
    app = create_app(env={"APP_DATA_ROOT": str(data), "APP_EVAL_ROOT_HINT": str(tmp_path / "eval")})
    sf = app.state.session_factory
    with sf.begin() as s:
        r = Rfx(title="T", kind="primary", origin="COPILOT_LIVE", status="sent", response_basis={}); s.add(r); s.flush()
        for n in PRICES:
            s.add(RfxLine(rfx_id=r.id, line_no=n, sku_code=f"S{n}", description="box", item_type="RSC", dims_mm={},
                          ply=3, flute_profile="B", layers=[], annual_qty=1000))
        vid = {}
        for name in ("V1", "V2", "V5"):
            v = Vendor(name=name, contact_email=f"{name}@x"); s.add(v); s.flush(); vid[name] = v.id
            s.add(Invitation(rfx_id=r.id, vendor_id=v.id, status="RESPONDED"))
            s.add(Response(rfx_id=r.id, vendor_id=v.id, submissions=[]))
        rid = r.id
    store_phase_a(sf, rid, _cells(PRICES, vid))
    recompute_rfx(sf, app.state.storage, rid)
    return TestClient(app), sf, app.state.storage, rid, vid


def _grid(c, rid):
    d = c.get(f"/rfx/{rid}/comparison").json()
    return {r["line_no"]: r["cells"] for r in d["rows"]}


def _resolve(c, rid, **kw):
    return c.post(f"/rfx/{rid}/resolutions", json=kw)


def test_accept_unit_suspect_suggestion_records_chosen_unit(tmp_path):
    c, sf, _, rid, vid = setup(tmp_path)
    g = _grid(c, rid)
    v5 = g[1][str(vid["V5"])]
    assert v5["status"] == "UNRESOLVED" and "UNIT_SUSPECT" in v5["reasons"] and v5["value"] is None
    queue = c.get(f"/rfx/{rid}/review").json()["items"]
    item = next(i for i in queue if i["line_no"] == 1 and i["vendor_id"] == vid["V5"])
    assert item["suggestion"] == {"divide_by": "100", "suggested_unit_price": "10.0000"}
    # REV-2: decision-sensitive items first, then by money at risk
    flags = [i["decision_sensitive"] for i in queue]
    assert flags == sorted(flags, reverse=True) and item["decision_sensitive"]
    r = _resolve(c, rid, vendor_id=vid["V5"], line_no=1, type="ACCEPT_SUGGESTION")
    assert r.status_code == 200 and r.json()["type"] == "CORRECT"
    v5 = _grid(c, rid)[1][str(vid["V5"])]
    assert v5["status"] == "VERIFIED" and v5["value"] == "10.0000"
    with sf() as s:
        actions = [e.action for e in s.scalars(select(AuditEvent).order_by(AuditEvent.id))]
        ev = s.scalar(select(AuditEvent).where(AuditEvent.action == "RESOLUTION_CORRECT"))
        assert ev.before["status"] == "UNRESOLVED" and ev.actor == "buyer" and "divide by 100" in ev.reason
    assert actions[-2:] == ["RESOLUTION_CORRECT", "RECOMPUTE"]


def test_accept_is_sticky_and_new_failure_flags_new_warning(tmp_path):
    c, sf, st, rid, vid = setup(tmp_path)
    v1 = _grid(c, rid)[4][str(vid["V1"])]
    assert v1["status"] == "NEEDS_REVIEW" and v1["reasons"] == ["OUTLIER"]
    assert _resolve(c, rid, vendor_id=vid["V1"], line_no=4, type="ACCEPT").status_code == 200
    v1 = _grid(c, rid)[4][str(vid["V1"])]
    assert v1["status"] == "VERIFIED" and v1["value"] == "25.0000" and "NEW_WARNING_AFTER_REVIEW" not in v1["flags"]
    recompute_rfx(sf, st, rid)  # recompute alone never undoes the resolution
    assert _grid(c, rid)[4][str(vid["V1"])]["status"] == "VERIFIED"
    # VAL-5: correcting peers changes V1's peer median; the new failure is a flag, not a downgrade
    for v in ("V2", "V5"):
        assert _resolve(c, rid, vendor_id=vid[v], line_no=4, type="CORRECT", value="0.5").status_code == 200
    v1 = _grid(c, rid)[4][str(vid["V1"])]
    assert v1["status"] == "VERIFIED" and v1["value"] == "25.0000"
    assert "NEW_WARNING_AFTER_REVIEW" in v1["flags"] and "UNIT_SUSPECT" in v1["reasons"]
    assert any(i["line_no"] == 4 and i["vendor_id"] == vid["V1"] for i in c.get(f"/rfx/{rid}/review").json()["items"])


def test_override_requires_reason_and_is_flagged(tmp_path):
    c, _, _, rid, vid = setup(tmp_path)
    assert _resolve(c, rid, vendor_id=vid["V2"], line_no=3, type="OVERRIDE", value="11").status_code == 422
    assert _resolve(c, rid, vendor_id=vid["V2"], line_no=3, type="CORRECT", value="abc").status_code == 422
    assert _resolve(c, rid, vendor_id=vid["V2"], line_no=3, type="OVERRIDE", value="30",
                    reason="negotiated by phone").status_code == 200
    cell = _grid(c, rid)[3][str(vid["V2"])]
    assert cell["status"] == "VERIFIED" and cell["value"] == "30.0000"
    assert {"OVERRIDE", "NEW_WARNING_AFTER_REVIEW"} <= set(cell["flags"])  # 3× peers → OUTLIER after review


def test_mark_missing_and_accept_without_candidate(tmp_path):
    c, _, _, rid, vid = setup(tmp_path)
    assert _resolve(c, rid, vendor_id=vid["V1"], line_no=3, type="MARK_MISSING", reason="line withdrawn").status_code == 200
    assert _grid(c, rid)[3][str(vid["V1"])] | {} == {**_grid(c, rid)[3][str(vid["V1"])], "status": "MISSING", "value": None}
    assert _resolve(c, rid, vendor_id=vid["V5"], line_no=2, type="ACCEPT").status_code == 422  # nothing to accept
    assert _resolve(c, rid, vendor_id=vid["V5"], line_no=9, type="ACCEPT").status_code == 422


def test_reference_confirmation_prices_and_neither(tmp_path):
    """T-EDGE-05c-B shape: only after the buyer confirms 'prices' does the same-vendor candidate count."""
    c, sf, _, rid, vid = setup(tmp_path)
    cell = _grid(c, rid)[2][str(vid["V5"])]
    assert cell["status"] == "UNRESOLVED" and "REFERENCE_AMBIGUOUS" in cell["reasons"] and cell["value"] is None
    assert _resolve(c, rid, vendor_id=vid["V5"], type="REFERENCE_CONFIRMATION", choice="prices").status_code == 422
    assert _resolve(c, rid, vendor_id=vid["V5"], type="REFERENCE_CONFIRMATION", choice="neither",
                    reason="call with vendor").status_code == 200
    assert _grid(c, rid)[2][str(vid["V5"])]["status"] == "UNRESOLVED"
    assert _resolve(c, rid, vendor_id=vid["V5"], type="REFERENCE_CONFIRMATION", choice="prices",
                    reason="vendor confirmed by email 3 Nov").status_code == 200
    cell = _grid(c, rid)[2][str(vid["V5"])]
    assert cell["status"] == "ASSUMED" and cell["value"] == "9.0000"
    assert "BASELINE_REFERENCE" in cell["reasons"] and "FREIGHT_BASIS_CHANGED" in cell["flags"]
    assert cell["freight_basis"] == "UNKNOWN"  # last year's freight never carried forward (DL-8)


def test_changed_source_makes_resolution_stale(tmp_path):
    c, sf, st, rid, vid = setup(tmp_path)
    _resolve(c, rid, vendor_id=vid["V1"], line_no=4, type="ACCEPT")
    assert _grid(c, rid)[4][str(vid["V1"])]["status"] == "VERIFIED"
    changed = {n: dict(per) for n, per in PRICES.items()}
    changed[4]["V1"] = "26"  # re-run read a different number
    store_phase_a(sf, rid, _cells(changed, vid))
    recompute_rfx(sf, st, rid, cause="re-run")
    assert _grid(c, rid)[4][str(vid["V1"])]["status"] == "NEEDS_REVIEW"  # review item reopens
    with sf() as s:
        r = s.scalar(select(Resolution).where(Resolution.type == "ACCEPT"))
        assert r.state == "stale"
        assert s.scalar(select(AuditEvent).where(AuditEvent.action == "RESOLUTION_STALE")).reason == "STALE_SOURCE_CHANGED"


def test_unchanged_source_carries_resolution_forward(tmp_path):
    c, sf, st, rid, vid = setup(tmp_path)
    _resolve(c, rid, vendor_id=vid["V1"], line_no=4, type="ACCEPT")
    store_phase_a(sf, rid, _cells(PRICES, vid))  # re-run with an identical read
    recompute_rfx(sf, st, rid, cause="re-run")
    assert _grid(c, rid)[4][str(vid["V1"])]["status"] == "VERIFIED"


def test_freight_estimate_resolves_freight_dependency(tmp_path):
    """DL-25 AC: entering a disclosed freight estimate removes FREIGHT_DEPENDENT and recomputes."""
    c, sf, _, rid, vid = setup(tmp_path)
    assert _resolve(c, rid, vendor_id=vid["V1"], type="FREIGHT_ESTIMATE", value="0.5").status_code == 422  # source required
    assert _resolve(c, rid, vendor_id=vid["V1"], type="FREIGHT_ESTIMATE", value="0.5",
                    reason="transporter quote 2 Nov").status_code == 200
    landed = {r["line_no"]: r["cells"] for r in c.get(f"/rfx/{rid}/comparison?basis=landed").json()["rows"]}
    assert landed[3][str(vid["V1"])] | {} == {**landed[3][str(vid["V1"])], "value": "10.5000", "status": "ASSUMED"}
    r = c.post(f"/rfx/{rid}/scenarios", json={"line_nos": [3]}).json()
    assert r["awards"][0]["freight_status"] == "FREIGHT_DEPENDENT" and r["awards"][0]["break_even_inr_per_box"] == "0.5000"
    for v, est in (("V2", "0.1"), ("V5", "0.2")):
        _resolve(c, rid, vendor_id=vid[v], type="FREIGHT_ESTIMATE", value=est, reason="transporter quote")
    assert c.get(f"/scenarios/{r['scenario_id']}").json()["stale"] is True  # cells_used changed (AWD-7)
    r2 = c.post(f"/rfx/{rid}/scenarios", json={"line_nos": [3]}).json()
    a = r2["awards"][0]
    assert (a["vendor"], a["price_on_basis_inr"], a["freight_status"]) == ("V2", "10.1000", "LANDED")
    assert r2["freight_dependent_lines"] == []


def test_acknowledged_award_superseded_on_change(tmp_path):
    c, sf, _, rid, vid = setup(tmp_path)
    sc = c.post(f"/rfx/{rid}/scenarios", json={"basis": "unit"}).json()
    ack = c.post(f"/scenarios/{sc['scenario_id']}/acknowledge", json={"actor": "priya"}).json()
    used = {(a["line_no"], a["vendor_id"]) for a in sc["awards"]}
    line, v = sorted(used)[0]
    _resolve(c, rid, vendor_id=v, line_no=line, type="OVERRIDE", value="9.99", reason="renegotiated")
    from app.db.models import AwardDecision
    with sf() as s:
        assert s.get(AwardDecision, ack["award_decision_id"]).superseded is True
    assert c.post(f"/scenarios/{sc['scenario_id']}/acknowledge", json={"actor": "priya"}).status_code == 409
    new = c.post(f"/scenarios/{sc['scenario_id']}/recompute").json()
    assert new["replaces"] == sc["scenario_id"]
    assert c.post(f"/scenarios/{new['scenario_id']}/acknowledge", json={"actor": "priya"}).status_code == 200
