"""Slice API for the primary RFx flow (M6a). Errors from out-of-order steps map to 409."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.rfx import service as svc
from app.rfx.item_master import MappingNotConfirmed

router = APIRouter(prefix="/rfx")


def _deps(request: Request):
    st = request.app.state
    return st.session_factory, st.storage


def _gw(request: Request):
    return request.app.state.gateway_factory()


class StartBody(BaseModel):
    title: str = "Annual corrugated packaging RFx"
    sandbox: bool = False


class MappingBody(BaseModel):
    mapping: dict[str, str]


class TextBody(BaseModel):
    text: str


def _conflict(fn):
    try:
        return fn()
    except (svc.FlowError, MappingNotConfirmed) as e:
        raise HTTPException(409, str(e))


@router.post("/primary")
def start(body: StartBody, request: Request):
    sf, st = _deps(request)
    rfx_id, proposal = _conflict(lambda: svc.start_primary_rfx(sf, st, _gw(request), body.title, body.sandbox))
    return {"rfx_id": rfx_id, "mapping_proposal": proposal.model_dump()}


@router.post("/{rfx_id}/mapping/confirm")
def confirm(rfx_id: int, body: MappingBody, request: Request):
    sf, st = _deps(request)
    return _conflict(lambda: svc.confirm_mapping(sf, st, rfx_id, body.mapping))


@router.post("/{rfx_id}/gaps/propose")
def gaps_propose(rfx_id: int, body: TextBody, request: Request):
    sf, st = _deps(request)
    return svc.propose_gap_patch(_gw(request), sf, st, rfx_id, body.text).model_dump()


class PatchBody(BaseModel):
    patch: dict
    source_text: str


@router.post("/{rfx_id}/gaps/apply")
def gaps_apply(rfx_id: int, body: PatchBody, request: Request):
    sf, st = _deps(request)
    # a quote may come from the buyer's reply or the buyer's own policy documents (both were shown to the model)
    rejected = svc.apply_gap_patch(sf, rfx_id, svc.GapPatch.model_validate(body.patch),
                                   body.source_text + "\n" + svc.policy_text(st))
    return {"rejected": rejected, "remaining_gaps": svc.rfx_gaps(sf, rfx_id)}


@router.get("/{rfx_id}/form")
def form_download(rfx_id: int, request: Request):
    from fastapi.responses import PlainTextResponse
    sf, _ = _deps(request)
    return PlainTextResponse(_conflict(lambda: svc.form_text(sf, rfx_id)), headers={"Content-Disposition": f'attachment; filename="rfx-{rfx_id}-form.txt"'})


class FormBody(BaseModel):
    text: str


@router.post("/{rfx_id}/form/apply")
def form_apply(rfx_id: int, body: FormBody, request: Request):
    sf, _ = _deps(request)
    return _conflict(lambda: svc.apply_form(sf, rfx_id, body.text))


@router.post("/{rfx_id}/conformance")
def conformance(rfx_id: int, request: Request):
    sf, st = _deps(request)
    return svc.conformance(sf, rfx_id, json.loads(st.read_text("seed/canonical_rfx.json")))


@router.post("/{rfx_id}/approve")
def approve(rfx_id: int, request: Request):
    sf, _ = _deps(request)
    _conflict(lambda: svc.approve(sf, rfx_id))
    return {"status": "approved"}


@router.post("/{rfx_id}/send")
def send(rfx_id: int, request: Request):
    sf, st = _deps(request)
    return {"sent": _conflict(lambda: svc.send(sf, st, rfx_id))}


@router.post("/{rfx_id}/deliver-next")
def deliver_next(rfx_id: int, request: Request):
    sf, st = _deps(request)
    return {"delivered": _conflict(lambda: svc.deliver_next(sf, st, rfx_id))}


@router.post("/{rfx_id}/process")
def process(rfx_id: int, request: Request):
    from app.process.run import process_rfx
    sf, st = _deps(request)
    return process_rfx(sf, st, _gw(request), rfx_id)


@router.post("/{rfx_id}/responses/{vendor_id}/rerun")
def rerun(rfx_id: int, vendor_id: int, request: Request):
    """EXT-11: basic re-run; human resolutions carry forward when the raw fingerprint is unchanged."""
    from app.process.run import rerun_vendor
    sf, st = _deps(request)
    try:
        return rerun_vendor(sf, st, _gw(request), rfx_id, vendor_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


# --- questionnaire (M6b) -----------------------------------------------------------------------
@router.post("/{rfx_id}/questionnaire/propose")
def questionnaire_propose(rfx_id: int, request: Request):
    from app.rfx.questionnaire import brief_units, propose_questionnaire, validate
    _, st = _deps(request)
    draft = propose_questionnaire(_gw(request), st)
    units, _ = brief_units(st)
    return {"draft": draft.model_dump(), "validation": validate(draft, units)}


class DraftBody(BaseModel):
    draft: dict
    actor: str = "buyer"


@router.post("/{rfx_id}/questionnaire/apply")
def questionnaire_apply(rfx_id: int, body: DraftBody, request: Request):
    from app.rfx.questionnaire import QuestionnaireDraft, apply_questionnaire
    sf, st = _deps(request)
    try:
        out = apply_questionnaire(sf, st, rfx_id, QuestionnaireDraft.model_validate(body.draft), body.actor)
    except ValueError as e:
        raise HTTPException(409, str(e))
    if out["rejected"]:
        raise HTTPException(422, {"message": "questionnaire not applied: some questions failed validation",
                                  "rejected": out["rejected"]})
    return out


@router.get("/{rfx_id}/vendors/{vendor_id}/eligibility")
def vendor_eligibility(rfx_id: int, vendor_id: int, request: Request):
    """Vendor panel (DL-14, DL-29): Quality and Commercial reported separately; line-scoped questions
    are shown per flagged line and never in the vendor roll-up; Unverified is never 'Failed'."""
    from sqlalchemy import select
    from app.db.models import EligibilityResult, Question, RfxLine
    from app.eligibility.rules import LINE_FLAG, QResult, label, roll_up
    sf, _ = _deps(request)
    with sf() as s:
        qs = {q.id: q for q in s.scalars(select(Question).where(Question.rfx_id == rfx_id))}
        rows = list(s.scalars(select(EligibilityResult).where(EligibilityResult.vendor_id == vendor_id,
                                                              EligibilityResult.question_id.in_(list(qs)))))
        flagged = {f: [l.line_no for l in s.scalars(select(RfxLine).where(RfxLine.rfx_id == rfx_id)) if getattr(l, f)]
                   for f in ("food_contact", "requires_fsc")}
    if not qs:
        return {"configured": False, "note": "no questionnaire on this RFx"}
    results = [QResult(qs[r.question_id].requirement_key, qs[r.question_id].section, r.state, r.reason,
                       LINE_FLAG.get(qs[r.question_id].applicability)) for r in rows]
    by_key = {qs[r.question_id].requirement_key: r for r in rows}
    sections = {}
    for sec in ("QUALITY", "COMMERCIAL"):
        state, why = roll_up(results, sec)
        sections[sec.lower()] = {"state": state if rows else "UNVERIFIED", "label": label(state if rows else "UNVERIFIED"),
                                 "questions": [{"no": qs[r.question_id].no, "key": res.key, "state": res.state,
                                                "label": label(res.state), "reason": res.reason,
                                                "provenance": by_key[res.key].provenance}
                                               for res, r in zip(results, rows) if res.section == sec and res.line_flag is None]}
    line_level = [{"key": res.key, "flag": res.line_flag, "lines": flagged.get(res.line_flag, []), "state": res.state,
                   "label": label(res.state), "reason": res.reason, "provenance": by_key[res.key].provenance}
                  for res in results if res.line_flag]
    return {"configured": True, "vendor_id": vendor_id, **sections, "line_level": line_level,
            "note": "line-level requirements gate only that vendor's cells on flagged lines (DL-29)"}


@router.post("/seeded-fallback")
def seeded(body: StartBody, request: Request):
    sf, st = _deps(request)
    rid = svc.seeded_fallback(sf, st, None if body.title == StartBody().title else body.title)
    return svc.header(sf, rid)


@router.get("/{rfx_id}")
def rfx_header(rfx_id: int, request: Request):
    sf, _ = _deps(request)
    return _conflict(lambda: svc.header(sf, rfx_id))


@router.get("")
def list_rfx(request: Request):
    from sqlalchemy import select
    from app.db.models import Rfx
    sf, _ = _deps(request)
    from app.api.overview import rfx_context
    _, st = _deps(request)
    with sf() as s:
        return [rfx_context(r, st) for r in s.scalars(select(Rfx).order_by(Rfx.id))]


class UploadBody(BaseModel):
    vendor_name: str
    vendor_email: str
    filename: str
    content_b64: str
    actor: str = "buyer"


@router.post("/{rfx_id}/upload")
def upload(rfx_id: int, body: UploadBody, request: Request):
    import base64
    sf, st = _deps(request)
    try:
        data = base64.b64decode(body.content_b64, validate=True)
    except ValueError:
        raise HTTPException(422, "content_b64 is not valid base64")
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "file too large")
    return _conflict(lambda: svc.upload_response(sf, st, rfx_id, body.vendor_name, body.vendor_email, body.filename, data, body.actor))
