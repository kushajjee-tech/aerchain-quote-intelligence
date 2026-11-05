"""Co-pilot questionnaire drafting (RFX-9/10, M6b): the model proposes questions from the brief-pack
requirement documents; code validates every question against its citation before the buyer applies it.
Nothing the model writes is applied unless its source quote verifies and its key and threshold appear in
that quote. Applying is a buyer action and is audited."""
from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.db.models import AuditEvent, Question, Rfx
from app.ingest.evidence import render_units
from app.ingest.parsers.docx_ import parse_docx
from app.ingest.schemas import DocTypeLit, Evidence
from app.ingest.verify import check_evidence, norm
from app.llm.prompts import QUESTIONNAIRE_SYSTEM, QUESTIONNAIRE_V1, questionnaire_user

BRIEF_PACK = "seed/brief_pack"


class DraftQuestion(BaseModel):
    no: str
    requirement_key: str
    section: Literal["QUALITY", "COMMERCIAL"]
    applicability: Literal["ALL", "LINES_WITH_FLAG(food_contact)", "LINES_WITH_FLAG(requires_fsc)"]
    text: str = Field(description="The question as the supplier will read it")
    answer_type: Literal["yes_no", "number", "text", "document"]
    mandatory: bool
    pass_op: Literal["==", ">=", "<=", "<", ">", "present"]
    pass_value: Optional[str] = None
    evidence_required: bool
    evidence_doc_type: Optional[DocTypeLit] = None
    source: Evidence


class DraftTerm(BaseModel):
    type: Literal["PAYMENT", "LEAD_TIME", "GST_REGISTRATION", "VALIDITY", "FREIGHT", "PRICING_BASIS", "OTHER"]
    text: str = Field(description="The term as it will appear in the RFx")
    source: Evidence


class QuestionnaireDraft(BaseModel):
    questions: list[DraftQuestion]
    terms: list[DraftTerm] = Field(default_factory=list)


def brief_units(storage) -> tuple[dict, str]:
    docs = [parse_docx(f"B{i}", f.split("/")[-1], storage.read_bytes(f))
            for i, f in enumerate(sorted(f for f in storage.iter_files(BRIEF_PACK) if f.endswith(".docx")), start=1)]
    docs = [d for d in docs if d.parse_status == "parsed"]
    return {u.id: u for d in docs for u in d.units}, "\n\n".join(render_units(d) for d in docs)


SECTION_ORDER = {"QUALITY": 0, "COMMERCIAL": 1}


def number_questions(draft: QuestionnaireDraft, units: dict) -> QuestionnaireDraft:
    """Question numbers are assigned by code, never by the model or by file-name order: Quality first, then
    Commercial (RFX-4 sections), each in the order the buyer's documents list the requirements."""
    pos = {uid: i for i, uid in enumerate(units)}
    order = sorted(draft.questions, key=lambda q: (SECTION_ORDER.get(q.section, 9),
                                                   min((pos.get(u, 10**6) for u in q.source.unit_ids), default=10**6),
                                                   q.requirement_key))
    return draft.model_copy(update={"questions": [q.model_copy(update={"no": f"Q{i}"}) for i, q in enumerate(order, start=1)]})


def propose_questionnaire(gw, storage) -> QuestionnaireDraft:
    units, rendered = brief_units(storage)
    return number_questions(_propose(gw, rendered), units)


def _propose(gw, rendered: str) -> QuestionnaireDraft:
    return gw.structured("copilot", QuestionnaireDraft, [{"role": "user", "content": questionnaire_user(rendered)}],
                         system=QUESTIONNAIRE_SYSTEM, prompt_version=QUESTIONNAIRE_V1, max_tokens=8000)


def validate(draft: QuestionnaireDraft, units: dict) -> list[dict]:
    """One verdict per question: {no, key, ok, problems}. Deterministic."""
    seen_keys, seen_nos, out = set(), set(), []
    for q in draft.questions:
        problems = list(check_evidence(q.source, units).reasons)
        cited = norm(" ".join(units[u].text for u in q.source.unit_ids if u in units))
        if norm(q.requirement_key) not in cited:
            problems.append("requirement key not in the cited source")
        if q.pass_op in (">=", "<=", "<", ">"):
            if q.pass_value is None or not re.fullmatch(r"\d+(\.\d+)?", q.pass_value.strip()):
                problems.append("numeric pass rule needs a number")
            elif not re.search(rf"(?<![\d.]){re.escape(q.pass_value.strip())}(?![\d.])", cited):
                problems.append("threshold not stated in the cited source")
        if q.pass_op == "==" and (q.pass_value or "").strip().lower() not in ("yes", "no"):
            problems.append("equality rule must be yes or no")
        if q.evidence_required != (q.evidence_doc_type is not None):
            problems.append("evidence_required and evidence_doc_type disagree")
        if q.requirement_key in seen_keys or q.no in seen_nos:
            problems.append("duplicate question number or key")
        seen_keys.add(q.requirement_key)
        seen_nos.add(q.no)
        out.append({"no": q.no, "key": q.requirement_key, "ok": not problems, "problems": problems})
    for t in draft.terms:  # terms are applied only with a verified policy citation
        problems = list(check_evidence(t.source, units).reasons)
        out.append({"no": None, "key": f"term:{t.type}", "ok": not problems, "problems": problems})
    return out


def _rule(q: DraftQuestion) -> dict:
    if q.pass_op == "present":
        return {"op": "present"}
    v = q.pass_value.strip()
    return {"op": q.pass_op, "value": (float(v) if "." in v else int(v)) if re.fullmatch(r"\d+(\.\d+)?", v) else v.lower()}


def apply_questionnaire(sf, storage, rfx_id: int, draft: QuestionnaireDraft, actor: str = "buyer") -> dict:
    units, _ = brief_units(storage)
    draft = number_questions(draft, units)
    verdicts = validate(draft, units)
    rejected = [v for v in verdicts if not v["ok"]]
    if rejected:  # all-or-nothing: an invalid patch is never partially applied
        return {"applied": 0, "rejected": rejected}
    with sf.begin() as s:
        rfx = s.get(Rfx, rfx_id)
        if rfx is None or rfx.status not in ("draft",):
            raise ValueError("the questionnaire can only be changed while the RFx is a draft")
        before = [q.requirement_key for q in s.scalars(select(Question).where(Question.rfx_id == rfx_id))]
        s.execute(delete(Question).where(Question.rfx_id == rfx_id))
        for q in draft.questions:
            s.add(Question(rfx_id=rfx_id, no=q.no, section=q.section, requirement_key=q.requirement_key,
                           applicability=q.applicability, text=q.text, answer_type=q.answer_type, mandatory=q.mandatory,
                           pass_rule=_rule(q), evidence_required=q.evidence_required, evidence_doc_type=q.evidence_doc_type))
        rfx.terms = [{"type": t.type, "text": t.text, "source": t.source.model_dump()} for t in draft.terms]
        rfx.conformance = None  # any change needs a new conformance check (RFX-10)
        s.add(AuditEvent(actor=actor, action="QUESTIONNAIRE_APPLIED", target={"rfx_id": rfx_id}, before={"keys": before},
                         after={"questions": [{"no": q.no, "key": q.requirement_key,
                                               "source": q.source.model_dump()} for q in draft.questions],
                                "terms": [t.type for t in draft.terms]}))
    return {"applied": len(draft.questions), "rejected": []}


Q_FIELDS = ["no", "section", "applicability", "answer_type", "mandatory", "pass_rule", "evidence_required", "evidence_doc_type"]


def _norm_rule(r):
    if not r:
        return r
    r = dict(r)
    if "value" in r and isinstance(r["value"], (int, float)):
        r["value"] = float(r["value"])
    elif "value" in r:
        r["value"] = str(r["value"]).lower()
    return r


def questionnaire_differences(s, rfx_id: int, canonical: dict) -> list[dict]:
    have = {q.requirement_key: {"no": q.no, "section": q.section, "applicability": q.applicability,
                                "answer_type": q.answer_type, "mandatory": q.mandatory, "pass_rule": _norm_rule(q.pass_rule),
                                "evidence_required": q.evidence_required, "evidence_doc_type": q.evidence_doc_type}
            for q in s.scalars(select(Question).where(Question.rfx_id == rfx_id))}
    canon = {q["requirement_key"]: {**{f: q.get(f) for f in Q_FIELDS}, "pass_rule": _norm_rule(q.get("pass_rule"))}
             for q in canonical.get("questionnaire", [])}
    diffs = [{"question": k, "difference": "missing from draft"} for k in sorted(set(canon) - set(have))]
    diffs += [{"question": k, "difference": "not in canonical spec"} for k in sorted(set(have) - set(canon))]
    for k in sorted(set(have) & set(canon)):
        diffs += [{"question": k, "field": f, "draft": have[k][f], "canonical": canon[k][f]}
                  for f in Q_FIELDS if have[k][f] != canon[k][f]]
    return diffs
