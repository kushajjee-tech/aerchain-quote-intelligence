"""M3a: deterministic evidence + unit-inheritance verification (DL-12, architecture §7.3)."""
from app.ingest.evidence import EvidenceUnit
from app.ingest.schemas import Evidence, GroupScope, LineQuote, Price
from app.ingest.verify import verify_line

SENTENCE = "₹42/kg for the 5-ply, 38 for the 3-ply, rest same as last year, freight extra."


def U(id_, text, **loc):
    return EvidenceUnit(id_, id_.split(":")[0], "email_line", loc or {"line_no": 1}, text)


def lq(value, quote, unit_id="D1:l1", unit="PER_KG", source="STATED", unit_as_stated="/kg", inherited=None, num=None):
    return LineQuote(
        vendor_line_ref="g", description_as_stated="group", unit_class=unit, unit_source=source,
        unit_as_stated=unit_as_stated, unit_inherited_from=inherited,
        price=Price(value_as_stated=value, value=num if num is not None else float(value.replace(",", "")),
                    currency_source="STATED", evidence=Evidence(unit_ids=[unit_id], quote=quote)),
        applies_to_group=GroupScope(attribute="ply", value=5, evidence=Evidence(unit_ids=[unit_id], quote="5-ply")),
    )


UNITS = {"D1:l1": U("D1:l1", SENTENCE)}


def test_stated_price_ok():
    v = verify_line(lq("42", "₹42/kg"), UNITS)
    assert v.reasons == [] and v.unit_class == "PER_KG"


def test_exact_sentence_inherited_unit_dl12():
    q = lq("38", "38 for the 3-ply", source="INHERITED_FROM_CONTEXT", unit_as_stated=None,
           inherited=Evidence(unit_ids=["D1:l1"], quote="₹42/kg"))
    v = verify_line(q, UNITS)
    assert v.unit_class == "PER_KG" and v.reasons == ["UNIT_INHERITED"]


def test_inheritance_from_other_message_rejected():
    units = {"D1:l1": U("D1:l1", "38 for the 3-ply"), "D7:l1": U("D7:l1", "₹42/kg for the 5-ply")}
    q = lq("38", "38 for the 3-ply", source="INHERITED_FROM_CONTEXT", unit_as_stated=None,
           inherited=Evidence(unit_ids=["D7:l1"], quote="₹42/kg"))
    v = verify_line(q, units)
    assert v.unit_class == "UNKNOWN" and "UNIT_UNKNOWN" in v.reasons


def test_intervening_unit_token_rejected():
    units = {"D1:l1": U("D1:l1", "₹42/kg for the 5-ply, ₹4 per pc for pads, 38 for the 3-ply")}
    q = lq("38", "38 for the 3-ply", source="INHERITED_FROM_CONTEXT", unit_as_stated=None,
           inherited=Evidence(unit_ids=["D1:l1"], quote="₹42/kg"))
    assert verify_line(q, units).unit_class == "UNKNOWN"


def test_invented_value_rejected():
    assert verify_line(lq("45", "₹45/kg"), UNITS).reasons == ["EVIDENCE_NOT_FOUND"]
    assert verify_line(lq("42", "₹42/kg", num=41.0), UNITS).reasons == ["EVIDENCE_NOT_FOUND"]
    assert verify_line(lq("42", "₹42/kg", unit_id="D9:l1"), UNITS).reasons == ["EVIDENCE_NOT_FOUND"]


def test_indian_grouping_and_rs_prefix():
    units = {"D2:l4": U("D2:l4", "Plates & dies one-time: Rs. 42,000")}
    v = verify_line(lq("42,000", "₹42,000", unit_id="D2:l4", unit="LUMP_SUM", unit_as_stated="one-time"), units)
    assert "EVIDENCE_NOT_FOUND" not in v.reasons


def test_dictionary_unseen_vs_disagree():
    unseen = verify_line(lq("42", "₹42/kg", unit_as_stated="per kilo"), UNITS)
    assert unseen.unit_class == "PER_KG" and "UNIT_DICT_UNSEEN" in unseen.flags
    disagree = verify_line(lq("42", "₹42/kg", unit="PER_BOX", unit_as_stated="/kg"), UNITS)
    assert disagree.unit_class == "UNKNOWN" and "UNIT_UNKNOWN" in disagree.reasons


def test_missing_unit_is_unknown():
    v = verify_line(lq("42", "₹42/kg", unit="UNKNOWN", source="NONE", unit_as_stated=None), UNITS)
    assert v.unit_class == "UNKNOWN" and "UNIT_UNKNOWN" in v.reasons


# --- units from table headers / document-wide statements (live finding: V1/V2/V3 prices withheld) ---------
def _u(uid, text, **loc):
    from app.ingest.evidence import EvidenceUnit
    return EvidenceUnit(uid, uid.split(":")[0], "cell", loc, text)


def _inherit(src, price, value="7.08"):
    from app.ingest.schemas import Evidence, LineQuote, Price
    from app.ingest.verify import check_inheritance
    lq = LineQuote(vendor_line_ref="1", description_as_stated="x", unit_class="PER_BOX", unit_source="INHERITED_FROM_CONTEXT",
                   unit_inherited_from=Evidence(unit_ids=[src.id], quote=src.text),
                   price=Price(value_as_stated=value, currency_source="INHERITED_FROM_CONTEXT",
                               evidence=Evidence(unit_ids=[price.id], quote=value)))
    return check_inheritance(lq, {src.id: src, price.id: price}).reasons


def test_unit_from_column_header_or_declaration():
    hdr = _u("D2:t1r1c6", "Rate (₹ per box)", table=1, row=1, col=6)
    assert _inherit(hdr, _u("D2:t1r9c6", "10.66", table=1, row=9, col=6)) == ["UNIT_INHERITED"]
    assert _inherit(hdr, _u("D2:t1r9c5", "10.66", table=1, row=9, col=5)) == ["UNIT_UNKNOWN"]       # other column
    xh = _u("D2:Q!H5", "Rate (₹ per pc) — quantity slabs (annual)", sheet="Q", row=5, col=8)
    assert _inherit(xh, _u("D2:Q!I20", "10.82", sheet="Q", row=20, col=9)) == ["UNIT_INHERITED"]   # merged header
    assert _inherit(xh, _u("D2:R!I20", "10.82", sheet="R", row=20, col=9)) == ["UNIT_UNKNOWN"]     # other sheet
    decl = _u("D2:p1l7", "All prices in US Dollars (USD) per piece, ex-GST.", page=1, line=7)
    assert _inherit(decl, _u("D2:p1l30", "0.0864", page=1, line=30), "0.0864") == ["UNIT_INHERITED"]
    assert _inherit(_u("D2:p1l2", "Delivered per box to Chakan", page=1, line=2),
                    _u("D2:p1l30", "0.0864", page=1, line=30), "0.0864") == ["UNIT_UNKNOWN"]       # no price word/declaration


def test_slab_only_line_inherits_header_unit():
    """Live finding: V1's lines carry only quantity-slab prices; the header unit was never checked for them."""
    from app.ingest.schemas import Evidence, LineQuote, Price, Slab
    from app.ingest.verify import check_inheritance
    hdr = _u("D2:Q!H5", "Rate (₹ per pc) — quantity slabs (annual)", sheet="Q", row=5, col=8)
    cells = {c: _u(f"D2:Q!{c}8", v, sheet="Q", row=8, col=col) for c, v, col in (("H", "7.43", 8), ("I", "7.01", 9), ("J", "6.73", 10))}
    lq = LineQuote(vendor_line_ref="1", description_as_stated="x", unit_class="PER_BOX", unit_source="INHERITED_FROM_CONTEXT",
                   unit_inherited_from=Evidence(unit_ids=[hdr.id], quote=hdr.text),
                   slabs=[Slab(price=Price(value_as_stated=u.text, currency_source="INHERITED_FROM_CONTEXT",
                                           evidence=Evidence(unit_ids=[u.id], quote=u.text))) for u in cells.values()])
    assert check_inheritance(lq, {hdr.id: hdr, **{u.id: u for u in cells.values()}}).reasons == ["UNIT_INHERITED"]
