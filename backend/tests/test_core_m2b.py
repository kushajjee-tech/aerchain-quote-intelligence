"""M2b: eligibility truth table (DL-3/14/24/29), spec signature, reading A/B candidates (DL-8/20),
discounts, FX (DL-15), confirmed references. Hand-calculated expectations."""
import json
import random
from datetime import date
from decimal import Decimal as D
from pathlib import Path

import pytest

from app.domain.enums import ValueStatus as S
from app.eligibility.rules import (FAIL, NA, PASS, UNVERIFIED, AnswerIn, DocFact, evaluate_question, label, line_gate, roll_up)
from app.normalize.baseline import price_candidates, spec_signature, term_candidates
from app.normalize.engine import QuoteInput, ResponseContext, normalize_cell

DATA = Path(__file__).resolve().parents[2] / "app_data"
TODAY = date(2026, 11, 5)
V = "Sahyadri Paper Mills"
ISO = {"requirement_key": "QC-01", "section": "QUALITY", "applicability": "ALL", "pass_rule": {"op": "==", "value": "yes"},
       "evidence_required": True, "evidence_doc_type": "ISO_9001_CERTIFICATE"}
CAP = {"requirement_key": "QC-04", "section": "QUALITY", "applicability": "ALL", "pass_rule": {"op": ">=", "value": 250}}
FOOD = {"requirement_key": "QC-03", "section": "QUALITY", "applicability": "LINES_WITH_FLAG(food_contact)",
        "pass_rule": {"op": "==", "value": "yes"}, "evidence_required": True, "evidence_doc_type": "FOOD_CONTACT_DECLARATION"}
PAY = {"requirement_key": "CP-01", "section": "COMMERCIAL", "applicability": "ALL", "pass_rule": {"op": "==", "value": "yes"}}
iso_doc = lambda **kw: DocFact("ISO_9001_CERTIFICATE", kw.get("entity", V), kw.get("expiry", "2027-08-18"), kw.get("readable", True))


@pytest.mark.parametrize("answer,expected,why", [
    (AnswerIn("Yes", [iso_doc()]), PASS, "valid"),
    (AnswerIn("Yes", [iso_doc(expiry="2026-03-31")]), UNVERIFIED, "expired"),
    (AnswerIn("Yes", [iso_doc(entity="Sahyadri Packaging LLP")]), UNVERIFIED, "another entity"),
    (AnswerIn("Yes", []), UNVERIFIED, "not attached"),
    (AnswerIn("Yes", [iso_doc(readable=False)]), UNVERIFIED, "could not be read"),
    (AnswerIn("No", [iso_doc()]), FAIL, "does not meet"),
    (None, UNVERIFIED, "unanswered"),
])
def test_evidence_question_truth_table(answer, expected, why):
    r = evaluate_question(ISO, answer, V, set(), TODAY)
    assert r.state == expected and why in r.reason


def test_numeric_rule_and_entity_normalisation():
    assert evaluate_question(CAP, AnswerIn("320"), V, set(), TODAY).state == PASS
    assert evaluate_question(CAP, AnswerIn("150 t"), V, set(), TODAY).state == FAIL
    assert evaluate_question(CAP, AnswerIn("about a lot"), V, set(), TODAY).state == UNVERIFIED
    assert evaluate_question(ISO, AnswerIn("Yes", [iso_doc(entity="SAHYADRI PAPER MILLS.")]), V, set(), TODAY).state == PASS


def test_sections_and_line_level_food_grade():
    v5 = [evaluate_question(ISO, AnswerIn("Yes", [iso_doc()]), V, {"food_contact"}, TODAY),
          evaluate_question(CAP, AnswerIn("320"), V, {"food_contact"}, TODAY),
          evaluate_question(FOOD, AnswerIn("Yes", []), V, {"food_contact"}, TODAY),          # no declaration attached
          evaluate_question(PAY, AnswerIn("No"), V, {"food_contact"}, TODAY)]
    assert roll_up(v5, "QUALITY")[0] == PASS          # line-scoped food-grade never enters the vendor roll-up (DL-29)
    assert roll_up(v5, "COMMERCIAL")[0] == FAIL and roll_up(v5, None)[0] == FAIL
    assert line_gate(v5, "food_contact", "strict") is False and line_gate(v5, "food_contact", "inclusive") is True
    no_food = evaluate_question(FOOD, AnswerIn("Yes"), V, set(), TODAY)
    assert no_food.state == NA and line_gate([no_food], "food_contact") is True
    assert label(UNVERIFIED) == "Unverified" and label(FAIL) == "Failed" and "fail" not in label(UNVERIFIED).lower()


@pytest.mark.skipif(not (DATA / "seed/canonical_rfx.json").exists(), reason="M1a dataset not generated")
def test_signature_matches_canonical_and_candidates():
    rfx = json.loads((DATA / "seed/canonical_rfx.json").read_text())
    assert all(spec_signature(l) == l["spec_signature"] for l in rfx["lines"])
    rows = json.loads((DATA / "seed/baseline_prices.json").read_text())
    c = price_candidates(rfx["lines"], [15, 16, 17, 18], V, rows)
    assert [c[n].reason for n in (15, 16, 17, 18)] == ["REFERENCE_AMBIGUOUS", "REFERENCE_AMBIGUOUS", "BASELINE_SPEC_CHANGED", "BASELINE_NOT_FOR_VENDOR"]
    assert c[15].candidate is not None and c[17].candidate is None and c[18].candidate is None
    assert c[15].baseline_freight_basis == "INCLUDED"
    terms = json.loads((DATA / "seed/baseline_terms.json").read_text())
    got = term_candidates(V, {"PAYMENT", "LEAD_TIME"}, terms)
    assert sorted(t["term_type"] for t in got) == ["MOQ", "VALIDITY"] and all(not t["applied"] for t in got)


def test_never_another_vendors_price_property():
    rng = random.Random(7)
    line = {"line_no": 1, "sku_code": "S1", "item_type": "RSC", "dims_mm": {"L": 1, "W": 2, "H": 3}, "ply": 7,
            "flute_profile": "BCB", "layers": [], "printing": {}}
    for _ in range(200):
        rows = [{"vendor": rng.choice(["A", "B", "C"]), "sku": "S1", "spec_signature": spec_signature(line),
                 "unit_price_inr_ex_gst": str(rng.randint(1, 999))} for _ in range(rng.randint(0, 4))]
        c = price_candidates([line], [1], "V5", rows)[1]
        assert c.candidate is None and c.reason == "BASELINE_NOT_FOR_VENDOR"


LINE = {"line_no": 1, "item_type": "RSC", "ply": 5, "annual_qty": 1000, "reference_unit_weight_g": None}
CTX = ResponseContext("STATED", True, "prices exclusive of GST")


def test_reference_confirmation_rules():
    pending = normalize_cell(LINE, QuoteInput(reference=True, reference_reason="REFERENCE_AMBIGUOUS", reference_candidate=D("147.25")), CTX)
    assert pending.unit_status == S.UNRESOLVED and pending.unit_price_inr_ex_gst is None
    assert next(t for t in pending.trace if t["step"] == "reference")["candidate"] == "147.25"
    ok = normalize_cell(LINE, QuoteInput(reference=True, reference_reason="REFERENCE_AMBIGUOUS", reference_candidate=D("147.25"),
                                         reference_confirmed=True, baseline_freight_basis="INCLUDED"), CTX)
    assert ok.unit_status == S.ASSUMED and ok.unit_price_inr_ex_gst == D("147.2500") and "BASELINE_REFERENCE" in ok.reasons
    assert "FREIGHT_BASIS_CHANGED" in ok.flags and ok.freight_basis == "UNKNOWN" and ok.landed_inr_ex_gst is None
    changed = normalize_cell(LINE, QuoteInput(reference=True, reference_reason="BASELINE_SPEC_CHANGED", reference_confirmed=True), CTX)
    assert changed.unit_status == S.UNRESOLVED and "BASELINE_SPEC_CHANGED" in changed.reasons


def test_discounts_once_and_in_scope():
    q = QuoteInput(value=D("10.00"), unit_class="PER_BOX")
    all5 = normalize_cell(LINE, q, ResponseContext("STATED", True, "x", discounts=[{"pct": D("5"), "scope": "all"}]))
    assert all5.unit_price_inr_ex_gst == D("9.5000") and len([t for t in all5.trace if t["step"] == "discount"]) == 1
    ply3 = normalize_cell(LINE, q, ResponseContext("STATED", True, "x", discounts=[{"pct": D("5"), "scope": {"ply": 3}}]))
    assert ply3.unit_price_inr_ex_gst == D("10.0000")


def test_fx_conversion_preserves_original():
    fx = {"USD": {"rate": D("88.50"), "as_of": "2026-10-28", "source": "RBI reference rate"}}
    c = normalize_cell(LINE, QuoteInput(value=D("0.05"), unit_class="PER_BOX", currency="USD"), ResponseContext("STATED", True, "x", fx_rates=fx))
    assert c.unit_price_inr_ex_gst == D("4.4250") and c.unit_status == S.ASSUMED and "FX" in c.flags
    t = next(t for t in c.trace if t["step"] == "fx")
    assert t["original"] == "0.0500" and t["rate"] == "88.50" and t["as_of"] == "2026-10-28"
    missing = normalize_cell(LINE, QuoteInput(value=D("0.05"), unit_class="PER_BOX", currency="USD"), CTX)
    assert missing.unit_status == S.UNRESOLVED and missing.unit_price_inr_ex_gst is None
