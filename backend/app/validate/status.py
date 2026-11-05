"""Canonical status model (PRD §6, DL-10/16) — the ONLY place that decides status and inclusion."""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import (
    ADVISORY_REASONS, ASSUMPTION_REASONS, BLOCKING_REASONS, NOT_CONVERTIBLE_REASONS, ValueStatus as S,
)

PRECEDENCE = [S.MISSING, S.NOT_CONVERTIBLE, S.UNRESOLVED, S.NEEDS_REVIEW, S.ASSUMED, S.EXTRACTED, S.VERIFIED]

# PRD §6.2 inclusion table as data: formal default / exploratory-on-request
INCLUSION = {
    S.VERIFIED: {"has_number": True, "formal": True, "exploratory": True},
    S.EXTRACTED: {"has_number": True, "formal": True, "exploratory": True},
    S.ASSUMED: {"has_number": True, "formal": True, "exploratory": True},
    S.NEEDS_REVIEW: {"has_number": True, "formal": False, "exploratory": False},  # opt-in only
    S.UNRESOLVED: {"has_number": False, "formal": False, "exploratory": False},
    S.NOT_CONVERTIBLE: {"has_number": False, "formal": False, "exploratory": False},
    S.MISSING: {"has_number": False, "formal": False, "exploratory": False},
}


class OverrideRequired(PermissionError):
    """Formal inclusion of NEEDS_REVIEW without an audited buyer override (DL-16)."""


def worst(statuses) -> S:
    return min(statuses, key=PRECEDENCE.index)


def status_from(reasons: list[str], *, quoted: bool = True, cap_extracted: bool = False,
                auto_verify_ok: bool = False) -> S:
    """Derive the Phase A status from reason codes (PRD §6.3). `cap_extracted` for image-sourced or
    plausibility-unchecked values; `auto_verify_ok` only when every §6.4 condition holds."""
    if not quoted:
        return S.MISSING
    rs = set(reasons)
    if rs & NOT_CONVERTIBLE_REASONS:
        return S.NOT_CONVERTIBLE
    if rs & BLOCKING_REASONS:
        return S.UNRESOLVED
    if rs & ADVISORY_REASONS:
        return S.NEEDS_REVIEW
    if rs & ASSUMPTION_REASONS:
        return S.ASSUMED
    if auto_verify_ok and not cap_extracted:
        return S.VERIFIED
    return S.EXTRACTED


@dataclass(frozen=True)
class Policy:
    context: str = "formal"  # formal / exploratory
    include_needs_review: bool = False


def includable(status: S, policy: Policy = Policy(), override_id: int | None = None) -> bool:
    row = INCLUSION[S(status)]
    if not row["has_number"]:
        return False
    if status == S.NEEDS_REVIEW:
        if not policy.include_needs_review:
            return False
        if policy.context == "formal" and override_id is None:
            raise OverrideRequired("formal award inclusion of NEEDS_REVIEW requires an audited buyer override")
        return True
    return row[policy.context]
