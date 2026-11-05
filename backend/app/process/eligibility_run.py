"""Persist eligibility per vendor after extraction (ELG-1…6). Deterministic rules over verified facts;
re-evaluation replaces the vendor's rows for this RFx (derived data); every result keeps provenance."""
from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select

from app.db.models import AuditEvent, DocumentFact, EligibilityResult, Question
from app.eligibility.evaluate import evaluate_vendor, verify_fact
from app.ingest.extract import TextExtractionResult


def question_dicts(s, rfx_id: int) -> list[dict]:
    return [{"id": q.id, "no": q.no, "requirement_key": q.requirement_key, "section": q.section,
             "applicability": q.applicability, "text": q.text, "answer_type": q.answer_type, "mandatory": q.mandatory,
             "pass_rule": q.pass_rule, "evidence_required": q.evidence_required, "evidence_doc_type": q.evidence_doc_type}
            for q in s.scalars(select(Question).where(Question.rfx_id == rfx_id).order_by(Question.id))]


def evaluate_and_store(sf, rfx_id: int, vendor_id: int, vendor_name: str, results: list[TextExtractionResult],
                       quoted_flags: set[str], on: date | None = None) -> list[dict]:
    on = on or date.today()
    answers, facts = [], []
    for r in results:
        answers += list(zip(r.extraction.questionnaire_answers, r.answer_reasons))
        facts += [verify_fact(d, r.units, r.filenames) for d in r.extraction.attached_documents]
    with sf.begin() as s:
        qs = question_dicts(s, rfx_id)
        if not qs:
            return []
        evaluated = evaluate_vendor(qs, answers, facts, vendor_name, quoted_flags, on)
        s.execute(delete(DocumentFact).where(DocumentFact.rfx_id == rfx_id, DocumentFact.vendor_id == vendor_id))
        s.execute(delete(EligibilityResult).where(EligibilityResult.vendor_id == vendor_id,
                                                  EligibilityResult.question_id.in_([q["id"] for q in qs])))
        for f in facts:
            s.add(DocumentFact(vendor_id=vendor_id, rfx_id=rfx_id, filename=f.filename, doc_type=f.doc.doc_type,
                               standard=f.doc.standard, certificate_number=f.doc.reference_no, entity_name=f.doc.entity_name,
                               issue_date=f.doc.issue_date_as_stated, expiry_date=f.expiry_date,
                               fact_status="EXTRACTED" if f.readable else "UNREADABLE",
                               evidence=[f.doc.evidence.model_dump(), {"verification": f.reasons, "expiry_kind": f.expiry_kind}]))
        out = []
        for q, res, prov in evaluated:
            s.add(EligibilityResult(vendor_id=vendor_id, question_id=q["id"], state=res.state, reason=res.reason,
                                    evidence=[prov.get("answer") or {}], provenance={**prov, "evaluated_on": on.isoformat()}))
            out.append({"no": q["no"], "key": q["requirement_key"], "section": q["section"], "state": res.state, "reason": res.reason})
        s.add(AuditEvent(actor="system", action="ELIGIBILITY_EVALUATED", target={"rfx_id": rfx_id, "vendor_id": vendor_id},
                         after={"results": out}))
        return out
