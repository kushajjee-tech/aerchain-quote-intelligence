"""M4a: matching, group expansion, reference scope, Phase A on the generated V1/V5 inputs, minimal
Phase B (order independence, unit-suspect, outlier, plausibility), persistence.

Extraction is simulated as a *correct* model output built from the real files' units, so these tests
exercise the deterministic pipeline without network access. Expected prices are recomputed here
from the canonical RFx and the file cells, not read from any answer key."""
import json
from decimal import Decimal as D
from pathlib import Path

import pytest

from app.db.models import NormalizedQuote, Rfx, RfxLine, Vendor
from app.domain.enums import ValueStatus as S
from app.ingest.extract import TextExtractionResult
from app.ingest.parsers import parse_message
from app.ingest.schemas import (Answer, DocTerm, DocumentExtraction, Evidence, GroupScope, LineQuote, Price, RefItem, Slab)
from app.ingest.verify import check_evidence, verify_line
from app.normalize.engine import NormalizedCell, QuoteInput, ResponseContext, normalize_cell
from app.process.persist import persist
from app.process.phase_a import phase_a
from app.process.phase_b import phase_b, snapshot_hash

DATA = Path(__file__).resolve().parents[2] / "app_data"
pytestmark = pytest.mark.skipif(not (DATA / "seed/canonical_rfx.json").exists(), reason="M1a dataset not generated")


def ev(uid, quote):
    return Evidence(unit_ids=[uid], quote=quote)


def result(extraction, units):
    return TextExtractionResult(extraction, [verify_line(l, units) for l in extraction.line_quotes],
                                [check_evidence(t.evidence, units).reasons for t in extraction.document_terms],
                                [check_evidence(a.evidence, units).reasons for a in extraction.questionnaire_answers])


@pytest.fixture(scope="module")
def rfx():
    return json.loads((DATA / "seed/canonical_rfx.json").read_text())


@pytest.fixture(scope="module")
def v5_results():
    _, docs = parse_message((DATA / "inbox/01_V5_quote.eml").read_bytes())
    units = {u.id: u for d in docs for u in d.units}
    u = "D1:l1"
    ext = DocumentExtraction(
        line_quotes=[
            LineQuote(vendor_line_ref="5-ply", description_as_stated="5-ply", unit_class="PER_KG", unit_source="STATED",
                      unit_as_stated="/kg", price=Price(value_as_stated="42", value=42, currency_as_stated="₹", currency_source="STATED", evidence=ev(u, "₹42/kg")),
                      applies_to_group=GroupScope(attribute="ply", value=5, evidence=ev(u, "5-ply"))),
            LineQuote(vendor_line_ref="3-ply", description_as_stated="3-ply", unit_class="PER_KG", unit_source="INHERITED_FROM_CONTEXT",
                      unit_inherited_from=ev(u, "₹42/kg"), price=Price(value_as_stated="38", value=38, currency_source="INHERITED_FROM_CONTEXT", evidence=ev(u, "38 for the 3-ply")),
                      applies_to_group=GroupScope(attribute="ply", value=3, evidence=ev(u, "3-ply"))),
        ],
        document_terms=[DocTerm(type="FREIGHT", scope="all", text="freight extra", evidence=ev(u, "freight extra"))],
        references=[RefItem(type="PRIOR_UNSPECIFIED", scope_text="rest", evidence=ev(u, "rest same as last year"))],
        gst_statement="SILENT")
    r1 = result(ext, units)
    _, docs2 = parse_message((DATA / "inbox/02_V5_questionnaire.eml").read_bytes())
    r2 = result(DocumentExtraction(gst_statement="SILENT"), {x.id: x for d in docs2 for x in d.units})
    return [r1, r2]


SLAB_BOUNDS = [(None, 10000), (10001, 50000), (50001, None)]


@pytest.fixture(scope="module")
def v1_results():
    _, docs = parse_message((DATA / "inbox/03_V1_quotation.eml").read_bytes())
    xlsx = docs[1]
    units = {u.id: u for d in docs for u in d.units}
    grid = {(u.locator["sheet"], u.locator["cell"]): u for u in xlsx.units}
    quotes = []
    for (sheet, cell), u in sorted(grid.items(), key=lambda kv: (kv[1].locator["row"], kv[1].locator["col"])):
        if sheet != "Quotation" or u.locator["col"] != 3 or not u.text.startswith("PK-"):
            continue
        row = u.locator["row"]
        slabs = []
        for (lo, hi), col in zip(SLAB_BOUNDS, "HIJ"):
            c = grid[("Quotation", f"{col}{row}")]
            slabs.append(Slab(min_qty=lo, max_qty=hi, price=Price(value_as_stated=c.text, value=float(c.text), currency_source="STATED", evidence=ev(c.id, c.text))))
        is_set = grid.get(("Quotation", f"K{row}")) and grid[("Quotation", f"K{row}")].text == "Set price"
        quotes.append(LineQuote(vendor_line_ref=str(row), description_as_stated=grid[("Quotation", f"D{row}")].text, item_code=u.text,
                                slabs=slabs, unit_class="PER_SET" if is_set else "PER_BOX", unit_source="STATED",
                                unit_as_stated="per set" if is_set else "per pc"))
    notes = {u.text: u for u in xlsx.units if u.text.startswith(("1.", "2.", "Printing"))}
    fr = next(t for t in notes if "freight" in t)
    gst = next(t for t in notes if "GST" in t)
    ext = DocumentExtraction(line_quotes=quotes, gst_statement="STATED", document_terms=[
        DocTerm(type="FREIGHT", scope="all", text=fr, evidence=ev(notes[fr].id, "freight included")),
        DocTerm(type="GST", scope="all", text=gst, evidence=ev(notes[gst].id, "exclusive of GST"))])
    return [result(ext, units)], grid


def cells_by_line(results, rfx):
    return {c.line_no: c.cell for c in phase_a(rfx, results)}


def test_v5_phase_a(rfx, v5_results):
    cells = cells_by_line(v5_results, rfx)
    lines = {l["line_no"]: l for l in rfx["lines"]}
    for n, line in lines.items():
        c = cells[n]
        assert c.freight_basis == "UNKNOWN" and c.landed_inr_ex_gst is None
        if line["ply"] == 7:
            assert c.unit_status == S.UNRESOLVED and "REFERENCE_AMBIGUOUS" in c.reasons
        elif line["item_type"] == "PARTITION":
            assert c.unit_status == S.NOT_CONVERTIBLE and "ITEM_TYPE_NOT_WEIGHT_COMPUTABLE" in c.reasons
        elif line["reference_unit_weight_g"]:
            rate = D(42) if line["ply"] == 5 else D(38)
            assert c.unit_status == S.ASSUMED and c.unit_price_inr_ex_gst == (rate * D(line["reference_unit_weight_g"]) / 1000).quantize(D("0.0001"))
            assert {"REFERENCE_WEIGHT", "GST_PER_RFX_BASIS"} <= set(c.reasons) and "DERIVED_FROM_GROUP_PRICE" in c.flags
            assert ("UNIT_INHERITED" in c.reasons) == (line["ply"] == 3)
        elif line["item_type"] == "RSC":
            assert c.unit_status == S.NEEDS_REVIEW and "WEIGHT_ESTIMATED" in c.reasons
        else:  # die-cut without blank size and without reference weight
            assert c.unit_status == S.NOT_CONVERTIBLE and "MISSING_CONSTRUCTION_INPUT" in c.reasons


def test_v1_phase_a(rfx, v1_results):
    results, grid = v1_results
    cells = cells_by_line(results, rfx)
    quoted = {u.text: u.locator["row"] for (sh, _), u in grid.items() if sh == "Quotation" and u.locator["col"] == 3 and u.text.startswith("PK-")}
    for line in rfx["lines"]:
        c = cells[line["line_no"]]
        if line["sku_code"] not in quoted:
            assert c.unit_status == S.MISSING
            continue
        qty = line["annual_qty"]
        col = "H" if qty <= 10000 else ("I" if qty <= 50000 else "J")
        expected = D(grid[("Quotation", f"{col}{quoted[line['sku_code']]}")].text).quantize(D("0.0001"))
        assert c.unit_price_inr_ex_gst == expected and c.unit_status == S.EXTRACTED and c.reasons == []
        assert c.freight_basis == "INCLUDED" and c.landed_inr_ex_gst == expected
    assert sorted(l["line_no"] for l in rfx["lines"] if cells[l["line_no"]].unit_status == S.MISSING) == [19, 20]


def test_phase_b_order_independent_and_plausibility(rfx, v1_results, v5_results):
    a = {"V1": cells_by_line(v1_results[0], rfx), "V5": cells_by_line(v5_results, rfx)}
    b = {"V5": a["V5"], "V1": a["V1"]}
    base = {b_["line_no"]: D(b_["unit_price_inr_ex_gst"]) for b_ in json.loads((DATA / "seed/baseline_prices.json").read_text())}
    ra, rb = phase_b(a, base), phase_b(b, base)
    assert snapshot_hash(ra) == snapshot_hash(rb)
    v1 = ra["V1"]
    for n, c in v1.items():
        if c.unit_price_inr_ex_gst is None:
            continue
        if n in base:
            assert c.unit_status in (S.VERIFIED, S.NEEDS_REVIEW)  # checked against a reference
        else:
            assert "PLAUSIBILITY_UNCHECKED" in c.flags and c.unit_status == S.EXTRACTED


def _cell(price: str) -> NormalizedCell:
    line = {"line_no": 1, "item_type": "RSC", "annual_qty": 1000, "reference_unit_weight_g": None}
    return normalize_cell(line, QuoteInput(value=D(price), unit_class="PER_BOX"),
                          ResponseContext("STATED", True, "prices exclusive of GST"))


def test_unit_suspect_and_outlier_never_auto_fixed():
    out = phase_b({"A": {1: _cell("5.00")}, "B": {1: _cell("5.20")}, "C": {1: _cell("5.10")}, "D": {1: _cell("480")}})
    d = out["D"][1]
    assert d.unit_status == S.UNRESOLVED and "UNIT_SUSPECT" in d.reasons and d.unit_price_inr_ex_gst is None
    sug = next(t for t in d.trace if t["step"] == "plausibility")["suggestion"]
    assert sug == {"divide_by": "100", "suggested_unit_price": "4.8000"}
    assert all(out[k][1].unit_status == S.VERIFIED for k in "ABC")
    out2 = phase_b({"A": {1: _cell("5.00")}, "B": {1: _cell("5.20")}, "C": {1: _cell("5.10")}, "D": {1: _cell("11.00")}})
    assert out2["D"][1].unit_status == S.NEEDS_REVIEW and "OUTLIER" in out2["D"][1].reasons
    assert out2["D"][1].unit_price_inr_ex_gst == D("11.0000")


def test_persist_round_trip(rfx, v1_results, v5_results, session_factory):
    with session_factory.begin() as s:
        r = Rfx(title="t", kind="primary", origin="SEEDED_FALLBACK", response_basis=rfx["response_basis"])
        s.add(r); s.flush()
        line_ids = {}
        for l in rfx["lines"]:
            row = RfxLine(rfx_id=r.id, line_no=l["line_no"], sku_code=l["sku_code"], description=l["description"], item_type=l["item_type"],
                          dims_mm=l["dims_mm"], ply=l["ply"], flute_profile=l["flute_profile"], layers=l["layers"], annual_qty=l["annual_qty"])
            s.add(row); s.flush(); line_ids[l["line_no"]] = row.id
        vids = {}
        for k in ("V1", "V5"):
            v = Vendor(name=k, contact_email=f"{k}@x"); s.add(v); s.flush(); vids[k] = v.id
        rid = r.id
    cells = phase_b({"V1": cells_by_line(v1_results[0], rfx), "V5": cells_by_line(v5_results, rfx)})
    snap = persist(session_factory, rid, vids, line_ids, cells)
    with session_factory() as s:
        rows = s.query(NormalizedQuote).all()
        assert len(rows) == 60 and len(snap) == 64
        assert all((q.unit_price_inr_ex_gst is None) == (q.unit_status in ("MISSING", "NOT_CONVERTIBLE", "UNRESOLVED")) for q in rows)
