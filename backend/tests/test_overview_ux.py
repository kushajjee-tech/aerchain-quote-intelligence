"""UX spec support: Home overview (data-derived metrics, findings, blocker logic), finding review with audit,
RFx metadata, and the comparison's by-supplier summary (no partial sum shown as a total; never a false zero)."""
from tests.test_comparison_m5a import setup


def _overview(c, rid):
    r = c.get(f"/rfx/{rid}/overview")
    assert r.status_code == 200, r.text
    return r.json()


def test_overview_metrics_and_blockers_are_derived(tmp_path):
    c, rid, v1, v5, v2 = setup(tmp_path, final=True)
    d = _overview(c, rid)
    assert d["metrics"]["vendors_invited"] == 3 and d["metrics"]["vendors_responded"] == 2
    assert d["metrics"]["skus"] == 3 and d["metrics"]["annual_demand"] == 3000
    by = {(f["vendor_id"], f["kind"], f["severity"]): f for f in d["findings"]}
    withheld = by[(v5, "cells", "blocker")]                    # UNRESOLVED value → blocker, never a number
    assert withheld["lines"] == [3] and withheld["title"].startswith("Values withheld")
    review = by[(v5, "cells", "warning")]                       # NEEDS_REVIEW → warning
    assert review["lines"] == [2]
    assert (v1, "missing", "warning") in by                     # not quoted → disclosed, not zero
    assert d["metrics"]["open_blockers"] == sum(1 for f in d["findings"] if f["severity"] == "blocker")
    assert any(f["vendor_id"] == v2 for f in d["findings"])     # awaiting vendor surfaced
    assert {s["key"] for s in d["stages"]} == {"issued", "responses", "review", "comparison", "award"}
    assert d["rfx"]["demo"] is True


def test_finding_review_requires_reason_and_is_audited(tmp_path):
    c, rid, v1, v5, _ = setup(tmp_path, final=True)
    d = _overview(c, rid)
    blocker = next(f for f in d["findings"] if f["severity"] == "blocker")
    before = d["metrics"]["open_blockers"]
    url = f"/rfx/{rid}/findings/{blocker['id']}/review"
    assert c.post(url, json={"state": "rejected"}).status_code == 422             # reason required
    assert c.post(url, json={"state": "bogus"}).status_code == 422
    assert c.post(f"/rfx/{rid}/findings/nope/review", json={"state": "confirmed"}).status_code == 404
    assert c.post(url, json={"state": "confirmed"}).status_code == 200
    assert _overview(c, rid)["metrics"]["open_blockers"] == before               # confirmed stays open
    assert c.post(url, json={"state": "rejected", "comment": "misread"}).status_code == 200
    d2 = _overview(c, rid)
    assert d2["metrics"]["open_blockers"] == before - 1
    assert next(f for f in d2["findings"] if f["id"] == blocker["id"])["review"]["state"] == "rejected"
    hist = c.get(f"/rfx/{rid}/findings/{blocker['id']}/history").json()
    assert [(h["before"]["state"], h["after"]["state"]) for h in hist] == [("open", "confirmed"), ("confirmed", "rejected")]
    assert hist[-1]["reason"] == "misread"
    assert c.post(url, json={"state": "open"}).status_code == 200                # reopen keeps history
    assert _overview(c, rid)["metrics"]["open_blockers"] == before
    assert len(c.get(f"/rfx/{rid}/findings/{blocker['id']}/history").json()) == 3


def test_meta_update_is_audited_and_returned(tmp_path):
    c, rid, *_ = setup(tmp_path)
    r = c.put(f"/rfx/{rid}/meta", json={"code": "TEST-1", "plant": "Plant A"})
    assert r.status_code == 200 and r.json()["meta"]["code"] == "TEST-1"
    assert _overview(c, rid)["rfx"]["meta"]["plant"] == "Plant A"
    assert any(e["action"] == "RFX_METADATA_CHANGED" for e in c.get(f"/rfx/{rid}/audit").json())
    assert c.get("/rfx").json()[0]["meta"]["code"] == "TEST-1"


def test_vendor_summary_never_reports_partial_sum_as_total(tmp_path):
    c, rid, v1, v5, v2 = setup(tmp_path, final=True)
    s = {x["vendor_id"]: x for x in c.get(f"/rfx/{rid}/comparison").json()["vendor_summary"]}
    assert s[v1]["quoted"] == 2 and s[v1]["not_quoted"] == 1 and s[v1]["comparable"] == 2
    assert s[v1]["comparable_spend_inr"] == "22000" and s[v1]["complete_total_inr"] is None
    assert s[v5]["comparable"] == 1 and s[v5]["exceptions"] == 2              # NEEDS_REVIEW + UNRESOLVED
    assert s[v2]["quoted"] == 0 and s[v2]["comparable_spend_inr"] is None       # awaiting: no number at all
    rows = c.get(f"/rfx/{rid}/comparison").json()["rows"]
    assert all(r["baseline"] is None and r["best_vs_baseline_pct"] is None for r in rows)  # no seed baseline → none invented
