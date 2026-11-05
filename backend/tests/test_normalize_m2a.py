"""M2a golden + property tests. Expected values are hand-calculated here (PRD §5.2–§5.10), not
taken from any answer key."""
import ast
import copy
from decimal import Decimal as D
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.enums import ValueStatus as S
from app.normalize.constants import CONSTANT_SET_V1
from app.normalize.engine import QuoteInput, ResponseContext, normalize_cell
from app.normalize.money import line_total
from app.validate.status import OverrideRequired, Policy, includable, worst

BASIS = "prices exclusive of GST"


def rsc(**kw):
    line = {"line_no": 1, "item_type": "RSC", "dims_mm": {"L": 250, "W": 200, "H": 150}, "blank_size_mm": None,
            "ply": 3, "flute_profile": "B", "annual_qty": 25000, "reference_unit_weight_g": None,
            "reference_weight_source": None,
            "layers": [{"role": "liner", "gsm": 150}, {"role": "medium", "gsm": 120}, {"role": "liner", "gsm": 150}]}
    line.update(kw)
    return line


def five_ply(**kw):
    return rsc(dims_mm={"L": 400, "W": 300, "H": 300}, ply=5, flute_profile="BC",
               layers=[{"role": "liner", "gsm": 180}, {"role": "medium", "gsm": 120}, {"role": "liner", "gsm": 150},
                       {"role": "medium", "gsm": 150}, {"role": "liner", "gsm": 180}], **kw)


SILENT = ResponseContext(gst_statement="SILENT", rfx_gst_basis=BASIS)
STATED = ResponseContext(gst_statement="STATED", gst_stated_exclusive=True, rfx_gst_basis=BASIS)
per_kg = lambda v: QuoteInput(value=D(v), unit_class="PER_KG")


# --- weight hierarchy (DL-18 / DL-31) -----------------------------------------------------
def test_reference_weight_is_assumed_with_billed_weight_risk():
    c = normalize_cell(rsc(reference_unit_weight_g=158, reference_weight_source="IM row 2"), per_kg("38"), STATED)
    assert c.unit_price_inr_ex_gst == D("6.0040") and c.unit_status == S.ASSUMED
    assert c.weight_source == "SKU_REFERENCE" and "REFERENCE_WEIGHT" in c.reasons and "BILLED_WEIGHT_RISK" in c.flags


def test_rsc_estimate_hand_calculated():
    # blank (2·250+2·200+35)·(200+150)=327,250 mm² = 0.32725 m²; grammage 150+150+120·1.35 = 462 g/m²
    c = normalize_cell(rsc(), per_kg("38"), STATED)
    assert c.weight_g == D("151.1895") and c.unit_price_inr_ex_gst == D("5.7452")
    assert c.unit_status == S.NEEDS_REVIEW and {"WEIGHT_ESTIMATED", "METHOD_CONSTANTS"} <= set(c.reasons)
    est = next(t for t in c.trace if t["step"] == "weight_estimate")
    assert all(k["label"] == "approximate engineering constant — not validated" and k["version"] == "v1" for k in est["constants"])
    assert "may understate" in est["label"]


def test_flute_maps_to_mediums_in_layer_order():
    # 0.861 m² × (180+150+180 + 120·1.35(B) + 150·1.45(C)) = 0.861 × 889.5 = 765.8595 g (reversed mapping would give 763.2765)
    c = normalize_cell(five_ply(), per_kg("42"), STATED)
    assert c.weight_g == D("765.8595") and c.unit_price_inr_ex_gst == D("32.1661")


def test_flat_blank_die_cut_and_missing_blank():
    dc = rsc(item_type="DIE_CUT", blank_size_mm={"L": 700, "W": 600})
    assert normalize_cell(dc, per_kg("38"), STATED).weight_g == D("194.0400")  # 0.42 m² × 462
    no_blank = normalize_cell(rsc(item_type="DIE_CUT"), per_kg("38"), STATED)
    assert no_blank.unit_status == S.NOT_CONVERTIBLE and "MISSING_CONSTRUCTION_INPUT" in no_blank.reasons
    assert no_blank.unit_price_inr_ex_gst is None


def test_partition_never_estimated_but_converts_with_reference():
    p = normalize_cell(rsc(item_type="PARTITION"), per_kg("38"), STATED)
    assert p.unit_status == S.NOT_CONVERTIBLE and p.reasons == ["ITEM_TYPE_NOT_WEIGHT_COMPUTABLE"]
    pr = normalize_cell(rsc(item_type="PARTITION", reference_unit_weight_g=90), per_kg("38"), STATED)
    assert pr.unit_price_inr_ex_gst == D("3.4200") and pr.unit_status == S.ASSUMED


@pytest.mark.parametrize("mutate", [
    lambda l: l["dims_mm"].pop("H"), lambda l: l["layers"][1].update(gsm=None), lambda l: l.update(flute_profile=""),
    lambda l: l["layers"].pop(), lambda l: l.update(ply=4),
])
def test_removing_any_input_never_yields_a_number(mutate):
    line = copy.deepcopy(rsc())
    mutate(line)
    c = normalize_cell(line, per_kg("38"), STATED)
    assert c.unit_price_inr_ex_gst is None and c.unit_status == S.NOT_CONVERTIBLE


def test_vendor_weight_paths():
    only_vendor = normalize_cell(rsc(), QuoteInput(value=D("40"), unit_class="PER_KG", vendor_weight_g=D("150")), STATED)
    assert only_vendor.weight_source == "VENDOR_STATED" and only_vendor.unit_status == S.EXTRACTED
    assert only_vendor.unit_price_inr_ex_gst == D("6.0000") and "CONVERTED" in only_vendor.flags
    mism = normalize_cell(rsc(reference_unit_weight_g=158), QuoteInput(value=D("40"), unit_class="PER_KG", vendor_weight_g=D("190")), STATED)
    assert mism.weight_source == "SKU_REFERENCE" and mism.unit_status == S.NEEDS_REVIEW and "WEIGHT_MISMATCH" in mism.reasons


# --- quantity units, slabs ---------------------------------------------------------------
@pytest.mark.parametrize("value,unit", [("480", "PER_100"), ("4800", "PER_1000"), ("57.6", "PER_DOZEN"), ("4.80", "PER_BOX")])
def test_qty_units(value, unit):
    c = normalize_cell(rsc(), QuoteInput(value=D(value), unit_class=unit), STATED)
    assert c.unit_price_inr_ex_gst == D("4.8000") and c.unit_status == S.EXTRACTED
    assert ("CONVERTED" in c.flags) == (unit != "PER_BOX")


def test_unknown_unit_has_no_number():
    c = normalize_cell(rsc(), QuoteInput(value=D("480"), unit_class="UNKNOWN"), STATED)
    assert c.unit_status == S.UNRESOLVED and c.unit_price_inr_ex_gst is None and "UNIT_UNKNOWN" in c.reasons


SLABS = [{"min_qty": None, "max_qty": 10000, "value": "11.66"}, {"min_qty": 10001, "max_qty": 50000, "value": "11.00"},
         {"min_qty": 50001, "max_qty": None, "value": "10.56"}]


def test_slab_selection():
    c = normalize_cell(rsc(annual_qty=25000), QuoteInput(unit_class="PER_BOX", slabs=SLABS), STATED)
    assert c.unit_price_inr_ex_gst == D("11.0000") and any(t["step"] == "slab" and t["chosen"] == 1 for t in c.trace)
    overlap = SLABS + [{"min_qty": 20000, "max_qty": 30000, "value": "10.90"}]
    bad = normalize_cell(rsc(annual_qty=25000), QuoteInput(unit_class="PER_BOX", slabs=overlap), STATED)
    assert bad.unit_status == S.UNRESOLVED and "SLAB_AMBIGUOUS" in bad.reasons


# --- GST (DL-26), freight (DL-2/DL-8), references, missing --------------------------------
def test_gst_rules():
    q = QuoteInput(value=D("4.80"), unit_class="PER_BOX")
    assert normalize_cell(rsc(), q, SILENT).unit_status == S.ASSUMED
    assert "GST_PER_RFX_BASIS" in normalize_cell(rsc(), q, SILENT).reasons
    assert normalize_cell(rsc(), q, ResponseContext(gst_statement="SILENT", rfx_gst_basis=None)).unit_status == S.UNRESOLVED
    assert normalize_cell(rsc(), q, ResponseContext(gst_statement="AMBIGUOUS", rfx_gst_basis=BASIS)).reasons == ["GST_UNCLEAR"]
    assert normalize_cell(rsc(), q, STATED).reasons == []


def test_freight_bases():
    q = QuoteInput(value=D("4.80"), unit_class="PER_BOX")
    inc = normalize_cell(rsc(), q, ResponseContext("STATED", True, BASIS, [{"type": "FREIGHT", "text": "Rates are for delivery at your plant — freight included"}]))
    assert inc.freight_basis == "INCLUDED" and inc.landed_inr_ex_gst == D("4.8000")
    st = normalize_cell(rsc(), q, ResponseContext("STATED", True, BASIS, [{"type": "FREIGHT", "text": "Freight", "value": "0.40", "unit": "per box"}]))
    assert st.freight_basis == "STATED" and st.landed_inr_ex_gst == D("5.2000")
    ex = normalize_cell(rsc(), q, ResponseContext("STATED", True, BASIS, [{"type": "FREIGHT", "text": "freight extra"}]))
    assert ex.freight_basis == "UNKNOWN" and ex.landed_inr_ex_gst is None and ex.landed_status == S.NOT_CONVERTIBLE
    silent = normalize_cell(rsc(), q, STATED)
    assert silent.freight_basis == "UNKNOWN" and silent.landed_inr_ex_gst is None


def test_reference_and_missing():
    ref = normalize_cell(rsc(), QuoteInput(reference=True), SILENT)
    assert ref.unit_status == S.UNRESOLVED and "REFERENCE_AMBIGUOUS" in ref.reasons and ref.unit_price_inr_ex_gst is None
    miss = normalize_cell(rsc(), QuoteInput(quoted=False), SILENT)
    assert miss.unit_status == S.MISSING and miss.unit_price_inr_ex_gst is None


def test_blocking_verification_reason_discards_number():
    c = normalize_cell(rsc(), QuoteInput(value=D("4.80"), unit_class="PER_BOX", verification_reasons=["EVIDENCE_NOT_FOUND"]), STATED)
    assert c.unit_status == S.UNRESOLVED and c.unit_price_inr_ex_gst is None
    assert any(t["step"] == "candidate" for t in c.trace)


def test_phase_a_never_verifies_and_image_never_auto_verifies():
    q = QuoteInput(value=D("4.80"), unit_class="PER_BOX")
    clean = normalize_cell(rsc(), q, STATED)
    assert clean.unit_status == S.EXTRACTED and clean.auto_verify_candidate is True
    img = normalize_cell(rsc(), QuoteInput(value=D("4.80"), unit_class="PER_BOX", image_sourced=True), STATED)
    assert img.auto_verify_candidate is False


# --- canonical inclusion (DL-10, DL-16) -------------------------------------------------
@pytest.mark.parametrize("st", [S.UNRESOLVED, S.NOT_CONVERTIBLE, S.MISSING])
@pytest.mark.parametrize("pol", [Policy(), Policy("exploratory", True), Policy("formal", False)])
def test_excluded_statuses_never_includable(st, pol):
    assert includable(st, pol, override_id=1) is False


def test_needs_review_policy():
    assert includable(S.NEEDS_REVIEW) is False
    with pytest.raises(OverrideRequired):
        includable(S.NEEDS_REVIEW, Policy("formal", True))
    assert includable(S.NEEDS_REVIEW, Policy("formal", True), override_id=7) is True
    assert includable(S.NEEDS_REVIEW, Policy("exploratory", True)) is True
    assert all(includable(s) for s in (S.VERIFIED, S.EXTRACTED, S.ASSUMED))
    assert worst([S.ASSUMED, S.NEEDS_REVIEW, S.EXTRACTED]) == S.NEEDS_REVIEW


# --- money + constants ---------------------------------------------------------------------
def test_money_rounding_and_no_floats():
    assert line_total(D("5.7452"), 30000) == D("172356") and line_total(D("0.0005"), 1) == D("0")
    assert line_total(D("1.00005"), 10000) == D("10001")  # 10000.5 → half-up
    app = Path(__file__).resolve().parents[1] / "app"
    for f in list((app / "normalize").glob("*.py")) + [app / "validate" / "status.py"]:
        for node in ast.walk(ast.parse(f.read_text())):
            assert not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "float"), f.name
            assert not (isinstance(node, ast.Constant) and isinstance(node.value, float)), f.name


def test_constant_set_is_versioned_and_unvalidated():
    cs = CONSTANT_SET_V1
    assert cs.version == "v1" and len(cs.content_hash) == 16
    assert all(c["validation_status"] == "UNVALIDATED" for c in cs.constants)
    assert cs.label("takeup.B").endswith("not validated") and cs.label("check.unit_suspect_ratio").startswith("product heuristic")


# --- freight phrasing and currency (found while generating V2/V3, M1b) ---------------------------
from app.normalize.freight import freight_basis as _fb, freight_currency as _fc  # noqa: E402


@pytest.mark.parametrize("term,basis,amount,cur", [
    ({"type": "FREIGHT", "value": "0.0060", "unit": "USD per box",
      "text": "Freight USD 0.0060 per box, delivered to your Chakan plant (charged separately)"}, "STATED", "0.0060", "USD"),
    ({"type": "FREIGHT", "value": "0.45", "unit": "per box",
      "text": "Freight to your Chakan plant will be charged at ₹0.45 per box over and above the rates quoted."}, "STATED", "0.45", "INR"),
    ({"type": "FREIGHT", "text": "Rates are for delivery at your Chakan plant — freight included."}, "INCLUDED", "0", "INR"),
    ({"type": "FREIGHT", "text": "freight extra"}, "UNKNOWN", None, "INR"),
    ({"type": "FREIGHT", "text": "Rates ex-works, GST extra as applicable."}, "UNKNOWN", None, "INR"),
])
def test_freight_phrasing(term, basis, amount, cur):
    b, a, _ = _fb([term])
    assert b == basis and (a == (Decimal(amount) if amount is not None else None)) and _fc(term) == cur


def test_usd_freight_converted_or_landed_withheld():
    term = {"type": "FREIGHT", "value": "0.0060", "unit": "USD per box", "text": "Freight USD 0.0060 per box (charged separately)"}
    q = QuoteInput(value=Decimal("0.0864"), unit_class="PER_BOX", currency="USD")
    no_rate = normalize_cell(rsc(), q, ResponseContext(gst_statement="STATED", gst_stated_exclusive=True, freight_terms=[term]))
    assert no_rate.landed_inr_ex_gst is None and no_rate.freight_inr_per_box is None   # never USD added as ₹
    fx = {"USD": {"rate": Decimal("84.20"), "as_of": "2026-10-30", "source": "stated"}}
    ok = normalize_cell(rsc(), q, ResponseContext(gst_statement="STATED", gst_stated_exclusive=True, freight_terms=[term], fx_rates=fx))
    assert ok.freight_inr_per_box == Decimal("0.5052")
    assert ok.landed_inr_ex_gst == ok.unit_price_inr_ex_gst + Decimal("0.5052")
