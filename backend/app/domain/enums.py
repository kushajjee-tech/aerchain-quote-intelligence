"""Canonical vocabularies (PRD §6, §7). Single canonical source for statuses and reason codes."""
from __future__ import annotations

from enum import StrEnum


class ValueStatus(StrEnum):
    """PRD §6.2 canonical value statuses (DL-10). Order = precedence, worst first."""

    MISSING = "MISSING"
    NOT_CONVERTIBLE = "NOT_CONVERTIBLE"
    UNRESOLVED = "UNRESOLVED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    ASSUMED = "ASSUMED"
    EXTRACTED = "EXTRACTED"
    VERIFIED = "VERIFIED"


STATUS_PRECEDENCE: tuple[ValueStatus, ...] = tuple(ValueStatus)


class EligibilityState(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNVERIFIED = "UNVERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"  # question-level applicability only (DL-24/29)


class QuestionSection(StrEnum):
    QUALITY = "QUALITY"
    COMMERCIAL = "COMMERCIAL"


class QuestionApplicability(StrEnum):
    ALL = "ALL"
    FOOD_CONTACT_LINES = "LINES_WITH_FLAG(food_contact)"
    REQUIRES_FSC_LINES = "LINES_WITH_FLAG(requires_fsc)"


class ItemType(StrEnum):
    RSC = "RSC"
    DIE_CUT = "DIE_CUT"
    PAD = "PAD"
    PARTITION = "PARTITION"


class UnitClass(StrEnum):
    PER_BOX = "PER_BOX"
    PER_100 = "PER_100"
    PER_1000 = "PER_1000"
    PER_DOZEN = "PER_DOZEN"
    PER_KG = "PER_KG"
    PER_SET = "PER_SET"
    LUMP_SUM = "LUMP_SUM"
    UNKNOWN = "UNKNOWN"


class UnitSource(StrEnum):
    STATED = "STATED"
    INHERITED_FROM_CONTEXT = "INHERITED_FROM_CONTEXT"
    NONE = "NONE"


class FreightBasis(StrEnum):
    INCLUDED = "INCLUDED"
    STATED = "STATED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class WeightSource(StrEnum):
    SKU_REFERENCE = "SKU_REFERENCE"
    VENDOR_STATED = "VENDOR_STATED"
    ESTIMATED_CONSTANTS = "ESTIMATED_CONSTANTS"


class GstStatement(StrEnum):
    SILENT = "SILENT"
    STATED = "STATED"
    AMBIGUOUS = "AMBIGUOUS"


class RfxOrigin(StrEnum):
    COPILOT_LIVE = "COPILOT_LIVE"
    SEEDED_FALLBACK = "SEEDED_FALLBACK"
    SANDBOX = "SANDBOX"


class InvitationStatus(StrEnum):
    AWAITING_RESPONSE = "AWAITING_RESPONSE"
    RESPONDED = "RESPONDED"


class ResponseStatus(StrEnum):
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class SubmissionKind(StrEnum):
    QUOTE = "QUOTE"
    QUESTIONNAIRE = "QUESTIONNAIRE"
    OTHER = "OTHER"


class ExtractionPath(StrEnum):
    TEXT = "TEXT"
    OCR = "OCR"
    VISION = "VISION"


class ReasonSeverity(StrEnum):
    BLOCKING = "blocking"
    ADVISORY = "advisory"


# PRD §6.2 / §7 reason codes. Blocking -> UNRESOLVED; advisory -> NEEDS_REVIEW.
BLOCKING_REASONS = frozenset({
    "UNIT_UNKNOWN", "UNIT_SUSPECT", "READ_DISAGREEMENT", "READ_SINGLE_SOURCE",
    "EVIDENCE_NOT_FOUND", "PRICE_CONFLICT", "MATCH_LOW", "MATCH_CONFLICT", "GST_UNCLEAR",
    "SLAB_AMBIGUOUS", "BASELINE_SPEC_CHANGED", "BASELINE_NOT_FOR_VENDOR", "REFERENCE_UNRESOLVED",
    "REFERENCE_AMBIGUOUS", "LOW_OCR_CONFIDENCE", "FX_RATE_MISSING",
})
ADVISORY_REASONS = frozenset({"OUTLIER", "ARITHMETIC_MISMATCH", "WEIGHT_MISMATCH", "WEIGHT_ESTIMATED", "VALUE_CHANGED_AFTER_REVIEW"})
NOT_CONVERTIBLE_REASONS = frozenset({
    "MISSING_CONSTRUCTION_INPUT", "ITEM_TYPE_NOT_WEIGHT_COMPUTABLE", "FREIGHT_UNKNOWN",
})
ASSUMPTION_REASONS = frozenset({
    "UNIT_INHERITED", "METHOD_CONSTANTS", "FX_RATE", "BASELINE_REFERENCE", "FREIGHT_ESTIMATE",
    "GST_PER_RFX_BASIS", "REFERENCE_WEIGHT",
})
