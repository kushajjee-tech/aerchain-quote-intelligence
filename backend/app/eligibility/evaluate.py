"""Vendor eligibility from extracted answers and document facts (ELG-1…6; DL-3, DL-14, DL-24, DL-29).

The model only reads; this module decides. A fact is used only if its evidence verifies and every
stated value appears in the cited quote. Validity statements are resolved deterministically:
an explicit date, "N months/years from <date>", or a no-expiry clause ("until superseded").
Anything else is unreadable → the question is Unverified, never Failed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from app.eligibility.rules import AnswerIn, DocFact, QResult, evaluate_question
from app.ingest.schemas import Answer, AttachedDocument
from app.ingest.verify import check_evidence, norm

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
NO_EXPIRY = re.compile(r"supersed|until (revoked|withdrawn)|no expiry|perpetual", re.I)


def parse_date(text: str | None) -> date | None:
    if not text:
        return None
    t = text.strip()
    if m := re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", t):
        y, mo, d = map(int, m.groups())
    elif m := re.search(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b", t):  # Indian convention: day first
        d, mo, y = map(int, m.groups())
    elif m := re.search(r"\b(\d{1,2})\s+([A-Za-z]{3})[a-z]*\.?,?\s+(\d{4})\b", t):
        d, mo, y = int(m.group(1)), MONTHS.get(m.group(2).lower()), int(m.group(3))
    elif m := re.search(r"\b([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b", t):
        mo, d, y = MONTHS.get(m.group(1).lower()), int(m.group(2)), int(m.group(3))
    else:
        return None
    try:
        return date(y, mo, d) if mo else None
    except ValueError:
        return None


def _add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(y, m, day)
        except ValueError:
            continue
    raise ValueError(d)


def resolve_expiry(expiry_as_stated: str | None, issue_as_stated: str | None) -> tuple[str, str | None]:
    """Returns (kind, iso_date): kind ∈ DATE / NO_EXPIRY / NONE_STATED / UNREADABLE."""
    if not expiry_as_stated:
        return "NONE_STATED", None
    if NO_EXPIRY.search(expiry_as_stated):
        return "NO_EXPIRY", None
    if m := re.search(r"(\d+)\s*(month|year)s?\s+from", expiry_as_stated, re.I):
        base = parse_date(issue_as_stated)
        if base is None:
            return "UNREADABLE", None
        n = int(m.group(1)) * (12 if m.group(2).lower() == "year" else 1)
        return "DATE", _add_months(base, n).isoformat()
    d = parse_date(expiry_as_stated)
    return ("DATE", d.isoformat()) if d else ("UNREADABLE", None)


@dataclass
class VerifiedFact:
    doc: AttachedDocument
    filename: str | None
    expiry_kind: str
    expiry_date: str | None
    readable: bool
    reasons: list[str]

    def as_docfact(self) -> DocFact:
        return DocFact(self.doc.doc_type, self.doc.entity_name, self.expiry_date, self.readable)


def verify_fact(doc: AttachedDocument, units: dict, filenames: dict[str, str]) -> VerifiedFact:
    ev = check_evidence(doc.evidence, units)
    reasons = list(ev.reasons)
    cited = norm(" ".join(units[u].text for u in doc.evidence.unit_ids if u in units))
    for f in ("entity_name", "reference_no", "issue_date_as_stated", "expiry_as_stated"):
        v = getattr(doc, f)
        if v and norm(v) not in cited:
            reasons.append(f"VALUE_NOT_IN_EVIDENCE:{f}")
    kind, iso = resolve_expiry(doc.expiry_as_stated, doc.issue_date_as_stated)
    return VerifiedFact(doc, filenames.get(doc.document_ref), kind, iso,
                        readable=not reasons and kind != "UNREADABLE", reasons=reasons + ([f"EXPIRY_{kind}"] if kind == "UNREADABLE" else []))


def evaluate_vendor(questions: list[dict], answers: list[tuple[Answer, list[str]]], facts: list[VerifiedFact],
                    vendor_name: str, quoted_flags: set[str], on: date) -> list[tuple[dict, QResult, dict]]:
    """questions: dicts with no/requirement_key/section/applicability/pass_rule/evidence_*.
    answers: (answer, verification reasons). Returns (question, result, provenance) per question."""
    by_no: dict[str, tuple[Answer, list[str]]] = {}
    for a, reasons in answers:
        by_no.setdefault(a.question_no.strip().upper(), (a, reasons))
    out = []
    for q in questions:
        hit = by_no.get(str(q["no"]).upper())
        a_in, prov = None, {"answer": None, "documents": []}
        if hit:
            a, reasons = hit
            named = {norm(x) for x in a.attachment_refs}
            docs = [f for f in facts if f.filename and norm(f.filename) in named] or facts  # same-response evidence pool
            a_in = AnswerIn(a.answer_value, [f.as_docfact() for f in docs], extracted_confidently=not reasons)
            prov = {"answer": {"value": a.answer_value, "text": a.answer_text, "evidence": a.evidence.model_dump(),
                               "verification": reasons},
                    "documents": [{"filename": f.filename, "doc_type": f.doc.doc_type, "entity_name": f.doc.entity_name,
                                   "expiry": f.expiry_date, "expiry_kind": f.expiry_kind, "readable": f.readable,
                                   "evidence": f.doc.evidence.model_dump()} for f in docs
                                  if f.doc.doc_type == q.get("evidence_doc_type")]}
        out.append((q, evaluate_question(q, a_in, vendor_name, quoted_flags, on), prov))
    return out
