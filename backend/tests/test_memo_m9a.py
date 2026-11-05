"""M9a: draft memo numbers equal the scenario; uncovered, awaiting and exclusions listed; no model call."""
from decimal import Decimal

from app.award.memo import inr
from tests.test_comparison_m5a import setup


def test_inr_grouping():
    assert inr("40000000") == "₹4,00,00,000" and inr("12000") == "₹12,000" and inr("8.0000") == "₹8" and inr("6.0040") == "₹6.00"


def test_memo_matches_scenario(tmp_path):
    c, rid, *_ = setup(tmp_path, final=True)
    sc = c.post(f"/rfx/{rid}/scenarios", json={}).json()
    m = c.post(f"/scenarios/{sc['scenario_id']}/memo?title=Test%20RFx").json()["memo_markdown"]
    assert f"Total annual spend: **{inr(sc['total_annual_spend_inr'])}**" in m
    for v, amt in sc["per_vendor_spend_inr"].items():
        assert f"- {v}: {inr(amt)}" in m
    for a in sc["awards"]:
        assert f"| {a['line_no']} | {a['sku']} | {a['vendor']} | {inr(a['unit_price_inr_ex_gst'])} |" in m
    assert "Line 3 (S3): no includable quote." in m and "Awaiting response (not considered): V2." in m
    assert "Line 2, V5: NEEDS_REVIEW" in m and "excluded (formal policy)" in m and "DRAFT" in m
    assert c.post("/scenarios/999/memo").status_code == 404
