"""Slice processing (S): delivered submissions → live TEXT extraction → Phase A per vendor →
Phase B across vendors → persist. A vendor whose extraction fails is marked failed and left out of
the comparison (never half-applied); other vendors continue."""
from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import select

from app.db.models import ExtractionRun, Response, Rfx, RfxLine, Vendor
from app.process.eligibility_run import evaluate_and_store, question_dicts
from app.ingest.extract import run_text_extraction
from app.ingest.parsers import parse_message
from app.llm.gateway import LLMError, LLMGateway
from app.llm.prompts import EXTRACT_TEXT_V1
from app.process.phase_a import phase_a
from app.ingest.match import match_lines
from app.ingest.match_ai import propose_matches
from app.process.recompute import drop_vendor_cells, recompute, store_phase_a


def rfx_dict(sf, rfx_id: int) -> dict:
    with sf() as s:
        rfx = s.get(Rfx, rfx_id)
        lines = list(s.scalars(select(RfxLine).where(RfxLine.rfx_id == rfx_id).order_by(RfxLine.line_no)))
        return {"response_basis": dict(rfx.response_basis or {}), "questionnaire": question_dicts(s, rfx_id), "lines": [
            {"line_no": l.line_no, "sku_code": l.sku_code, "description": l.description, "item_type": l.item_type,
             "dims_mm": l.dims_mm, "blank_size_mm": l.blank_size_mm, "ply": l.ply, "flute_profile": l.flute_profile,
             "layers": l.layers, "printing": l.printing, "annual_qty": l.annual_qty,
             "reference_unit_weight_g": l.reference_unit_weight_g, "reference_weight_source": l.reference_weight_source,
             "food_contact": l.food_contact, "requires_fsc": l.requires_fsc} for l in lines]}, {l.line_no: l.id for l in lines}


def awarded_baseline(storage, rfx: dict) -> dict[int, Decimal]:
    by_sku = {l["sku_code"]: l["line_no"] for l in rfx["lines"]}
    if not storage.exists("seed/baseline_prices.json"):
        return {}
    rows = json.loads(storage.read_text("seed/baseline_prices.json"))
    return {by_sku[r["sku"]]: Decimal(r["unit_price_inr_ex_gst"]) for r in rows if r.get("awarded") and r["sku"] in by_sku}


def awarded_baseline_rows(sf, storage, rfx_id: int) -> dict[int, dict]:
    """§5.9 savings input: last year's awarded row per line (price + freight basis)."""
    rfx, _ = rfx_dict(sf, rfx_id)
    by_sku = {l["sku_code"]: l["line_no"] for l in rfx["lines"]}
    if not storage.exists("seed/baseline_prices.json"):
        return {}
    rows = json.loads(storage.read_text("seed/baseline_prices.json"))
    return {by_sku[r["sku"]]: {"unit_price_inr_ex_gst": r["unit_price_inr_ex_gst"], "freight_basis": r.get("freight_basis")}
            for r in rows if r.get("awarded") and r["sku"] in by_sku}


def _extract_vendor(sf, storage, gw: LLMGateway, rfx: dict, rfx_id: int, resp: Response, name: str):
    """One vendor end to end (Phase A). Raises LLMError; on failure nothing of this run is kept."""
    results = []
    for sub in resp.submissions:
        _, docs = parse_message(storage.read_bytes(sub["path"]))
        results.append(run_text_extraction(gw, rfx, docs))
    verified = [v for r in results for v in r.lines]
    pre = match_lines(rfx["lines"], verified)
    taken = set(pre.individual)
    ai = propose_matches(gw, rfx["lines"], pre.unmatched, taken) if pre.unmatched else {}
    ai = {k: v for k, v in ai.items() if not v["conflicts_with_deterministic"]} | \
         {k: {**v, "confidence": "LOW"} for k, v in ai.items() if v["conflicts_with_deterministic"]}
    base_rows = json.loads(storage.read_text("seed/baseline_prices.json")) if storage.exists("seed/baseline_prices.json") else []
    from app.settings_.registry import active_constant_set, fx_rates
    out = phase_a(rfx, results, vendor_name=name, baseline_rows=base_rows, ai_matches=ai,
                  fx_rates=fx_rates(sf), constants=active_constant_set(sf))
    return results, {c.line_no: c.cell for c in out}, {c.line_no: c.inputs for c in out}


def store_references(sf, storage, rfx_id: int, vendor_id: int, name: str, results, cells: dict) -> None:
    """DL-20: one Reference per ambiguous statement, with both readings' candidates (nothing applied)."""
    from sqlalchemy import delete
    from app.db.models import Reference
    from app.normalize.baseline import term_candidates
    term_rows = json.loads(storage.read_text("seed/baseline_terms.json")) if storage.exists("seed/baseline_terms.json") else []
    stated = {t.type for r in results for t, reasons in zip(r.extraction.document_terms, r.term_reasons) if not reasons}
    with sf.begin() as s:
        s.execute(delete(Reference).where(Reference.rfx_id == rfx_id, Reference.vendor_id == vendor_id))
        for r in results:
            for ref in r.extraction.references:
                if ref.type != "PRIOR_UNSPECIFIED":
                    continue
                prices = []
                for n, c in sorted(cells.items()):
                    t = next((t for t in c.trace if t.get("step") == "reference"), None)
                    if t:
                        prices.append({"line_no": n, "reason": t.get("reason"), "candidate": t.get("candidate"),
                                       "baseline_freight_basis": t.get("baseline_freight_basis")})
                terms = term_candidates(name, stated, term_rows)
                s.add(Reference(rfx_id=rfx_id, vendor_id=vendor_id, type=ref.type, text=ref.scope_text,
                                evidence=[ref.evidence.model_dump()], scope_prices=[p["line_no"] for p in prices],
                                scope_terms=[t["term_type"] for t in terms],
                                candidates=[{"reading": "A_prices", **p} for p in prices] + [{"reading": "B_terms", **t} for t in terms]))


def process_vendor(sf, storage, gw: LLMGateway, rfx_id: int, resp_id: int, rfx: dict | None = None) -> tuple[str, dict | str]:
    """Extract + Phase A + eligibility for one response. Returns ("ok", cells) or ("failed", reason).
    A failed run leaves no rows of its own: the vendor's previous cells are removed, never half-replaced."""
    rfx = rfx or rfx_dict(sf, rfx_id)[0]
    with sf.begin() as s:
        resp = s.get(Response, resp_id)
        resp.status = "processing"
        name = s.get(Vendor, resp.vendor_id).name
        s.expunge(resp)
    try:
        results, cells, inputs = _extract_vendor(sf, storage, gw, rfx, rfx_id, resp, name)
    except LLMError as e:
        with sf.begin() as s:
            s.get(Response, resp_id).status = "failed"
            s.add(ExtractionRun(response_id=resp_id, model=gw.model, prompt_version=EXTRACT_TEXT_V1, path="TEXT",
                                status="failed", token_usage={"error": f"{type(e).__name__}: {e}"}))
        drop_vendor_cells(sf, rfx_id, resp.vendor_id)
        return "failed", f"{type(e).__name__}: {e}"
    flags = {f for l in rfx["lines"] for f in ("food_contact", "requires_fsc")
             if l.get(f) and str(cells[l["line_no"]].unit_status) != "MISSING"}
    evaluate_and_store(sf, rfx_id, resp.vendor_id, name, results, flags)
    store_references(sf, storage, rfx_id, resp.vendor_id, name, results, cells)
    store_phase_a(sf, rfx_id, {str(resp.vendor_id): cells}, {str(resp.vendor_id): inputs})
    with sf.begin() as s:
        r = s.get(Response, resp_id)
        r.status = "processed"
        r.coverage_count = sum(1 for c in cells.values() if str(c.unit_status) != "MISSING")
        s.add(ExtractionRun(response_id=resp_id, model=gw.model, prompt_version=EXTRACT_TEXT_V1, path="TEXT",
                            status="ok", token_usage={"submissions": len(resp.submissions)}))
    return "ok", cells


def process_rfx(sf, storage, gw: LLMGateway, rfx_id: int) -> dict:
    rfx, _ = rfx_dict(sf, rfx_id)
    with sf() as s:
        responses = list(s.scalars(select(Response).where(Response.rfx_id == rfx_id).order_by(Response.vendor_id)))
        names = {v.id: v.name for v in s.scalars(select(Vendor))}
    processed, failed = [], {}
    for resp in responses:
        if resp.status == "processed":  # unchanged since its last run (a new submission resets it to "received")
            processed.append(names[resp.vendor_id])
            continue
        state, out = process_vendor(sf, storage, gw, rfx_id, resp.id, rfx)
        if state == "ok":
            processed.append(names[resp.vendor_id])
        else:
            failed[names[resp.vendor_id]] = out
    snap = recompute_rfx(sf, storage, rfx_id, cause="processing run")
    return {"processed_vendors": sorted(processed), "failed": failed, "snapshot_hash": snap}


def rerun_vendor(sf, storage, gw: LLMGateway, rfx_id: int, vendor_id: int, actor: str = "buyer") -> dict:
    """EXT-11: re-run extraction for one response; resolutions carry forward by raw fingerprint (§6.5)."""
    with sf() as s:
        resp = s.scalar(select(Response).where(Response.rfx_id == rfx_id, Response.vendor_id == vendor_id))
        if resp is None:
            raise ValueError("no response from this vendor")
        resp_id = resp.id
    with sf.begin() as s:
        r = s.get(Response, resp_id)
        r.version = (r.version or 1) + 1
        from app.db.models import AuditEvent
        s.add(AuditEvent(actor=actor, action="RERUN_REQUESTED", target={"rfx_id": rfx_id, "vendor_id": vendor_id},
                         after={"response_version": r.version}))
    state, out = process_vendor(sf, storage, gw, rfx_id, resp_id)
    snap = recompute_rfx(sf, storage, rfx_id, actor=actor, cause=f"re-run vendor {vendor_id}")
    with sf() as s:
        from app.db.models import Resolution
        stale = [r.id for r in s.scalars(select(Resolution).where(Resolution.state == "stale"))
                 if (r.target or {}).get("rfx_id") == rfx_id and r.target.get("vendor_id") == vendor_id]
    return {"status": state, "error": out if state == "failed" else None, "snapshot_hash": snap,
            "stale_resolutions": stale}


def recompute_rfx(sf, storage, rfx_id: int, actor: str = "system", cause: str = "recompute") -> str | None:
    """Global recompute (VAL-5) from stored Phase A cells + active resolutions; no model call."""
    from app.settings_.registry import active_constant_set
    rfx, line_ids = rfx_dict(sf, rfx_id)
    return recompute(sf, rfx_id, line_ids, awarded_baseline(storage, rfx), actor=actor, cause=cause,
                     cs=active_constant_set(sf))


def renormalize_all(sf, storage, actor: str, cause: str) -> dict:
    """FX or constant-set change: rebuild every Phase A cell from its stored inputs, then recompute each RFx."""
    from sqlalchemy import select as _sel
    from app.db.models import PhaseACell
    from app.process.cells_io import to_json
    from app.process.phase_a import cell_from_inputs
    from app.settings_.registry import active_constant_set, fx_rates
    fx, cs = fx_rates(sf), active_constant_set(sf)
    rfx_ids = set()
    with sf.begin() as s:
        for row in s.scalars(_sel(PhaseACell)):
            if row.inputs:
                row.cell = to_json(cell_from_inputs(row.inputs, fx, cs))
                rfx_ids.add(row.rfx_id)
    return {rid: recompute_rfx(sf, storage, rid, actor=actor, cause=cause) for rid in sorted(rfx_ids)}
