"""Scenario, readiness, acknowledgement and memo API (AWD-1…4, AWD-7; DL-16, DL-25)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.analysis.scenario import ScenarioParams, readiness_items, run_scenario
from app.award.memo import render_memo
from app.db.models import AuditEvent, AwardDecision, NormalizedQuote, Rfx, RfxLine, Scenario, Vendor
from app.normalize.money import line_total
from app.process.run import awarded_baseline_rows
from app.validate.status import OverrideRequired

router = APIRouter()


class ScenarioBody(BaseModel):
    name: str = "scenario"
    strategy: str = "cheapest_per_line"
    vendor_id: int | None = None
    context: str = "formal"
    basis: str | None = None
    eligibility_mode: str = "strict"
    eligibility_scope: str = "quality"
    include_alternates: bool = False
    include_needs_review: bool = False
    override_id: int | None = None
    override_reason: str | None = None
    actor: str = "buyer"
    exclude_vendor_ids: list[int] = []
    line_nos: list[int] | None = None


def _needs_review_override(sf, rfx_id: int, actor: str, reason: str) -> int:
    """DL-16: an audited buyer override listing the NEEDS_REVIEW cells and their money at risk."""
    with sf.begin() as s:
        lines = {l.id: l for l in s.scalars(select(RfxLine).where(RfxLine.rfx_id == rfx_id))}
        names = {v.id: v.name for v in s.scalars(select(Vendor))}
        from decimal import Decimal
        cells = [{"line_no": lines[q.rfx_line_id].line_no, "vendor": names[q.vendor_id], "value": q.unit_price_inr_ex_gst,
                  "money_at_risk_inr": str(line_total(Decimal(q.unit_price_inr_ex_gst), lines[q.rfx_line_id].annual_qty))}
                 for q in s.scalars(select(NormalizedQuote).where(NormalizedQuote.rfx_line_id.in_(list(lines))))
                 if q.unit_status == "NEEDS_REVIEW" and q.unit_price_inr_ex_gst]
        ev = AuditEvent(actor=actor, action="NEEDS_REVIEW_OVERRIDE", target={"rfx_id": rfx_id},
                        after={"cells": sorted(cells, key=lambda c: (c["line_no"], c["vendor"]))}, reason=reason)
        s.add(ev)
        s.flush()
        return ev.id


def _valid_override(sf, rfx_id: int, override_id: int) -> bool:
    with sf() as s:
        ev = s.get(AuditEvent, override_id)
        return bool(ev and ev.action == "NEEDS_REVIEW_OVERRIDE" and (ev.target or {}).get("rfx_id") == rfx_id)


def _compute(sf, storage, rfx_id: int, body: ScenarioBody) -> dict:
    params = body.model_dump(exclude={"name", "override_reason", "actor"})
    if body.context == "formal" and body.include_needs_review:
        if body.override_id is None and body.override_reason:
            params["override_id"] = _needs_review_override(sf, rfx_id, body.actor, body.override_reason)
        elif body.override_id is not None and not _valid_override(sf, rfx_id, body.override_id):
            raise HTTPException(409, "override_id does not name an audited NEEDS_REVIEW override for this RFx")
    try:
        p = ScenarioParams(**params)
    except ValueError as e:
        raise HTTPException(422, str(e))
    try:
        return run_scenario(sf, rfx_id, p, awarded_baseline_rows(sf, storage, rfx_id))
    except OverrideRequired as e:
        raise HTTPException(409, str(e))


def _save(sf, rfx_id: int, name: str, result: dict) -> int:
    with sf.begin() as s:
        sc = Scenario(rfx_id=rfx_id, name=name, context=result["params"]["context"], params=result["params"],
                      result_snapshot=result, needs_review_override_id=result["params"]["override_id"],
                      cells_used_fingerprints={"cells": {f"{c['vendor_id']}:{c['line_no']}": c["fingerprint"]
                                                         for c in result["cells_used"]}},
                      computed_at=datetime.now(timezone.utc))
        s.add(sc)
        s.flush()
        return sc.id


@router.post("/rfx/{rfx_id}/scenarios")
def create_scenario(rfx_id: int, body: ScenarioBody, request: Request):
    sf, storage = request.app.state.session_factory, request.app.state.storage
    with sf() as s:
        if s.get(Rfx, rfx_id) is None:
            raise HTTPException(404, "no such RFx")
    result = _compute(sf, storage, rfx_id, body)
    return {"scenario_id": _save(sf, rfx_id, body.name, result), **result}


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: int, request: Request):
    with request.app.state.session_factory() as s:
        sc = s.get(Scenario, scenario_id)
        if sc is None:
            raise HTTPException(404, "no such scenario")
        return {"scenario_id": sc.id, "stale": sc.stale, **sc.result_snapshot}


@router.post("/scenarios/{scenario_id}/recompute")
def recompute_scenario(scenario_id: int, request: Request):
    """AWD-7: opening a stale scenario offers recompute → a new scenario with the same params; formal policy
    re-applied for exploratory promotions is the caller's choice of context."""
    sf, storage = request.app.state.session_factory, request.app.state.storage
    with sf() as s:
        sc = s.get(Scenario, scenario_id)
        if sc is None:
            raise HTTPException(404, "no such scenario")
        rfx_id, name, params = sc.rfx_id, sc.name, dict(sc.params)
    body = ScenarioBody(name=name, **{k: v for k, v in params.items() if k in ScenarioBody.model_fields})
    result = _compute(sf, storage, rfx_id, body)
    return {"scenario_id": _save(sf, rfx_id, name, result), "replaces": scenario_id, **result}


@router.get("/scenarios/{scenario_id}/readiness")
def readiness(scenario_id: int, request: Request):
    sf = request.app.state.session_factory
    with sf() as s:
        sc = s.get(Scenario, scenario_id)
        if sc is None:
            raise HTTPException(404, "no such scenario")
        rfx_id, result, stale, ctx = sc.rfx_id, sc.result_snapshot, sc.stale, sc.context
    items = readiness_items(sf, rfx_id, result)
    return {"scenario_id": scenario_id, "stale": stale, "context": ctx, "items": items,
            "requires_acknowledgement": bool(items), "can_acknowledge": not stale and ctx == "formal"}


class AckBody(BaseModel):
    actor: str
    reason: str | None = None


@router.post("/scenarios/{scenario_id}/acknowledge")
def acknowledge(scenario_id: int, body: AckBody, request: Request):
    """AWD-3: audited acknowledgement of every readiness item. Formal, non-stale scenarios only."""
    sf = request.app.state.session_factory
    r = readiness(scenario_id, request)
    if r["stale"]:
        raise HTTPException(409, "scenario is stale: recompute it first (AWD-7)")
    if r["context"] != "formal":
        raise HTTPException(409, "an exploratory result must be recomputed under the formal policy before award")
    with sf.begin() as s:
        sc = s.get(Scenario, scenario_id)
        ev = AuditEvent(actor=body.actor, action="READINESS_ACK", target={"rfx_id": sc.rfx_id, "scenario_id": sc.id},
                        after={"items": r["items"]}, reason=body.reason)
        s.add(ev)
        s.flush()
        if any(i["kind"] == "FREIGHT_DEPENDENT" for i in r["items"]):
            sc.freight_dependency_ack_id = ev.id
        for old in s.scalars(select(AwardDecision).where(AwardDecision.scenario_id == sc.id,
                                                         AwardDecision.acknowledged_at.is_not(None))):
            old.superseded = True
        title = s.get(Rfx, sc.rfx_id).title
        now = datetime.now(timezone.utc)
        ad = AwardDecision(scenario_id=sc.id, readiness_items=r["items"], acknowledged_by=body.actor, acknowledged_at=now,
                           memo=render_memo(title, sc.id, sc.result_snapshot, readiness=r["items"],
                                            acknowledged=(body.actor, now.date().isoformat())))
        s.add(ad)
        s.flush()
        return {"award_decision_id": ad.id, "audit_event_id": ev.id, "items": r["items"]}


@router.post("/scenarios/{scenario_id}/memo")
def draft_memo(scenario_id: int, request: Request):
    sf = request.app.state.session_factory
    with sf.begin() as s:
        sc = s.get(Scenario, scenario_id)
        if sc is None or not sc.result_snapshot:
            raise HTTPException(404, "no such scenario")
        acked = s.scalar(select(AwardDecision).where(AwardDecision.scenario_id == sc.id, AwardDecision.acknowledged_at.is_not(None),
                                                     AwardDecision.superseded.is_(False)).order_by(AwardDecision.id.desc()))
        if acked is not None and not sc.stale:  # the acknowledged memo is the record; never re-rendered as a draft
            return {"award_decision_id": acked.id, "memo_markdown": acked.memo, "acknowledged": True}
        rfx = s.get(Rfx, sc.rfx_id) if sc.rfx_id else None
        title = request.query_params.get("title") or (rfx.title if rfx else "RFx")
        items = readiness_items(sf, sc.rfx_id, sc.result_snapshot) if sc.rfx_id else []
        memo = render_memo(title, sc.id, sc.result_snapshot, readiness=items)
        ad = AwardDecision(scenario_id=sc.id, memo=memo, readiness_items=items)
        s.add(ad)
        s.flush()
        return {"award_decision_id": ad.id, "memo_markdown": memo}
