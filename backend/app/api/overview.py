"""RFx overview for the UI (Home, Review, Vendors): RFx context, data-derived metrics, findings, vendor tracker,
progress and activity. Every figure is computed from stored data; nothing is hard-coded about the fixture.

Findings are DERIVED from eligibility results and normalised cells on every request, so they disappear when the
underlying data is resolved. Human review states live in FindingReview (latest) + AuditEvent (full history)."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.db.models import (AuditEvent, AwardDecision, EligibilityResult, FindingReview, InboxMessage, Invitation,
                           NormalizedQuote, ProcessingSet, Question, Response, Rfx, RfxLine, Scenario, Vendor)
from app.eligibility.rules import LINE_FLAG, QResult, label, roll_up

router = APIRouter(prefix="/rfx")

CATEGORIES = ["Quality & compliance", "Commercial terms", "Quote completeness", "Specification deviations", "Document validity"]
REASON_TEXT = {
    "READ_SINGLE_SOURCE": "read from an image by OCR only (single read)", "LOW_OCR_CONFIDENCE": "low OCR confidence",
    "UNIT_UNKNOWN": "pricing unit not stated or not verifiable", "UNIT_SUSPECT": "price ~100× its peers (unit suspect)",
    "EVIDENCE_NOT_FOUND": "value not found in the cited source", "REFERENCE_AMBIGUOUS": "\"same as last year\" is ambiguous",
    "BASELINE_SPEC_CHANGED": "last year's price was for a different specification",
    "BASELINE_NOT_FOR_VENDOR": "no last-year price from this vendor", "GST_UNCLEAR": "GST basis unclear",
    "MATCH_LOW": "line match uncertain", "MATCH_CONFLICT": "two vendor lines match one RFx line",
    "PRICE_CONFLICT": "conflicting prices", "SLAB_AMBIGUOUS": "quantity slab ambiguous", "FX_RATE_MISSING": "no FX rate set",
    "READ_DISAGREEMENT": "two reads disagree", "WEIGHT_ESTIMATED": "₹/kg converted with an estimated weight",
    "OUTLIER": "price outlier vs peers", "WEIGHT_MISMATCH": "vendor weight differs from reference",
    "MISSING_CONSTRUCTION_INPUT": "construction input missing for ₹/kg conversion",
    "ITEM_TYPE_NOT_WEIGHT_COMPUTABLE": "item type cannot be converted from ₹/kg",
}
OPEN_STATES = ("open", "confirmed", "clarification_requested")


def _fid(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, default=str).encode()).hexdigest()[:12]


def buyer_defaults(storage) -> dict:
    return json.loads(storage.read_text("seed/buyer.json")) if storage.exists("seed/buyer.json") else {}


def rfx_context(rfx: Rfx, storage) -> dict:
    d = buyer_defaults(storage)
    m = {**{"code": rfx.canonical_spec_version or d.get("rfx_code"), "buyer": d.get("organisation"),
            "category": d.get("category"), "buyer_name": d.get("buyer_name"), "plant": rfx.delivery_location or d.get("plant"), "currency": d.get("currency")},
         **{k: v for k, v in (rfx.meta or {}).items() if v}}
    return {"rfx_id": rfx.id, "title": rfx.title, "scope": rfx.scope, "status": rfx.status, "origin": rfx.origin,
            "kind": rfx.kind, "meta": m, "demo": True}


def _vendor_keys(storage) -> dict[str, str]:
    if not storage.exists("seed/vendors.json"):
        return {}
    return {v["email"]: v["key"] for v in json.loads(storage.read_text("seed/vendors.json"))}


def derive(sf, storage, rfx_id: int) -> dict:
    with sf() as s:
        rfx = s.get(Rfx, rfx_id)
        if rfx is None:
            raise HTTPException(404, "no such RFx")
        ctx = rfx_context(rfx, storage)
        lines = {l.id: l for l in s.scalars(select(RfxLine).where(RfxLine.rfx_id == rfx_id).order_by(RfxLine.line_no))}
        invs = list(s.scalars(select(Invitation).where(Invitation.rfx_id == rfx_id)))
        vendors = {v.id: v for v in s.scalars(select(Vendor).where(Vendor.id.in_([i.vendor_id for i in invs])))}
        responses = {r.vendor_id: r for r in s.scalars(select(Response).where(Response.rfx_id == rfx_id))}
        quotes = list(s.scalars(select(NormalizedQuote).where(NormalizedQuote.rfx_line_id.in_(list(lines)))))
        qs = {q.id: q for q in s.scalars(select(Question).where(Question.rfx_id == rfx_id))}
        elig = list(s.scalars(select(EligibilityResult).where(EligibilityResult.question_id.in_(list(qs)))))
        reviews = {r.finding_id: r for r in s.scalars(select(FindingReview).where(FindingReview.rfx_id == rfx_id))}
        ps = s.scalar(select(ProcessingSet).where(ProcessingSet.rfx_id == rfx_id))
        scen_ids = [x.id for x in s.scalars(select(Scenario).where(Scenario.rfx_id == rfx_id))]
        acked = s.scalar(select(AwardDecision).where(AwardDecision.scenario_id.in_(scen_ids), AwardDecision.acknowledged_at.is_not(None),
                                                     AwardDecision.superseded.is_(False))) if scen_ids else None
        paths = {sub["path"] for r in responses.values() for sub in (r.submissions or [])}
        inbox = {m.storage_path: m for m in s.scalars(select(InboxMessage)) if m.storage_path in paths}
        events = [e for e in s.scalars(select(AuditEvent).order_by(AuditEvent.id.desc())) if (e.target or {}).get("rfx_id") == rfx_id][:25]
        for x in [rfx, *lines.values(), *invs, *vendors.values(), *responses.values(), *quotes, *qs.values(), *elig,
                  *reviews.values(), *inbox.values(), *events] + ([ps] if ps else []) + ([acked] if acked else []):
            s.expunge(x)
    keys = _vendor_keys(storage)
    vkey = {vid: keys.get(v.contact_email, f"V{vid}") for vid, v in vendors.items()}
    by_vendor = defaultdict(list)
    for q in quotes:
        by_vendor[q.vendor_id].append(q)

    findings: list[dict] = []

    def add(severity, category, vid, title, *, statement=None, requirement=None, concern=None, lines_=None, source=None,
            confidence=None, kind, key, target=None):
        fid = _fid(rfx_id, kind, vid, key)
        rv = reviews.get(fid)
        findings.append({"id": fid, "kind": kind, "severity": severity, "category": category, "vendor_id": vid,
                         "vendor": vendors[vid].name if vid in vendors else None, "vendor_key": vkey.get(vid), "title": title,
                         "statement": statement, "requirement": requirement, "concern": concern, "lines": lines_ or [],
                         "source": source, "confidence": confidence, "target": target,
                         "review": {"state": rv.state, "comment": rv.comment, "actor": rv.actor, "at": rv.at.isoformat()}
                         if rv else {"state": "open"}})

    # a) questionnaire / document results that are not Pass (ELG; DL-3 Unverified ≠ Failed)
    for e in elig:
        q = qs[e.question_id]
        if e.state in ("PASS", "NOT_APPLICABLE"):
            continue
        prov = e.provenance or {}
        docs = prov.get("documents") or []
        doc_issue = any(w in (e.reason or "") for w in ("expired", "another entity", "not attached", "could not be read"))
        cat = "Document validity" if doc_issue else ("Commercial terms" if q.section == "COMMERCIAL" else "Quality & compliance")
        ans = (prov.get("answer") or {})
        add("blocker", cat, e.vendor_id,
            f"{q.requirement_key}: {label(e.state)} — {e.reason}",
            statement=(ans.get("text") or ans.get("value") or "Not provided"),
            requirement=q.text + (f" Pass rule: answer {q.pass_rule.get('op')} {q.pass_rule.get('value', '')}".rstrip() + "." if q.pass_rule else ""),
            concern=e.reason, source={"filename": (docs[0].get("filename") if docs else None),
                                      "evidence": (ans.get("evidence") or {}).get("unit_ids")},
            confidence="answer verified against its source" if not ans.get("verification") else "answer could not be verified",
            kind="eligibility", key=q.requirement_key, target=f"/vendors/{e.vendor_id}?tab=documents")

    # b) value-level findings grouped by vendor and reason
    for vid, qq in by_vendor.items():
        groups: dict[tuple, list] = defaultdict(list)
        for q in qq:
            ln = lines[q.rfx_line_id].line_no
            if q.unit_status == "UNRESOLVED":
                blocking = [r for r in (q.unit_reasons or []) if r in REASON_TEXT and r not in ("WEIGHT_ESTIMATED", "OUTLIER")]
                groups[("blocker", "UNRESOLVED", tuple(sorted(blocking)) or ("UNRESOLVED",))].append(ln)
            elif q.unit_status == "NEEDS_REVIEW":
                groups[("warning", "NEEDS_REVIEW", tuple(sorted(r for r in (q.unit_reasons or []) if r in ("WEIGHT_ESTIMATED", "OUTLIER", "WEIGHT_MISMATCH"))))].append(ln)
            elif q.unit_status == "NOT_CONVERTIBLE":
                groups[("warning", "NOT_CONVERTIBLE", tuple(sorted(r for r in (q.unit_reasons or []) if r in REASON_TEXT)) or ("NOT_CONVERTIBLE",))].append(ln)
        for (sev, status, reasons), lns in groups.items():
            ref = any(r.startswith(("REFERENCE", "BASELINE")) for r in reasons)
            cat = "Commercial terms" if ref else "Quote completeness"
            text = "; ".join(REASON_TEXT.get(r, r.lower()) for r in reasons)
            head = {"UNRESOLVED": "Values withheld", "NEEDS_REVIEW": "Values need review", "NOT_CONVERTIBLE": "Not convertible"}[status]
            add(sev, cat, vid, f"{head} on {len(lns)} line(s): {text}", lines_=sorted(lns), concern=text,
                statement="See each line's source in the comparison", requirement="Every compared price must be verified, in a stated unit, ex-GST per box",
                confidence="per line (see provenance)", kind="cells", key=[sev, reasons], target=f"/comparison?vendor={vid}&exceptions=1")
        missing = sorted(lines[q.rfx_line_id].line_no for q in qq if q.unit_status == "MISSING")
        if missing and vid in responses:
            add("warning", "Quote completeness", vid, f"Not quoted: {len(missing)} of {len(lines)} lines", lines_=missing,
                concern="Missing lines are never filled; totals for this vendor cover quoted lines only",
                requirement="Quote every RFx line", statement="No price stated for these lines",
                kind="missing", key=missing, target=f"/vendors/{vid}?tab=items")
        alts = sorted(lines[q.rfx_line_id].line_no for q in qq if "ALTERNATE" in (q.flags or []))
        if alts:
            add("warning", "Specification deviations", vid, f"Alternate specification offered on {len(alts)} line(s)", lines_=alts,
                concern="Excluded from awards unless alternates are included", requirement="RFx construction (GSM/ply/flute/dims)",
                statement="Vendor restated a different construction", kind="alternate", key=alts, target=f"/comparison?vendor={vid}&exceptions=1")
        quoted = [q for q in qq if q.unit_status != "MISSING"]
        unknown_freight = [q for q in quoted if q.freight_basis == "UNKNOWN"]
        if quoted and len(unknown_freight) == len(quoted):
            add("warning", "Commercial terms", vid, "Freight not included or not stated: landed cost not comparable",
                concern="Compared on unit price as a lower bound; freight-dependent awards show a break-even",
                requirement="Delivered price, or freight stated separately", statement="Freight extra / ex-works / silent",
                kind="freight", key="unknown", target=f"/comparison?vendor={vid}")
        fx = [q for q in quoted if "FX" in (q.flags or [])]
        if fx:
            t = next((t for q in fx for t in (q.trace or []) if t.get("step") == "fx"), {})
            add("info", "Commercial terms", vid, f"Prices quoted in {t.get('currency', 'foreign currency')}, converted at {t.get('rate')} ({t.get('source')}, {t.get('as_of')})",
                concern="Invoiced in INR at the rate on invoice date: FX exposure applies", statement=f"{len(fx)} lines in {t.get('currency')}",
                requirement="Prices in INR", kind="fx", key="fx", target="/settings?section=normalisation")

    # c) vendors that have not responded
    for vid in vendors:
        if vid not in responses:
            add("warning", "Quote completeness", vid, "No response received", concern="Shown as Awaiting response; never treated as zero",
                kind="awaiting", key="awaiting", target=f"/vendors/{vid}")

    sev_rank = {"blocker": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: (sev_rank[f["severity"]], f["vendor_key"] or "", f["title"]))
    open_blockers = [f for f in findings if f["severity"] == "blocker" and f["review"]["state"] in OPEN_STATES]

    # vendor tracker
    results = defaultdict(list)
    for e in elig:
        q = qs[e.question_id]
        results[e.vendor_id].append(QResult(q.requirement_key, q.section, e.state, e.reason, LINE_FLAG.get(q.applicability)))
    tracker = []
    for vid, v in sorted(vendors.items(), key=lambda kv: vkey.get(kv[0], "")):
        r = responses.get(vid)
        qq = by_vendor.get(vid, [])
        quoted = sum(1 for q in qq if q.unit_status != "MISSING")
        subs = (r.submissions or []) if r else []
        last = max((inbox[sub["path"]].received_at for sub in subs if sub["path"] in inbox), default=None)
        vf = [f for f in findings if f["vendor_id"] == vid]
        state = ("Pending" if r is None else "Failed to read" if r.status == "failed" else "Processing" if r.status in ("received", "processing")
                 else "Needs clarification" if any(f["severity"] == "blocker" for f in vf) else "Received")
        sec = {k: (label(roll_up(results[vid], k.upper())[0]) if results.get(vid) else ("Not provided" if r else "Awaiting"))
               for k in ("quality", "commercial")}
        tracker.append({"vendor_id": vid, "key": vkey.get(vid), "name": v.name, "email": v.contact_email, "state": state,
                        "messages": len(subs), "quoted_lines": quoted, "lines": len(lines),
                        "coverage_pct": round(100 * quoted / len(lines)) if lines and r else None,
                        "quality": sec["quality"], "commercial": sec["commercial"],
                        "blockers": sum(1 for f in vf if f["severity"] == "blocker" and f["review"]["state"] in OPEN_STATES),
                        "exceptions": len(vf), "last_activity": last.isoformat() if last else None})

    responded = sum(1 for vid in vendors if vid in responses)
    stages = [
        {"key": "issued", "label": "RFx issued", "route": "/copilot?tab=draft",
         "state": "done" if ctx["status"] in ("sent",) else "current" if ctx["status"] in ("draft", "approved") else "todo",
         "detail": ctx["status"]},
        {"key": "responses", "label": "Responses received", "route": "/vendors",
         "state": "todo" if ctx["status"] != "sent" else ("done" if vendors and responded == len(vendors) else "current"),
         "detail": f"{responded} of {len(vendors)}"},
        {"key": "review", "label": "Compliance review", "route": "/review",
         "state": "todo" if not responded else ("done" if not open_blockers else "current"),
         "detail": f"{len(open_blockers)} open blocker(s)"},
        {"key": "comparison", "label": "Commercial comparison", "route": "/comparison",
         "state": "todo" if not quotes else ("done" if ps and ps.phase_b_status == "final" else "current"),
         "detail": (ps.phase_b_status if ps else "not started")},
        {"key": "award", "label": "Award recommendation", "route": "/award",
         "state": "done" if acked else ("current" if quotes else "todo"),
         "detail": "acknowledged" if acked else "not saved"},
    ]
    activity = [{"id": e.id, "at": e.at.isoformat(), "actor": e.actor, "action": e.action,
                 "text": _activity_text(e, vendors)} for e in events]
    return {
        "rfx": ctx,
        "metrics": {"vendors_invited": len(vendors), "vendors_responded": responded, "skus": len(lines),
                    "annual_demand": sum(l.annual_qty for l in lines.values()), "open_blockers": len(open_blockers),
                    "findings": len(findings)},
        "findings": findings, "vendors": tracker, "stages": stages, "activity": activity,
        "provisional": not (ps and ps.phase_b_status == "final"),
    }


def _activity_text(e: AuditEvent, vendors) -> str:
    t = e.target or {}
    v = vendors.get(t.get("vendor_id")).name if t.get("vendor_id") in vendors else None
    m = {"RFX_SENT": "RFx sent to vendors", "RFX_APPROVED": "RFx approved", "CONFORMANCE_CHECKED": "Conformance checked",
         "QUESTIONNAIRE_APPLIED": "Questionnaire and terms applied", "MAPPING_CONFIRMED_AND_IMPORTED": "Item master imported",
         "GAP_PATCH_APPLIED": "Open fields answered", "ELIGIBILITY_EVALUATED": f"Eligibility evaluated{' for ' + v if v else ''}",
         "RECOMPUTE": "Comparison recomputed", "RERUN_REQUESTED": f"Re-read requested{' for ' + v if v else ''}",
         "READINESS_ACK": "Award readiness acknowledged", "FINDING_REVIEWED": f"Finding reviewed: {(e.after or {}).get('state')}",
         "RESPONSE_UPLOADED": f"Response uploaded{' for ' + v if v else ''}", "SEEDED_FALLBACK_LOADED": "Seeded fallback RFx loaded",
         "CLARIFICATION_PACK_APPROVED": "Clarification pack approved to outbox", "MAPPING_PROPOSED": "Co-pilot proposed column mapping"}
    if e.action.startswith("RESOLUTION_"):
        return f"Value resolution: {e.action.removeprefix('RESOLUTION_').title()}{' (' + v + ')' if v else ''}"
    return m.get(e.action, e.action.replace("_", " ").capitalize())


@router.get("/{rfx_id}/overview")
def overview(rfx_id: int, request: Request):
    st = request.app.state
    return derive(st.session_factory, st.storage, rfx_id)


class ReviewBody(BaseModel):
    state: str
    comment: str | None = None
    actor: str = "buyer"


@router.post("/{rfx_id}/findings/{finding_id}/review")
def review_finding(rfx_id: int, finding_id: str, body: ReviewBody, request: Request):
    """Human review state of a finding; every change is audited with the previous state (spec §7)."""
    if body.state not in ("open", "confirmed", "rejected", "clarification_requested", "not_applicable"):
        raise HTTPException(422, "unknown review state")
    if body.state in ("rejected", "not_applicable") and not (body.comment or "").strip():
        raise HTTPException(422, "a reason is required to reject or mark not applicable")
    st = request.app.state
    known = {f["id"]: f for f in derive(st.session_factory, st.storage, rfx_id)["findings"]}
    if finding_id not in known:
        raise HTTPException(404, "no such finding")
    with st.session_factory.begin() as s:
        r = s.scalar(select(FindingReview).where(FindingReview.rfx_id == rfx_id, FindingReview.finding_id == finding_id))
        before = {"state": r.state, "comment": r.comment} if r else {"state": "open"}
        if r is None:
            r = FindingReview(rfx_id=rfx_id, finding_id=finding_id, state=body.state, actor=body.actor)
            s.add(r)
        r.state, r.comment, r.actor, r.at = body.state, body.comment, body.actor, datetime.now(timezone.utc)
        f = known[finding_id]
        s.add(AuditEvent(actor=body.actor, action="FINDING_REVIEWED",
                         target={"rfx_id": rfx_id, "finding_id": finding_id, "vendor_id": f["vendor_id"]},
                         before=before, after={"state": body.state, "title": f["title"]}, reason=body.comment))
    return {"finding_id": finding_id, "state": body.state}


@router.get("/{rfx_id}/findings/{finding_id}/history")
def finding_history(rfx_id: int, finding_id: str, request: Request):
    with request.app.state.session_factory() as s:
        return [{"at": e.at.isoformat(), "actor": e.actor, "before": e.before, "after": e.after, "reason": e.reason}
                for e in s.scalars(select(AuditEvent).where(AuditEvent.action == "FINDING_REVIEWED").order_by(AuditEvent.id))
                if (e.target or {}).get("finding_id") == finding_id and (e.target or {}).get("rfx_id") == rfx_id]


class MetaBody(BaseModel):
    code: str | None = None
    buyer: str | None = None
    buyer_name: str | None = None
    category: str | None = None
    plant: str | None = None
    currency: str | None = None
    actor: str = "buyer"


@router.put("/{rfx_id}/meta")
def set_meta(rfx_id: int, body: MetaBody, request: Request):
    with request.app.state.session_factory.begin() as s:
        rfx = s.get(Rfx, rfx_id)
        if rfx is None:
            raise HTTPException(404, "no such RFx")
        before = dict(rfx.meta or {})
        rfx.meta = {**before, **{k: v for k, v in body.model_dump(exclude={"actor"}).items() if v is not None}}
        s.add(AuditEvent(actor=body.actor, action="RFX_METADATA_CHANGED", target={"rfx_id": rfx_id}, before=before, after=rfx.meta))
    return rfx_context(rfx, request.app.state.storage)
