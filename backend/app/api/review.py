"""Review actions (REV-4, §6.5): Accept / Accept suggestion / Correct / Mark missing / Override /
Confirm reference. Each writes a Resolution + AuditEvent and triggers a global recompute (VAL-5)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.db.models import AuditEvent, NormalizedQuote, RfxLine, Vendor
from app.process.recompute import ResolutionError, record_resolution
from app.process.run import recompute_rfx

router = APIRouter(prefix="/rfx")
packs_router = APIRouter()


class ResolveBody(BaseModel):
    vendor_id: int
    type: str  # ACCEPT / ACCEPT_SUGGESTION / CORRECT / MARK_MISSING / OVERRIDE / REFERENCE_CONFIRMATION
    line_no: int | None = None
    value: str | None = None
    reason: str | None = None
    choice: str | None = None
    actor: str = "buyer"


@router.post("/{rfx_id}/resolutions")
def resolve(rfx_id: int, body: ResolveBody, request: Request):
    sf, storage = request.app.state.session_factory, request.app.state.storage
    type_, value, reason = body.type.upper(), body.value, body.reason
    if type_ == "ACCEPT_SUGGESTION":  # REV AC: accepting a UNIT_SUSPECT suggestion records the chosen unit
        with sf() as s:
            line = s.scalar(select(RfxLine).where(RfxLine.rfx_id == rfx_id, RfxLine.line_no == body.line_no))
            q = line and s.scalar(select(NormalizedQuote).where(NormalizedQuote.rfx_line_id == line.id,
                                                                NormalizedQuote.vendor_id == body.vendor_id))
        sug = next((t.get("suggestion") for t in (q.trace if q else []) if t.get("suggestion")), None)
        if sug is None:
            raise HTTPException(409, "no unit suggestion on this cell")
        type_, value = "CORRECT", sug["suggested_unit_price"]
        reason = reason or f"accepted UNIT_SUSPECT suggestion: divide by {sug['divide_by']}"
    try:
        r = record_resolution(sf, rfx_id, vendor_id=body.vendor_id, type=type_, actor=body.actor, line_no=body.line_no,
                              value=value, reason=reason, choice=body.choice)
    except ResolutionError as e:
        raise HTTPException(422, str(e))
    snap = recompute_rfx(sf, storage, rfx_id, actor=body.actor, cause=f"resolution {r.id}")
    return {"resolution_id": r.id, "type": r.type, "snapshot_hash": snap}


@router.get("/{rfx_id}/review")
def review_queue(rfx_id: int, request: Request):
    """REV-1/2: one queue (UNRESOLVED, NEEDS_REVIEW, NEW_WARNING_AFTER_REVIEW, Unverified eligibility items,
    pending freight estimates), decision-sensitive first by quantified impact (DL-28), then money at risk."""
    from decimal import Decimal
    from statistics import median

    from app.analysis.scenario import ScenarioParams, run_scenario
    from app.db.models import EligibilityResult, Question
    sf = request.app.state.session_factory
    with sf() as s:
        lines = {l.id: l for l in s.scalars(select(RfxLine).where(RfxLine.rfx_id == rfx_id))}
        names = {v.id: v.name for v in s.scalars(select(Vendor))}
        qs = list(s.scalars(select(NormalizedQuote).where(NormalizedQuote.rfx_line_id.in_(list(lines)))))
        questions = {q.id: q for q in s.scalars(select(Question).where(Question.rfx_id == rfx_id))}
        unverified = [(e.vendor_id, questions[e.question_id], e.reason) for e in s.scalars(
            select(EligibilityResult).where(EligibilityResult.question_id.in_(list(questions)))) if e.state == "UNVERIFIED"]
    sc = run_scenario(sf, rfx_id, ScenarioParams()) if lines else {"decision_sensitive_lines": [], "freight_dependent_lines": []}
    sens: dict[tuple[int, str], list] = {}
    for d in sc["decision_sensitive_lines"]:
        for i in d["inputs"]:
            sens.setdefault((d["line_no"], i["vendor"]), []).append(i)
    by_line: dict[int, list] = {}
    for q in qs:
        if q.unit_price_inr_ex_gst is not None:
            by_line.setdefault(q.rfx_line_id, []).append((q.vendor_id, Decimal(q.unit_price_inr_ex_gst)))

    def impact(inputs) -> Decimal:
        return max((abs(Decimal(i["annual_inr_delta"])) for i in inputs if i.get("annual_inr_delta")),
                   default=Decimal(1) if inputs else Decimal(0))

    items = []
    for q in qs:
        new_warn = "NEW_WARNING_AFTER_REVIEW" in (q.flags or [])
        if q.unit_status not in ("UNRESOLVED", "NEEDS_REVIEW") and not new_warn:
            continue
        l = lines[q.rfx_line_id]
        peers = [p for v, p in by_line.get(l.id, []) if v != q.vendor_id]
        cand = next((t.get("candidate") for t in reversed(q.trace) if t.get("candidate")), None)
        vals = [Decimal(median(peers))] if peers else []
        if q.unit_price_inr_ex_gst or cand:
            vals.append(Decimal(q.unit_price_inr_ex_gst or cand))
        risk = (max(vals) * l.annual_qty) if vals else Decimal(0)
        sug = next((t.get("suggestion") for t in q.trace if t.get("suggestion")), None)
        ev = next((t for t in q.trace if t.get("step") == "evidence"), None)
        si = sens.get((l.line_no, names.get(q.vendor_id)), [])
        items.append({"kind": "CELL", "vendor_id": q.vendor_id, "vendor": names.get(q.vendor_id), "line_no": l.line_no,
                      "sku": l.sku_code, "status": q.unit_status, "reasons": q.unit_reasons, "flags": q.flags,
                      "value": q.unit_price_inr_ex_gst, "candidate": cand, "suggestion": sug, "source": ev,
                      "severity": "blocking" if q.unit_status == "UNRESOLVED" else "advisory",
                      "decision_sensitive": bool(si), "sensitivity": si, "impact_inr": str(impact(si)),
                      "money_at_risk_inr": str(risk.quantize(Decimal(1)))})
    for d in sc["freight_dependent_lines"]:  # pending freight estimates (REV-1)
        l = next(x for x in lines.values() if x.line_no == d["line_no"])
        vid = next(k for k, v in names.items() if v == d["vendor"])
        si = sens.get((l.line_no, d["vendor"]), [])
        items.append({"kind": "FREIGHT_ESTIMATE", "vendor_id": vid, "vendor": d["vendor"], "line_no": l.line_no, "sku": l.sku_code,
                      "status": None, "reasons": ["FREIGHT_UNKNOWN"], "severity": "advisory", "break_even": d["break_even_inr_per_box"],
                      "decision_sensitive": True, "sensitivity": si, "impact_inr": str(impact(si)),
                      "money_at_risk_inr": str((Decimal(d["break_even_inr_per_box"]) * l.annual_qty).quantize(Decimal(1)))})
    for vid, q, reason in unverified:
        items.append({"kind": "ELIGIBILITY", "vendor_id": vid, "vendor": names.get(vid), "line_no": None, "question": q.no,
                      "key": q.requirement_key, "section": q.section, "status": "UNVERIFIED", "reasons": [reason],
                      "severity": "advisory", "decision_sensitive": False, "sensitivity": [], "impact_inr": "0",
                      "money_at_risk_inr": "0"})
    items.sort(key=lambda i: (not i["decision_sensitive"], -Decimal(i["impact_inr"]), i["severity"] != "blocking",
                              -Decimal(i["money_at_risk_inr"]), i["line_no"] or 0, i["vendor_id"]))
    return {"rfx_id": rfx_id, "items": items}


@router.get("/{rfx_id}/cells/{vendor_id}/{line_no}")
def provenance(rfx_id: int, vendor_id: int, line_no: int, request: Request):
    """Provenance drawer (REV-3): the cell, its full trace (as quoted → conversions → checks), cited source units,
    the original Phase A read and every resolution on it."""
    from app.db.models import PhaseACell, Resolution
    sf = request.app.state.session_factory
    with sf() as s:
        line = s.scalar(select(RfxLine).where(RfxLine.rfx_id == rfx_id, RfxLine.line_no == line_no))
        if line is None:
            raise HTTPException(404, "no such line")
        q = s.scalar(select(NormalizedQuote).where(NormalizedQuote.rfx_line_id == line.id, NormalizedQuote.vendor_id == vendor_id))
        pa = s.scalar(select(PhaseACell).where(PhaseACell.rfx_id == rfx_id, PhaseACell.vendor_id == vendor_id,
                                               PhaseACell.line_no == line_no))
        res = [{"id": r.id, "type": r.type, "value": r.value, "choice": r.choice, "reason": r.reason, "state": r.state,
                "actor": r.actor, "at": r.at.isoformat()} for r in s.scalars(select(Resolution).order_by(Resolution.id))
               if r.target.get("rfx_id") == rfx_id and r.target.get("vendor_id") == vendor_id
               and r.target.get("line_no") in (line_no, None)]
        if q is None:
            raise HTTPException(404, "no processed cell")
        return {"line": {"line_no": line.line_no, "sku": line.sku_code, "description": line.description, "ply": line.ply,
                         "annual_qty": line.annual_qty},
                "cell": {"value": q.unit_price_inr_ex_gst, "status": q.unit_status, "reasons": q.unit_reasons, "flags": q.flags,
                         "landed": q.landed_inr_ex_gst, "landed_status": q.landed_status, "freight_basis": q.freight_basis,
                         "weight_source": q.weight_source, "weight_g": q.weight_g, "constant_set_version": q.constant_set_version},
                "source": next((t for t in q.trace if t.get("step") == "evidence"), None),
                "trace": q.trace, "phase_a": pa.cell if pa else None, "resolutions": res}


# --- clarification pack (DL-32) -----------------------------------------------------------------
@router.post("/{rfx_id}/vendors/{vendor_id}/clarification-pack")
def generate_pack(rfx_id: int, vendor_id: int, request: Request):
    from app.clarify.pack import build_pack
    from app.db.models import ClarificationPack
    sf = request.app.state.session_factory
    p = build_pack(sf, rfx_id, vendor_id)
    with sf.begin() as s:
        cp = ClarificationPack(rfx_id=rfx_id, vendor_id=vendor_id, items=p["items"], generated_body=p["body"],
                               content_hash=p["content_hash"], status="draft", created_by="system")
        s.add(cp)
        s.flush()
        s.add(AuditEvent(actor="system", action="CLARIFICATION_PACK_GENERATED", target={"rfx_id": rfx_id, "vendor_id": vendor_id},
                         after={"pack_id": cp.id, "items": len(p["items"]), "content_hash": p["content_hash"]}))
        return {"pack_id": cp.id, "status": "draft", **p}


class PackEdit(BaseModel):
    body: str
    actor: str = "buyer"


@packs_router.put("/clarification-packs/{pack_id}")
def edit_pack(pack_id: int, body: PackEdit, request: Request):
    from app.db.models import ClarificationPack
    with request.app.state.session_factory.begin() as s:
        cp = s.get(ClarificationPack, pack_id)
        if cp is None:
            raise HTTPException(404, "no such pack")
        if cp.status != "draft":
            raise HTTPException(409, "an approved pack cannot be edited")
        cp.edited_body = body.body
        s.add(AuditEvent(actor=body.actor, action="CLARIFICATION_PACK_EDITED", target={"rfx_id": cp.rfx_id, "pack_id": pack_id}))
        return {"pack_id": pack_id, "status": cp.status}


class PackApprove(BaseModel):
    actor: str


@packs_router.post("/clarification-packs/{pack_id}/approve")
def approve_pack(pack_id: int, body: PackApprove, request: Request):
    """Never sent without buyer approval: approval places it in the (simulated) outbox."""
    from datetime import datetime, timezone
    from app.db.models import ClarificationPack, OutboxMessage, Rfx
    with request.app.state.session_factory.begin() as s:
        cp = s.get(ClarificationPack, pack_id)
        if cp is None:
            raise HTTPException(404, "no such pack")
        if cp.status != "draft":
            raise HTTPException(409, "already approved")
        v = s.get(Vendor, cp.vendor_id)
        text = cp.edited_body or cp.generated_body
        subject, _, rest = text.partition("\n")
        om = OutboxMessage(kind="CLARIFICATION", to_addr=v.contact_email,
                           subject=subject.removeprefix("Subject: ") or f"Clarification — {s.get(Rfx, cp.rfx_id).title}",
                           body=rest.lstrip("\n"), attachments=[])
        s.add(om)
        s.flush()
        cp.status, cp.approved_by, cp.approved_at, cp.outbox_message_id = "in_outbox", body.actor, datetime.now(timezone.utc), om.id
        s.add(AuditEvent(actor=body.actor, action="CLARIFICATION_PACK_APPROVED", target={"rfx_id": cp.rfx_id, "pack_id": pack_id},
                         after={"outbox_message_id": om.id, "edited": cp.edited_body is not None}))
        return {"pack_id": pack_id, "status": cp.status, "outbox_message_id": om.id}


@router.get("/{rfx_id}/audit")
def audit(rfx_id: int, request: Request):
    sf = request.app.state.session_factory
    with sf() as s:
        ev = [e for e in s.scalars(select(AuditEvent).order_by(AuditEvent.id)) if (e.target or {}).get("rfx_id") == rfx_id]
        return [{"id": e.id, "actor": e.actor, "at": e.at.isoformat(), "action": e.action, "target": e.target,
                 "before": e.before, "after": e.after, "reason": e.reason} for e in ev]
