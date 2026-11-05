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
    return build_grid(request.app.state.session_factory, rfx_id, basis)


def build_grid(sf, rfx_id: int, basis: str = "unit") -> dict:
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
            cells[vid] = {"value": value, "status": status, "reasons": q.unit_reasons, "flags": q.flags,
                          "freight_basis": q.freight_basis, "weight_source": q.weight_source}
            if basis != "quoted" and value is not None and includable(ValueStatus(status)) \
                    and "ALTERNATE" not in (q.flags or []):
                if best is None or Decimal(value) < Decimal(cells[best]["value"]):
                    best = vid
        rows.append({"line_no": l.line_no, "sku_code": l.sku_code, "description": l.description, "item_type": l.item_type,
                     "ply": l.ply, "annual_qty": l.annual_qty, "cells": cells, "best_vendor_id": best})
    return {"rfx_id": rfx_id, "title": rfx.title, "basis": basis,
            "provisional": not (ps and ps.phase_b_status == "final"),
            "snapshot_hash": ps.snapshot_hash if ps else None, "vendors": vendor_cols, "rows": rows}


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
