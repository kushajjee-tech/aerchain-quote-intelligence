"""Phase A (DL-9): one vendor's submissions → per-RFx-line normalised cells. Reads no other vendor."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.ingest.extract import TextExtractionResult
from app.ingest.match import match_lines, reference_scope
from app.ingest.spec_diff import spec_diff
from app.ingest.verify import VerifiedLine
from app.normalize.baseline import price_candidates
from app.normalize.engine import NormalizedCell, QuoteInput, ResponseContext, normalize_cell

_NON_STATUS = {"UNIT_DICT_DISAGREES"}


def _discount_scope(scope: str):
    sc = (scope or "all").strip().lower().replace(" ", "")
    if sc in ("all", "allitems", "all_items"):
        return "all"
    if sc.startswith("ply="):
        try:
            return {"ply": int(sc.split("=", 1)[1])}
        except ValueError:
            return None
    return None  # unclear scope → not applied silently (UNRESOLVED via verification flags in M4b)


def response_context(rfx: dict, results: list[TextExtractionResult], fx_rates: dict | None = None) -> ResponseContext:
    """Merge every submission of one vendor (DL-23). Only terms whose evidence verified are used."""
    statements = [r.extraction.gst_statement for r in results]
    gst = "AMBIGUOUS" if "AMBIGUOUS" in statements else ("STATED" if "STATED" in statements else "SILENT")
    exclusive = None
    freight_terms, discounts = [], []
    for r in results:
        for term, reasons in zip(r.extraction.document_terms, r.term_reasons):
            if reasons:
                continue
            if term.type == "GST":
                t = term.text.lower()
                exclusive = True if ("exclusive" in t or "extra" in t) else (False if "inclusive" in t else exclusive)
            if term.type == "FREIGHT":
                freight_terms.append(term.model_dump())
            if term.type == "DISCOUNT_PCT" and term.value:
                sc = _discount_scope(term.scope)
                if sc is not None:
                    discounts.append({"pct": Decimal(term.value.replace("%", "").strip()), "scope": sc, "text": term.text})
    return ResponseContext(gst_statement=gst, gst_stated_exclusive=exclusive,
                           rfx_gst_basis=rfx["response_basis"].get("gst_treatment"), freight_terms=freight_terms,
                           discounts=discounts, fx_rates=fx_rates or {})


def quote_input(v: VerifiedLine, extra_reasons: list[str] | None = None, image_sourced: bool = False) -> QuoteInput:
    q = v.quote
    value = Decimal(str(q.price.value)) if q.price and q.price.value is not None else None
    cur_src = (q.price.currency_as_stated if q.price else None) or next(
        (s.price.currency_as_stated for s in q.slabs if s.price.currency_as_stated), None) or "INR"
    currency = "USD" if cur_src.strip().upper() in ("USD", "$", "US$", "US DOLLAR") else "INR"
    slabs = [{"min_qty": s.min_qty, "max_qty": s.max_qty, "value": str(s.price.value)}
             for s in q.slabs if s.price.value is not None]
    return QuoteInput(
        quoted=True, value=value, unit_class=v.unit_class, slabs=slabs, image_sourced=image_sourced, currency=currency,
        verification_reasons=[r for r in v.reasons if r not in _NON_STATUS] + list(extra_reasons or []),
        flags=list(v.flags) + (["DERIVED_FROM_GROUP_PRICE"] if q.applies_to_group else []),
        vendor_weight_g=Decimal(str(q.vendor_box_weight_g)) if q.vendor_box_weight_g else None,
    )


def _evidence_step(v: VerifiedLine, r) -> dict:
    """Provenance (REV-3): the cited units with their text and source file, for the drawer."""
    q = v.quote
    evs = ([("price", q.price.evidence)] if q.price else []) + [(f"slab {i + 1}", s.price.evidence) for i, s in enumerate(q.slabs)]
    if q.unit_inherited_from:
        evs.append(("unit (inherited)", q.unit_inherited_from))
    if q.applies_to_group:
        evs.append(("group scope", q.applies_to_group.evidence))
    units = r.units if r else {}
    files = r.filenames if r else {}
    cites = []
    for role, ev in evs:
        cites.append({"role": role, "quote": ev.quote, "units": [
            {"id": u, "text": units[u].text if u in units else None, "document": files.get(u.split(":")[0])} for u in ev.unit_ids]})
    return {"step": "evidence", "vendor_line_ref": q.vendor_line_ref, "description_as_stated": q.description_as_stated,
            "unit_as_stated": q.unit_as_stated, "verification": v.reasons, "cites": cites}


def cell_from_inputs(inputs: dict, fx_rates: dict, constants) -> NormalizedCell:
    """Deterministic: the same stored inputs + FX + constant set → the same Phase A cell."""
    from app.process.cells_io import ctx_from_json, input_from_json
    cell = normalize_cell(inputs["line"], input_from_json(inputs["q"]), ctx_from_json(inputs["ctx"], fx_rates, constants))
    cell.trace[0:0] = [dict(t) for t in inputs["pre_trace"]]
    cell.flags = sorted(set(cell.flags) - {"COMPLIANT"})
    return cell


@dataclass
class CellResult:
    line_no: int
    cell: NormalizedCell
    match_how: str | None
    inputs: dict | None = None


def phase_a(rfx: dict, results: list[TextExtractionResult], vendor_name: str | None = None,
            baseline_rows: list[dict] | None = None, confirmed_prices: bool = False, fx_rates: dict | None = None,
            ai_matches: dict[str, dict] | None = None, constants=None) -> list[CellResult]:
    from app.process.cells_io import ctx_to_json, input_to_json
    ctx = response_context(rfx, results, fx_rates)
    if constants is not None:
        ctx.constants = constants
    verified = [v for r in results for v in r.lines]
    origin = {id(v): r for r in results for v in r.lines}
    m = match_lines(rfx["lines"], verified, ai_matches)
    has_ref = any(ref.type == "PRIOR_UNSPECIFIED" for r in results for ref in r.extraction.references)
    ref_lines = set(reference_scope(rfx["lines"], m)) if has_ref else set()
    cands = price_candidates(rfx["lines"], sorted(ref_lines), vendor_name, baseline_rows or []) if (ref_lines and vendor_name) else {}
    out = []
    for line in rfx["lines"]:
        n = line["line_no"]
        spec_trace = None
        if n in m.individual:
            assigns = m.individual[n]
            extra = (["MATCH_CONFLICT"] if len(assigns) > 1 else []) + \
                    (["MATCH_LOW"] if any(a.confidence == "LOW" for a in assigns) else [])
            q = quote_input(assigns[0].source, extra)
            how = assigns[0].how
            verdict, diffs = spec_diff(line, assigns[0].source.quote.spec_as_stated)
            q.flags.append(verdict if verdict != "COMPLIANT" else "COMPLIANT")
            spec_trace = {"step": "spec_diff", "verdict": verdict, "differences": diffs,
                          "match": {"how": how, "confidence": assigns[0].confidence, "vendor_lines": len(assigns)}}
        elif n in m.group:
            q, how = quote_input(m.group[n].source), "group"
        elif n in ref_lines:
            c = cands.get(n)
            q = QuoteInput(reference=True, reference_reason=c.reason if c else None,
                           reference_candidate=c.candidate if c else None, reference_confirmed=confirmed_prices,
                           baseline_freight_basis=c.baseline_freight_basis if c else None)
            how = "reference"
        else:
            q, how = QuoteInput(quoted=False), None
        pre_trace = []
        src = (m.individual[n][0].source if n in m.individual else m.group[n].source if n in m.group else None)
        if spec_trace:
            pre_trace.append(spec_trace)
        if src is not None:
            pre_trace.append(_evidence_step(src, origin.get(id(src))))
        inputs = {"line": line, "q": input_to_json(q), "ctx": ctx_to_json(ctx), "pre_trace": pre_trace}
        out.append(CellResult(n, cell_from_inputs(inputs, ctx.fx_rates, ctx.constants), how, inputs))
    return out
