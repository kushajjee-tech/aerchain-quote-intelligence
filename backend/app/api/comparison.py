"""Comparison grid API (M5a, CMP-1/2/3/8). Numbers come only from NormalizedQuote rows; the UI does
no business arithmetic. Excluded statuses render as chips (value null); best price uses the formal
inclusion policy (DL-16); awaiting vendors have a column but no cells (SC-10)."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select

from app.db.models import Invitation, NormalizedQuote, ProcessingSet, Response, Rfx, RfxLine, Vendor
from app.domain.enums import ValueStatus
from app.validate.status import includable

router = APIRouter(prefix="/rfx")


@router.get("/{rfx_id}/comparison")
def comparison(rfx_id: int, request: Request, basis: str = Query("unit", pattern="^(unit|landed|quoted)$")):
    from app.process.run import awarded_baseline_rows
    sf, st = request.app.state.session_factory, request.app.state.storage
    try:
        baseline = awarded_baseline_rows(sf, st, rfx_id)
    except Exception:  # an RFx without lines or seed baseline: no baseline, never a fabricated one
        baseline = {}
    return build_grid(sf, rfx_id, basis, baseline)


def build_grid(sf, rfx_id: int, basis: str = "unit", baseline: dict | None = None) -> dict:
    with sf() as s:
        rfx = s.get(Rfx, rfx_id)
        if rfx is None:
            raise HTTPException(404, "no such RFx")
        lines = list(s.scalars(select(RfxLine).where(RfxLine.rfx_id == rfx_id).order_by(RfxLine.line_no)))
        invs = list(s.scalars(select(Invitation).where(Invitation.rfx_id == rfx_id)))
        vendors = {v.id: v for v in s.scalars(select(Vendor).where(Vendor.id.in_([i.vendor_id for i in invs])))}
        responded = {r.vendor_id for r in s.scalars(select(Response).where(Response.rfx_id == rfx_id))}
        quotes = {(q.rfx_line_id, q.vendor_id): q for q in s.scalars(
            select(NormalizedQuote).where(NormalizedQuote.rfx_line_id.in_([l.id for l in lines])))}
        ps = s.scalar(select(ProcessingSet).where(ProcessingSet.rfx_id == rfx_id))
    side = vendor_side_info(sf, rfx_id, list(vendors))
    vendor_cols = [{"vendor_id": v.id, "name": v.name,
                    "state": "RESPONDED" if v.id in responded else "AWAITING_RESPONSE", **side.get(v.id, {})}
                   for v in sorted(vendors.values(), key=lambda v: v.id)]
    rows = []
    for l in lines:
        cells, best = {}, None
        for col in vendor_cols:
            vid = col["vendor_id"]
            if col["state"] == "AWAITING_RESPONSE":
                cells[vid] = {"state": "AWAITING_RESPONSE", "value": None, "status": None}
                continue
            q = quotes.get((l.id, vid))
            if q is None:
                cells[vid] = {"state": "PENDING_PROCESSING", "value": None, "status": None}
                continue
            status = q.landed_status if basis == "landed" else q.unit_status
            value = q.landed_inr_ex_gst if basis == "landed" else q.unit_price_inr_ex_gst
            if basis == "quoted":
                value = next((t.get("value") for t in q.trace if t.get("step") == "as_quoted"), None)
            tr = {t.get("step"): t for t in (q.trace or [])}
            asq, fx, disc, slab = tr.get("as_quoted") or {}, tr.get("fx"), tr.get("discount"), tr.get("slab")
            cells[vid] = {"value": value, "status": status, "reasons": q.unit_reasons, "flags": q.flags,
                          "freight_basis": q.freight_basis, "weight_source": q.weight_source,
                          "unit_price": q.unit_price_inr_ex_gst, "landed": q.landed_inr_ex_gst, "landed_status": q.landed_status,
                          "freight_inr_per_box": q.freight_inr_per_box,
                          "quoted": {"value": asq.get("value"), "unit_class": asq.get("unit_class"),
                                     "currency": (fx or {}).get("currency", "INR")} if asq else None,
                          "fx": {"rate": fx.get("rate"), "source": fx.get("source"), "as_of": fx.get("as_of")} if fx else None,
                          "discount_pct": disc.get("pct") if disc else None,
                          "slab": {"chosen": slab.get("chosen"), **(slab.get("slab") or {})} if slab else None,
                          "gst": "ex-GST (RFx basis assumed: vendor silent)" if "GST_PER_RFX_BASIS" in (q.unit_reasons or [])
                                 else ("GST unclear" if "GST_UNCLEAR" in (q.unit_reasons or []) else "ex-GST (stated)"),
                          "candidate": next((t.get("candidate") for t in reversed(q.trace or []) if t.get("candidate")), None)}
            if basis != "quoted" and value is not None and includable(ValueStatus(status)) \
                    and "ALTERNATE" not in (q.flags or []):
                if best is None or Decimal(value) < Decimal(cells[best]["value"]):
                    best = vid
        rows.append({"line_no": l.line_no, "sku_code": l.sku_code, "description": l.description, "item_type": l.item_type,
                     "ply": l.ply, "flute": l.flute_profile, "dims_mm": l.dims_mm, "gsm": [x.get("gsm") for x in (l.layers or [])],
                     "printing": l.printing, "food_contact": l.food_contact,
                     "annual_qty": l.annual_qty, "cells": cells, "best_vendor_id": best,
                     **_baseline_fields((baseline or {}).get(l.line_no), cells.get(best) if best else None)})
    return {"rfx_id": rfx_id, "title": rfx.title, "basis": basis,
            "provisional": not (ps and ps.phase_b_status == "final"),
            "snapshot_hash": ps.snapshot_hash if ps else None, "vendors": vendor_cols, "rows": rows,
            "vendor_summary": vendor_summary(rows, vendor_cols, basis)}


def _baseline_fields(b: dict | None, best_cell: dict | None) -> dict:
    """Last year's awarded price for the line and the best comparable price's variance from it (null when either is absent)."""
    if not b:
        return {"baseline": None, "best_vs_baseline_pct": None}
    base = Decimal(b["unit_price_inr_ex_gst"])
    pct = None
    if best_cell and best_cell.get("value") is not None and base:
        pct = str(((Decimal(best_cell["value"]) - base) / base * 100).quantize(Decimal("0.1")))
    return {"baseline": {"unit_price_inr_ex_gst": b["unit_price_inr_ex_gst"], "freight_basis": b.get("freight_basis")},
            "best_vs_baseline_pct": pct}


def vendor_summary(rows: list[dict], vendor_cols: list[dict], basis: str) -> list[dict]:
    """By-supplier view: coverage, exceptions and spend on comparable lines only. A total is given only when the
    supplier has a comparable price on every line (like-for-like); otherwise it is null, never a partial sum shown as total."""
    from app.normalize.money import line_total
    out = []
    for col in vendor_cols:
        vid = col["vendor_id"]
        quoted = comparable = exceptions = missing = 0
        spend = Decimal(0)
        for r in rows:
            c = r["cells"][vid]
            st = c.get("status")
            if st is None:
                continue
            if st == "MISSING":
                missing += 1
                continue
            quoted += 1
            if basis != "quoted" and c.get("value") is not None and includable(ValueStatus(st)) and "ALTERNATE" not in (c.get("flags") or []):
                comparable += 1
                spend += line_total(Decimal(c["value"]), r["annual_qty"])
            else:
                exceptions += 1
        out.append({"vendor_id": vid, "name": col["name"], "lines": len(rows), "quoted": quoted, "not_quoted": missing,
                    "comparable": comparable, "exceptions": exceptions,
                    "comparable_spend_inr": str(spend) if comparable else None,
                    "complete_total_inr": str(spend) if comparable == len(rows) and rows else None})
    return out


def vendor_side_info(sf, rfx_id: int, vendor_ids: list[int]) -> dict[int, dict]:
    """FN-10: questionnaire results and attached documents beside each vendor's prices (labels per ELG-6)."""
    from app.db.models import DocumentFact, EligibilityResult, Question
    from app.eligibility.rules import LINE_FLAG, QResult, label, roll_up
    out: dict[int, dict] = {}
    with sf() as s:
        qs = {q.id: q for q in s.scalars(select(Question).where(Question.rfx_id == rfx_id))}
        for vid in vendor_ids:
            rows = list(s.scalars(select(EligibilityResult).where(EligibilityResult.vendor_id == vid,
                                                                  EligibilityResult.question_id.in_(list(qs)))))
            res = [QResult(qs[r.question_id].requirement_key, qs[r.question_id].section, r.state, r.reason,
                           LINE_FLAG.get(qs[r.question_id].applicability)) for r in rows]
            docs = [{"filename": d.filename, "doc_type": d.doc_type, "expiry_date": d.expiry_date, "fact_status": d.fact_status,
                     "evidence_ref": f"docfact:{d.id}"}
                    for d in s.scalars(select(DocumentFact).where(DocumentFact.rfx_id == rfx_id, DocumentFact.vendor_id == vid))]
            out[vid] = {"eligibility": ({sec.lower(): label(roll_up(res, sec)[0]) for sec in ("QUALITY", "COMMERCIAL")}
                                        if rows else None),
                        "documents": docs}
    return out
