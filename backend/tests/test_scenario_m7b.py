"""M7b: freight-aware selection + break-even (DL-25), eligibility filters (DL-3/14/29), decision
sensitivity (DL-28), savings (§5.9), FX/billed-weight exposure (DL-30/31), readiness + acknowledgement
(AWD-3), staleness (AWD-7), and oracle parity over 20 parameter combinations (AWD AC)."""
import itertools
from decimal import ROUND_HALF_UP, Decimal

import pytest
from fastapi.testclient import TestClient

from app.analysis.scenario import ScenarioParams, run_scenario
from app.db.models import EligibilityResult, Invitation, NormalizedQuote, Question, Response, Rfx, RfxLine, Vendor
from app.main import create_app

# line → (annual_qty, food_contact)
LINES = {1: (1000, False), 2: (2000, False), 3: (500, False), 4: (1500, True), 5: (800, False), 6: (1200, False)}
# (line, vendor) → (unit, status, freight_basis, freight, reasons, flags, weight_source, trace)
F = "INCLUDED"
QUOTES = {
    (1, "V1"): ("10.0000", "VERIFIED", F, "0", [], [], None, []),
    (1, "V5"): ("8.0000", "ASSUMED", "UNKNOWN", None, ["GST_PER_RFX_BASIS"], [], None, []),           # FREIGHT_DEPENDENT, BE 2
    (1, "V2"): ("9.0000", "ASSUMED", "STATED", "1.5000", ["FX_RATE"], ["FX"], None, []),             # landed 10.5
    (2, "V1"): ("9.0000", "VERIFIED", F, "0", [], [], None, []),
    (2, "V5"): ("9.5000", "ASSUMED", "UNKNOWN", None, ["GST_PER_RFX_BASIS"], [], None, []),           # V1 robust
    (3, "V5"): ("7.0000", "ASSUMED", "UNKNOWN", None, ["REFERENCE_WEIGHT"], [], "SKU_REFERENCE", []),  # K empty
    (4, "V1"): ("12.0000", "VERIFIED", F, "0", [], [], None, []),
    (4, "V2"): ("11.0000", "ASSUMED", "STATED", "0.5000", ["FX_RATE"], ["FX"], None, []),
    (4, "V5"): (None, "UNRESOLVED", "UNKNOWN", None, ["UNIT_SUSPECT"], [], None,
                [{"step": "plausibility", "suggestion": {"divide_by": "100", "suggested_unit_price": "10.0000"}}]),
    (5, "V1"): ("6.0000", "VERIFIED", F, "0", [], [], None, []),
    (5, "V2"): ("5.0000", "NEEDS_REVIEW", "STATED", "0.2000", ["OUTLIER"], ["FX"], None, []),
    (6, "V1"): ("4.0000", "VERIFIED", F, "0", [], [], None, []),
    (6, "V2"): ("3.5000", "ASSUMED", "STATED", "0.5000", ["FX_RATE"], ["FX"], None, []),             # landed 4.0 tie with V1
}
# vendor → {requirement_key: state}; Q-QUAL (ALL, quality), Q-FOOD (food_contact lines), Q-PAY (commercial)
ELIG = {"V1": {"Q-QUAL": "PASS", "Q-FOOD": "UNVERIFIED", "Q-PAY": "PASS"},
        "V2": {"Q-QUAL": "UNVERIFIED", "Q-FOOD": "PASS", "Q-PAY": "PASS"},
        "V5": {"Q-QUAL": "PASS", "Q-FOOD": "PASS", "Q-PAY": "FAIL"}}
BASELINE = {1: {"unit_price_inr_ex_gst": "11.0000", "freight_basis": "INCLUDED"},
            2: {"unit_price_inr_ex_gst": "9.5000", "freight_basis": "INCLUDED"},
            4: {"unit_price_inr_ex_gst": "12.5000", "freight_basis": "UNKNOWN"}}


def _landed(unit, basis, freight):
    if unit is None or basis == "UNKNOWN":
        return None
    return str((Decimal(unit) + Decimal(freight or 0)).quantize(Decimal("0.0001")))


def build(tmp_path, with_questions=True):
    data = tmp_path / "app_data"; data.mkdir()
    app = create_app(env={"APP_DATA_ROOT": str(data), "APP_EVAL_ROOT_HINT": str(tmp_path / "eval")})
    sf = app.state.session_factory
    with sf.begin() as s:
        r = Rfx(title="M7b RFx", kind="primary", origin="COPILOT_LIVE", status="sent", response_basis={}); s.add(r); s.flush()
        lid = {}
        for n, (qty, food) in LINES.items():
            l = RfxLine(rfx_id=r.id, line_no=n, sku_code=f"S{n}", description="box", item_type="RSC", dims_mm={}, ply=3,
                        flute_profile="B", layers=[], annual_qty=qty, food_contact=food); s.add(l); s.flush(); lid[n] = l.id
        vid = {}
        for name in ("V1", "V2", "V5", "V3"):
            v = Vendor(name=name, contact_email=f"{name}@x"); s.add(v); s.flush(); vid[name] = v.id
            s.add(Invitation(rfx_id=r.id, vendor_id=v.id, status="AWAITING_RESPONSE" if name == "V3" else "RESPONDED"))
            if name != "V3":
                cov = sum(1 for (n, vn), q in QUOTES.items() if vn == name)
                s.add(Response(rfx_id=r.id, vendor_id=v.id, submissions=[], coverage_count=cov))
        for (n, vn), (u, st, fb, fr, rs, fl, ws, tr) in QUOTES.items():
            land = _landed(u, fb, fr)
            s.add(NormalizedQuote(rfx_line_id=lid[n], vendor_id=vid[vn], unit_price_inr_ex_gst=u, unit_status=st,
                                  unit_reasons=rs, landed_inr_ex_gst=land,
                                  landed_status=st if land else ("NOT_CONVERTIBLE" if u else st), freight_basis=fb,
                                  freight_inr_per_box=fr, flags=fl, weight_source=ws, trace=tr, fingerprint="f"))
        if with_questions:
            qids = {}
            for key, sec, app_ in (("Q-QUAL", "QUALITY", "ALL"), ("Q-FOOD", "QUALITY", "LINES_WITH_FLAG(food_contact)"),
                                   ("Q-PAY", "COMMERCIAL", "ALL")):
                q = Question(rfx_id=r.id, section=sec, requirement_key=key, applicability=app_, text=key, answer_type="yes_no",
                             mandatory=True); s.add(q); s.flush(); qids[key] = q.id
            for vn, per in ELIG.items():
                for key, state in per.items():
                    s.add(EligibilityResult(vendor_id=vid[vn], question_id=qids[key], state=state, reason=f"{key} {state.lower()}"))
        rid = r.id
    return app, sf, rid, vid


def awards(res):
    return {a["line_no"]: (a["vendor"], a["price_on_basis_inr"], a["freight_status"]) for a in res["awards"]}


def test_freight_aware_selection_and_break_even(tmp_path):
    _, sf, rid, vid = build(tmp_path, with_questions=False)
    r = run_scenario(sf, rid, ScenarioParams())  # formal default basis = freight_aware (DL-25)
    assert r["basis"] == "freight_aware"
    aw = awards(r)
    assert aw[1] == ("V5", "8.0000", "FREIGHT_DEPENDENT")   # best_U 8 < best_K 10 (V1 delivered)
    assert next(a for a in r["awards"] if a["line_no"] == 1)["break_even_inr_per_box"] == "2.0000"
    assert aw[2] == ("V1", "9.0000", "ROBUST")              # V1 delivered beats V5's unit price: no flag
    assert aw[3] == ("V5", "7.0000", "FREIGHT_UNKNOWN_ALL")  # K empty: no break-even
    assert aw[6] == ("V1", "4.0000", "LANDED")               # landed tie 4.0: VERIFIED beats ASSUMED (tie-break)
    assert {d["line_no"] for d in r["freight_dependent_lines"]} == {1}
    assert r["freight_dependent_lines"][0]["against"] == "V1"
    unit = run_scenario(sf, rid, ScenarioParams(basis="unit"))
    assert awards(unit)[6][0] == "V2" and awards(unit)[2][0] == "V1"
    landed = run_scenario(sf, rid, ScenarioParams(basis="landed"))
    assert awards(landed)[1][0] == "V1" and 3 in [u["line_no"] for u in landed["uncovered_lines"]]
    assert run_scenario(sf, rid, ScenarioParams(context="exploratory"))["basis"] == "unit"


def test_eligibility_strict_inclusive_scope_and_line_gating(tmp_path):
    _, sf, rid, vid = build(tmp_path)
    strict = run_scenario(sf, rid, ScenarioParams(basis="unit"))
    assert [x["vendor"] for x in strict["ineligible_vendors"]["unverified"]] == ["V2"]  # never called Failed
    assert strict["ineligible_vendors"]["failed"] == []          # V5 commercial FAIL is outside the quality scope (DL-14)
    assert awards(strict)[1][0] == "V5"
    # line 4 is food-contact: V1 food-grade Unverified → gated under strict; V2 ineligible; V5 unresolved
    assert 4 in [u["line_no"] for u in strict["uncovered_lines"]]
    assert any(e["line_no"] == 4 and e["vendor"] == "V1" and "DL-29" in e["reason"] for e in strict["exclusions"])
    allm = run_scenario(sf, rid, ScenarioParams(basis="unit", eligibility_scope="all_mandatory"))
    assert [x["vendor"] for x in allm["ineligible_vendors"]["failed"]] == ["V5"]
    assert allm["ineligible_vendors"]["failed"][0]["state"] == "Failed"
    incl = run_scenario(sf, rid, ScenarioParams(basis="unit", eligibility_mode="inclusive"))
    assert awards(incl)[4][0] == "V2" and incl["ineligible_vendors"] == {"failed": [], "unverified": []}
    none = run_scenario(sf, rid, ScenarioParams(basis="unit", eligibility_mode="none", eligibility_scope="all_mandatory"))
    assert awards(none)[1][0] == "V5"


def test_tie_break_pass_over_unverified(tmp_path):
    _, sf, rid, _ = build(tmp_path)
    r = run_scenario(sf, rid, ScenarioParams(eligibility_mode="inclusive"))
    assert awards(r)[6] == ("V1", "4.0000", "LANDED")  # V1 Passed beats V2 Unverified at equal landed cost
    assert "Passed over Unverified" in r["tie_break"]


def test_decision_sensitivity(tmp_path):
    _, sf, rid, _ = build(tmp_path, with_questions=False)
    r = run_scenario(sf, rid, ScenarioParams(basis="unit"))
    sens = {d["line_no"]: d for d in r["decision_sensitive_lines"]}
    # (a) line 4: V5's UNIT_SUSPECT suggestion ₹10 would beat V2's ₹11 → ₹1 × 1500 = ₹1500/yr
    a = next(i for i in sens[4]["inputs"] if i["kind"] == "UNRESOLVED_CANDIDATE")
    assert a["vendor"] == "V5" and a["annual_inr_delta"] == "1500"
    # (b) line 5: excluded NEEDS_REVIEW V2 ₹5 would beat V1 ₹6 → ₹800/yr
    b = next(i for i in sens[5]["inputs"] if i["kind"] == "EXCLUDED_NEEDS_REVIEW")
    assert b["vendor"] == "V2" and b["annual_inr_delta"] == "800"
    # (c) line 4 winner V2 is ASSUMED FX: a 9.09% rise flips it to V1 (12/11 − 1)
    c = next(i for i in sens[4]["inputs"] if i["kind"] == "ASSUMED_FX")
    assert c["flip_margin_pct"] == "9.09"
    # (d) freight-aware: the dependent line is sensitive with its break-even
    fa = run_scenario(sf, rid, ScenarioParams())
    d = next(i for x in fa["decision_sensitive_lines"] if x["line_no"] == 1 for i in x["inputs"] if i["kind"] == "UNKNOWN_FREIGHT")
    assert d["break_even_inr_per_box"] == "2.0000"
    assert 2 not in {x["line_no"] for x in r["decision_sensitive_lines"]}  # nothing uncertain could flip line 2


def test_savings_definitions(tmp_path):
    _, sf, rid, _ = build(tmp_path, with_questions=False)
    r = run_scenario(sf, rid, ScenarioParams(basis="unit"), BASELINE)
    ly = r["savings"]["vs_last_year"]
    # unit basis, A = {1:V5 8, 2:V1 9, 3:V5 7, 4:V2 11, 5:V1 6, 6:V2 3.5}; A_b = {1, 2, 4}
    assert ly["lines"] == 3 and ly["of_awarded"] == 6
    assert ly["baseline_spend_inr"] == str(11000 + 19000 + 18750)
    assert ly["savings_inr"] == str((11000 + 19000 + 18750) - (8000 + 18000 + 16500))
    assert ly["lines_without_comparable_baseline"] == [3, 5, 6]
    assert set(ly["freight_basis_caveat_lines"]) == {1, 4}  # freight basis differs from last year's
    fa = run_scenario(sf, rid, ScenarioParams(), BASELINE)["savings"]["vs_last_year"]
    assert fa["lines"] == 2 and 4 in fa["lines_without_comparable_baseline"]  # UNKNOWN-freight baseline not comparable
    assert fa["freight_unknown_lines"] == [1] and fa["bound_note"]
    bs = r["savings"]["vs_best_single_vendor"]
    assert bs["vendor"] == "V1" and bs["lines"] == 5 and bs["lines_not_covered"] == [3]   # V1 covers the most lines
    assert bs["statement"] == "vs V1 on the 5 of 6 awarded lines V1 covers"


def test_exposures(tmp_path):
    _, sf, rid, _ = build(tmp_path, with_questions=False)
    r = run_scenario(sf, rid, ScenarioParams(basis="unit"))
    fx = r["exposures"]["fx"]
    assert fx == [{"vendor": "V2", "awarded_spend_inr": "20700", "per_1pct_inr": "207",
                   "statement": "each 1% USD/INR move changes V2-awarded spend by ₹207"}]  # 16500 + 4200
    bw = r["exposures"]["billed_weight"]
    assert bw["lines"] == [3] and bw["per_1pct_inr"] == "35"


def test_readiness_ack_and_staleness(tmp_path):
    app, sf, rid, vid = build(tmp_path, with_questions=False)
    c = TestClient(app)
    sc = c.post(f"/rfx/{rid}/scenarios", json={}).json()
    rd = c.get(f"/scenarios/{sc['scenario_id']}/readiness").json()
    kinds = {i["kind"] for i in rd["items"]}
    assert {"AWAITING_RESPONSE", "FREIGHT_DEPENDENT", "DECISION_SENSITIVE", "FX_EXPOSURE", "BILLED_WEIGHT_EXPOSURE"} <= kinds
    assert rd["requires_acknowledgement"] and rd["can_acknowledge"]
    ack = c.post(f"/scenarios/{sc['scenario_id']}/acknowledge", json={"actor": "priya", "reason": "freight to follow"}).json()
    audit = c.get(f"/rfx/{rid}/audit").json()
    assert any(e["action"] == "READINESS_ACK" and e["id"] == ack["audit_event_id"] for e in audit)
    memo = c.post(f"/scenarios/{sc['scenario_id']}/memo").json()["memo_markdown"]
    assert "FREIGHT_DEPENDENT (break-even ₹2.0000/box)" in memo and "each 1% USD/INR move" in memo
    assert "ACKNOWLEDGED by priya" in memo and "DRAFT" not in memo
    # exploratory results cannot be acknowledged
    ex = c.post(f"/rfx/{rid}/scenarios", json={"context": "exploratory"}).json()
    assert c.post(f"/scenarios/{ex['scenario_id']}/acknowledge", json={"actor": "priya"}).status_code == 409


def test_oracle_parity_20_combinations(tmp_path):
    """Independent re-implementation of AWD-1 / §5.4 selection compared on 20 parameter combinations."""
    _, sf, rid, vid = build(tmp_path)
    name = {v: k for k, v in vid.items()}
    combos = list(itertools.product(["cheapest_per_line", "single_vendor"], ["freight_aware", "unit", "landed"],
                                    ["strict", "inclusive", "none"], ["quality", "all_mandatory"]))
    picked = [combos[i] for i in range(0, len(combos), 2)][:18] + [combos[1], combos[3]]
    assert len(picked) == 20
    for strategy, basis, mode, scope in picked:
        p = ScenarioParams(strategy=strategy, vendor_id=vid["V1"] if strategy == "single_vendor" else None,
                           basis=basis, eligibility_mode=mode, eligibility_scope=scope)
        got = run_scenario(sf, rid, p)
        exp = _oracle(strategy, basis, mode, scope)
        assert {n: (a[0], a[1]) for n, a in awards(got).items()} == exp["awards"], (strategy, basis, mode, scope)
        assert got["total_annual_spend_inr"] == exp["total"], (strategy, basis, mode, scope)
        assert {d["line_no"]: d["break_even_inr_per_box"] for d in got["freight_dependent_lines"]} == exp["dependent"]


def _oracle(strategy, basis, mode, scope):
    ok_states = {"strict": {"PASS"}, "inclusive": {"PASS", "UNVERIFIED"}, "none": {"PASS", "UNVERIFIED", "FAIL"}}[mode]

    def vendor_state(v):
        keys = ["Q-QUAL"] if scope == "quality" else ["Q-QUAL", "Q-PAY"]
        st = [ELIG[v][k] for k in keys]
        return "FAIL" if "FAIL" in st else "UNVERIFIED" if "UNVERIFIED" in st else "PASS"

    out, total, dependent = {}, Decimal(0), {}
    for n, (qty, food) in LINES.items():
        K, U = [], []
        for (ln, v), (u, st, fb, fr, *_rest) in QUOTES.items():
            if ln != n or st not in ("VERIFIED", "EXTRACTED", "ASSUMED") or u is None:
                continue
            if strategy == "single_vendor" and v != "V1":
                continue
            if mode != "none":
                if vendor_state(v) not in ok_states:
                    continue
                if food and ELIG[v]["Q-FOOD"] not in ok_states - {"FAIL"}:
                    continue
            rank = (0 if vendor_state(v) == "PASS" else 1, 0 if st == "VERIFIED" else 1, v)
            unit = Decimal(u)
            if basis == "unit":
                K.append((unit, rank, v))
            elif fb == "UNKNOWN":
                if basis == "freight_aware":
                    U.append((unit, rank, v))
            else:
                K.append((unit + Decimal(fr), rank, v))
        bk, bu = min(K, default=None), min(U, default=None)
        if bk and (not bu or bk[0] <= bu[0]):
            win = bk
        elif bu:
            win = bu
            if bk:
                dependent[n] = str((bk[0] - bu[0]).quantize(Decimal("0.0001")))
        else:
            continue
        spend = (win[0] * qty).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        out[n] = (win[2], str(win[0].quantize(Decimal("0.0001"))))
        total += spend
    return {"awards": out, "total": str(total), "dependent": dependent}
