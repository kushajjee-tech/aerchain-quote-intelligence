"""M7a: minimal deterministic cheapest-per-line / single-vendor scenario."""
from tests.test_comparison_m5a import setup


def test_cheapest_per_line_formal(tmp_path):
    c, rid, v1, v5, v2 = setup(tmp_path, final=True)
    r = c.post(f"/rfx/{rid}/scenarios", json={}).json()
    aw = {a["line_no"]: a for a in r["awards"]}
    assert aw[1]["vendor_id"] == v5 and aw[1]["unit_price_inr_ex_gst"] == "8.0000"
    assert aw[2]["vendor_id"] == v1                                        # V5 NEEDS_REVIEW excluded (DL-16)
    assert {"line_no": 2, "vendor": "V5", "reason": "NEEDS_REVIEW", "detail": ""} in r["exclusions"]
    assert r["uncovered_lines"] == [{"line_no": 3, "sku": "S3"}]           # never awarded to an excluded cell
    assert r["total_annual_spend_inr"] == "20000" and r["per_vendor_spend_inr"] == {"V1": "12000", "V5": "8000"}
    assert r["awaiting_response"] == ["V2"] and r["caveats"]["freight_unknown_lines"] == [1]
    again = c.post(f"/rfx/{rid}/scenarios", json={}).json()
    assert {k: v for k, v in again.items() if k != "scenario_id"} == {k: v for k, v in r.items() if k != "scenario_id"}


def test_needs_review_override_and_exploratory(tmp_path):
    c, rid, v1, v5, _ = setup(tmp_path, final=True)
    assert c.post(f"/rfx/{rid}/scenarios", json={"include_needs_review": True}).status_code == 409
    # an override_id that names no audited NEEDS_REVIEW override is refused (DL-16)
    assert c.post(f"/rfx/{rid}/scenarios", json={"include_needs_review": True, "override_id": 1}).status_code == 409
    r = c.post(f"/rfx/{rid}/scenarios", json={"include_needs_review": True, "override_reason": "vendor confirmed by phone"}).json()
    assert next(a for a in r["awards"] if a["line_no"] == 2)["vendor_id"] == v5
    assert r["needs_review_cells_included"] == [{"line_no": 2, "vendor": "V5", "value": "5.0000", "money_at_risk_inr": "5000"}]
    audit = c.get(f"/rfx/{rid}/audit").json()
    ov = next(e for e in audit if e["action"] == "NEEDS_REVIEW_OVERRIDE")
    assert ov["id"] == r["params"]["override_id"] and ov["after"]["cells"][0]["money_at_risk_inr"] == "5000"
    again = c.post(f"/rfx/{rid}/scenarios", json={"include_needs_review": True, "override_id": ov["id"]}).json()
    assert again["awards"] == r["awards"]
    e = c.post(f"/rfx/{rid}/scenarios", json={"context": "exploratory", "include_needs_review": True}).json()
    assert next(a for a in e["awards"] if a["line_no"] == 2)["vendor_id"] == v5


def test_single_vendor(tmp_path):
    c, rid, v1, *_ = setup(tmp_path, final=True)
    r = c.post(f"/rfx/{rid}/scenarios", json={"strategy": "single_vendor", "vendor_id": v1}).json()
    assert [a["line_no"] for a in r["awards"]] == [1, 2] and r["uncovered_lines"] == [{"line_no": 3, "sku": "S3"}]
    assert r["total_annual_spend_inr"] == "22000"
