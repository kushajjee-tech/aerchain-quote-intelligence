"""Eligibility (PRD §5.7; DL-3, DL-14, DL-24, DL-29). Deterministic: the AI extracts answers and
document facts; these rules decide. Line-scoped questions never enter vendor roll-ups; they gate
cells on flagged lines only. Unverified is never reported as Fail."""
from __future__ import annotations

import re

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

PASS, FAIL, UNVERIFIED, NA = "PASS", "FAIL", "UNVERIFIED", "NOT_APPLICABLE"
LINE_FLAG = {"LINES_WITH_FLAG(food_contact)": "food_contact", "LINES_WITH_FLAG(requires_fsc)": "requires_fsc"}


@dataclass
class DocFact:
    doc_type: str | None
    entity_name: str | None = None
    expiry_date: str | None = None  # ISO date
    readable: bool = True


@dataclass
class AnswerIn:
    answer_value: str | None
    attachments: list[DocFact] = field(default_factory=list)
    extracted_confidently: bool = True


@dataclass
class QResult:
    key: str
    section: str
    state: str
    reason: str
    line_flag: str | None = None


def _norm_entity(s: str | None) -> str:
    return " ".join((s or "").lower().replace(".", "").replace(",", "").split())


YES = re.compile(r"^(yes|y|ok|okay|accepted|agreed|confirmed|sure)\b")
NO = re.compile(r"^(no|n|not\b|cannot|can't|unable)\b")


def _yes_no(v: str) -> str | None:
    if YES.match(v):
        return "yes"
    if NO.match(v):
        return "no"
    return None


def _meets(rule: dict | None, value: str | None) -> bool | None:
    """True/False if the answer can be judged against the rule; None if it can't."""
    if rule is None:
        return True
    if value in (None, ""):
        return None
    op = rule.get("op")
    if op == "present":
        return True
    v = str(value).strip().lower()
    if op == "==":
        target = str(rule["value"]).lower()
        if target in ("yes", "no"):
            said = _yes_no(v)
            return None if said is None else said == target  # unclear answers are Unverified, never Failed
        return v == target
    try:
        num, target = Decimal(v.replace(",", "").split()[0]), Decimal(str(rule["value"]))
    except (InvalidOperation, IndexError):
        return None
    return {"<=": num <= target, ">=": num >= target, "<": num < target, ">": num > target}.get(op)


def evaluate_question(q: dict, a: AnswerIn | None, vendor_name: str, quoted_flags: set[str], on: date) -> QResult:
    key, section = q.get("requirement_key") or q.get("no"), q["section"]
    flag = LINE_FLAG.get(q.get("applicability", "ALL"))
    if flag and flag not in quoted_flags:
        return QResult(key, section, NA, f"applies only to {flag.replace('_', '-')} lines; this vendor quotes none", flag)
    if a is None or a.answer_value in (None, "") or not a.extracted_confidently:
        return QResult(key, section, UNVERIFIED, "unanswered or not readable", flag)
    meets = _meets(q.get("pass_rule"), a.answer_value)
    if meets is False:
        return QResult(key, section, FAIL, f"answer '{a.answer_value}' does not meet the requirement", flag)
    if meets is None:
        return QResult(key, section, UNVERIFIED, f"answer '{a.answer_value}' could not be judged", flag)
    if q.get("evidence_required"):
        docs = [d for d in a.attachments if d.doc_type == q.get("evidence_doc_type")]
        if not docs:
            return QResult(key, section, UNVERIFIED, "claimed, but the required document is not attached", flag)
        d = docs[0]
        if not d.readable:
            return QResult(key, section, UNVERIFIED, "required document could not be read", flag)
        if d.expiry_date and date.fromisoformat(d.expiry_date) < on:
            return QResult(key, section, UNVERIFIED, f"document expired on {d.expiry_date}", flag)
        if d.entity_name and _norm_entity(d.entity_name) != _norm_entity(vendor_name):
            return QResult(key, section, UNVERIFIED, f"document is in another entity's name ({d.entity_name})", flag)
    return QResult(key, section, PASS, "meets the requirement" + (" with valid evidence" if q.get("evidence_required") else ""), flag)


def roll_up(results: list[QResult], section: str | None) -> tuple[str, list[QResult]]:
    """Vendor-level state over ALL-scope mandatory questions of a section (None = all_mandatory)."""
    scoped = [r for r in results if r.line_flag is None and (section is None or r.section == section)]
    if any(r.state == FAIL for r in scoped):
        return FAIL, [r for r in scoped if r.state == FAIL]
    if any(r.state == UNVERIFIED for r in scoped):
        return UNVERIFIED, [r for r in scoped if r.state == UNVERIFIED]
    return PASS, []


def line_gate(results: list[QResult], flag: str, mode: str = "strict") -> bool:
    """May this vendor's cells on lines with `flag` be candidates? (DL-29)"""
    states = [r.state for r in results if r.line_flag == flag]
    if not states or NA in states:
        return True
    allowed = {PASS} if mode == "strict" else {PASS, UNVERIFIED}
    return all(s in allowed for s in states)


def label(state: str) -> str:
    """The only eligibility wording (ELG-6): 'Failed' appears for FAIL only."""
    return {PASS: "Passed", FAIL: "Failed", UNVERIFIED: "Unverified", NA: "Not applicable"}[state]
