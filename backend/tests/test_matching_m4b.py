"""M4b: spec comparison (MAT-3, DL-6), AI match proposals + one-to-one (MAT-1/2/5), order-shuffle
determinism and peer independence (DL-9), ALTERNATE excluded by default with differences listed (AWD-5)."""
import random
from types import SimpleNamespace

import pytest

from app.ingest.evidence import EvidenceUnit
from app.ingest.extract import TextExtractionResult
from app.ingest.match_ai import MatchProposal, MatchProposals, propose_matches
from app.ingest.schemas import DocumentExtraction, Evidence, LineQuote, Price, SpecStated
from app.ingest.spec_diff import spec_diff
from app.ingest.verify import verify_line
from app.process.phase_a import phase_a
from app.process.recompute import store_phase_a
from app.process.run import recompute_rfx
from tests.test_resolutions_m2b import PRICES, _cells, _grid, _resolve, setup

LINE = {"line_no": 1, "sku_code": "PK-1", "description": "RSC 3-ply", "item_type": "RSC", "ply": 3, "flute_profile": "B",
        "dims_mm": {"L": 250, "W": 200, "H": 150}, "annual_qty": 1000, "blank_size_mm": None, "reference_unit_weight_g": None,
        "layers": [{"gsm": 150, "bf": 20}, {"gsm": 120, "bf": 16}, {"gsm": 150, "bf": 20}], "food_contact": False}
EV = Evidence(unit_ids=["D2:S!A1"], quote="spec")


def _spec(**kw):
    return SpecStated(evidence=EV, **kw)


@pytest.mark.parametrize("spec,verdict,fields", [
    (None, "NOT_RESTATED", []),
    (dict(ply=3, flute_profile="B", dims_as_stated="250 x 200 x 150 mm", layer_gsm=[150, 120, 150], bf_as_stated="20 BF"), "COMPLIANT", []),
    (dict(layer_gsm=[143, 120, 150]), "COMPLIANT", []),          # 4.7% lower: within the 5% tolerance
    (dict(layer_gsm=[140, 120, 150]), "ALTERNATE", ["gsm_layer_1"]),  # 6.7% lower
    (dict(layer_gsm=[180, 150, 180]), "COMPLIANT", []),          # heavier board is not an alternate
    (dict(ply=5, flute_profile="BC"), "ALTERNATE", ["ply", "flute_profile"]),
    (dict(dims_as_stated="252x198x150"), "COMPLIANT", []),       # within ±2 mm
    (dict(dims_as_stated="253x200x150"), "ALTERNATE", ["dims_mm"]),
    (dict(bf_as_stated="18/16/18"), "ALTERNATE", ["bf_layer_1", "bf_layer_3"]),
    (dict(bf_as_stated="18 BF"), "ALTERNATE", ["bf"]),
    (dict(layer_gsm=[150, 150]), "ALTERNATE", ["layer_count"]),
])
def test_spec_diff(spec, verdict, fields):
    v, diffs = spec_diff(LINE, _spec(**spec) if spec is not None else None)
    assert v == verdict and [d["field"] for d in diffs] == fields
    for d in diffs:
        if "tolerance" in d:
            assert d["tolerance"]["label"].endswith("not validated")  # constants cited with their label


UNITS = {u.id: u for u in [EvidenceUnit("D2:S!A1", "D2", "cell", {}, "spec"),
                           EvidenceUnit("D2:S!B1", "D2", "cell", {}, "12.50"),
                           EvidenceUnit("D2:S!B2", "D2", "cell", {}, "13.00")]}


def _lq(ref, price_unit, desc="Shipper", code=None, spec=None):
    return LineQuote(vendor_line_ref=ref, description_as_stated=desc, item_code=code, unit_class="PER_BOX", unit_source="STATED",
                     unit_as_stated="per pc", spec_as_stated=spec,
                     price=Price(value_as_stated=UNITS[price_unit].text, value=float(UNITS[price_unit].text),
                                 currency_source="STATED", evidence=Evidence(unit_ids=[price_unit], quote=UNITS[price_unit].text)))


def _result(*lqs):
    ex = DocumentExtraction(line_quotes=list(lqs), gst_statement="STATED")
    return TextExtractionResult(ex, [verify_line(l, UNITS) for l in lqs], [], [], UNITS, {"D2": "q.xlsx"})


RFX = {"response_basis": {"gst_treatment": "prices exclusive of GST"}, "questionnaire": [], "lines": [
    LINE, {**LINE, "line_no": 2, "sku_code": "PK-2", "dims_mm": {"L": 400, "W": 300, "H": 300}}]}


def test_alternate_and_not_restated_flags_with_differences():
    cells = {c.line_no: c.cell for c in phase_a(RFX, [_result(
        _lq("1", "D2:S!B1", code="PK-1", spec=_spec(layer_gsm=[120, 100, 120])),
        _lq("2", "D2:S!B2", code="PK-2"))])}
    assert "ALTERNATE" in cells[1].flags
    sd = next(t for t in cells[1].trace if t["step"] == "spec_diff")
    assert sd["verdict"] == "ALTERNATE" and len(sd["differences"]) == 3
    assert "NOT_RESTATED" in cells[2].flags and "ALTERNATE" not in cells[2].flags


def test_two_vendor_lines_on_one_rfx_line_is_match_conflict():
    cells = {c.line_no: c.cell for c in phase_a(RFX, [_result(_lq("1", "D2:S!B1", code="PK-1"), _lq("9", "D2:S!B2", code="PK 1"))])}
    assert str(cells[1].unit_status) == "UNRESOLVED" and "MATCH_CONFLICT" in cells[1].reasons


def test_ai_match_low_is_unresolved_and_high_is_matched():
    res = _result(_lq("a", "D2:S!B1", desc="Big brown box 40 by 30"), _lq("b", "D2:S!B2", desc="small shipper"))
    cells = {c.line_no: c.cell for c in phase_a(RFX, [res], ai_matches={
        "a": {"line_no": 2, "confidence": "HIGH", "reason": "dims"}, "b": {"line_no": 1, "confidence": "LOW", "reason": "guess"}})}
    assert cells[2].unit_price_inr_ex_gst is not None and "MATCH_LOW" not in cells[2].reasons
    assert str(cells[1].unit_status) == "UNRESOLVED" and "MATCH_LOW" in cells[1].reasons
    none = {c.line_no: c.cell for c in phase_a(RFX, [res])}
    assert all(str(c.unit_status) == "MISSING" for c in none.values())  # never placed by row position


def test_propose_matches_is_validated():
    unmatched = _result(_lq("a", "D2:S!B1"), _lq("b", "D2:S!B2")).lines
    fake = SimpleNamespace(structured=lambda *a, **k: MatchProposals(proposals=[
        MatchProposal(vendor_line_ref="a", rfx_line_no=1, confidence="HIGH", reason="x"),
        MatchProposal(vendor_line_ref="a", rfx_line_no=2, confidence="HIGH", reason="dup ref ignored"),
        MatchProposal(vendor_line_ref="zz", rfx_line_no=2, confidence="HIGH", reason="unknown ref"),
        MatchProposal(vendor_line_ref="b", rfx_line_no=99, confidence="HIGH", reason="no such line")]))
    out = propose_matches(fake, RFX["lines"], unmatched, taken={1})
    assert out == {"a": {"line_no": 1, "confidence": "HIGH", "reason": "x", "conflicts_with_deterministic": True}}


def test_order_shuffle_determinism(tmp_path):
    """B2/DL-9: 10 random completion orders → identical snapshot hash."""
    c, sf, st, rid, vid = setup(tmp_path)
    cells = _cells(PRICES, vid)
    hashes = set()
    for seed in range(10):
        order = list(cells)
        random.Random(seed).shuffle(order)
        for v in order:  # vendors complete one at a time, in random order
            store_phase_a(sf, rid, {v: cells[v]})
        hashes.add(recompute_rfx(sf, st, rid))
    assert len(hashes) == 1


def test_peer_independence(tmp_path):
    """A vendor's Phase B status change never changes another vendor's peer reference."""
    c, sf, st, rid, vid = setup(tmp_path)

    def refs():
        from app.db.models import NormalizedQuote
        with sf() as s:
            return {(q.vendor_id, q.rfx_line_id): next((t.get("reference") for t in q.trace if t.get("step") == "plausibility"), None)
                    for q in s.query(NormalizedQuote).all() if q.vendor_id != vid["V1"]}
    before = refs()
    _resolve(c, rid, vendor_id=vid["V1"], line_no=4, type="ACCEPT")  # V1 NEEDS_REVIEW → VERIFIED
    assert _grid(c, rid)[4][str(vid["V1"])]["status"] == "VERIFIED"
    assert refs() == before


def test_alternates_excluded_by_default_and_listed_when_included(tmp_path):
    from tests.test_scenario_m7b import build
    from app.db.models import NormalizedQuote
    from app.analysis.scenario import ScenarioParams, run_scenario
    from app.award.memo import render_memo
    _, sf, rid, vid = build(tmp_path, with_questions=False)
    with sf.begin() as s:  # V5's line-2 quote is an alternate construction
        q = next(q for q in s.query(NormalizedQuote).all() if q.vendor_id == vid["V5"] and q.unit_price_inr_ex_gst == "9.5000")
        q.flags = ["ALTERNATE"]
        q.trace = [{"step": "spec_diff", "verdict": "ALTERNATE", "differences": [{"field": "gsm_layer_1", "rfx": 150, "vendor": 120}]}]
        q.unit_price_inr_ex_gst = "5.0000"
    r = run_scenario(sf, rid, ScenarioParams(basis="unit"))
    assert next(a for a in r["awards"] if a["line_no"] == 2)["vendor"] == "V1"
    assert any(e["line_no"] == 2 and e["reason"] == "alternate spec (DL-6)" for e in r["exclusions"])
    r2 = run_scenario(sf, rid, ScenarioParams(basis="unit", include_alternates=True))
    a2 = next(a for a in r2["awards"] if a["line_no"] == 2)
    assert a2["vendor"] == "V5" and a2["spec_differences"] == [{"field": "gsm_layer_1", "rfx": 150, "vendor": 120}]
    assert "Alternates included" in render_memo("T", 1, r2) and "gsm_layer_1 150 → 120" in render_memo("T", 1, r2)
