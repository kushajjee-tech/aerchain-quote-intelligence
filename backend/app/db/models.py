"""SQLAlchemy models for the PRD §7 logical data model.

Money and other exact quantities are stored as Decimal text (architecture §5.4); complex
structures are JSON columns. Append-only tables are protected by SQLite triggers (see session.py).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class _Id:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


# --- RFx ---------------------------------------------------------------------------------
class CanonicalRfxSpec(Base):
    __tablename__ = "canonical_rfx_spec"
    version: Mapped[str] = mapped_column(String, primary_key=True)
    content_hash: Mapped[str] = mapped_column(String)
    spec: Mapped[dict] = mapped_column(JSON)


class Rfx(_Id, Base):
    __tablename__ = "rfx"
    title: Mapped[str] = mapped_column(String)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)  # FN-02: what is bought, drafted with the buyer
    kind: Mapped[str] = mapped_column(String)  # primary / sandbox
    origin: Mapped[str] = mapped_column(String)  # RfxOrigin
    status: Mapped[str] = mapped_column(String, default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    response_basis: Mapped[dict] = mapped_column(JSON, default=dict)
    delivery_location: Mapped[str | None] = mapped_column(String, nullable=True)
    canonical_spec_version: Mapped[str | None] = mapped_column(String, nullable=True)
    conformance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    copilot_conversation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    terms: Mapped[list] = mapped_column(JSON, default=list)  # [{type, text, source}] cited to the policy (RFX-9)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)  # code, buyer organisation, category, plant, currency


class RfxLine(_Id, Base):
    __tablename__ = "rfx_line"
    rfx_id: Mapped[int] = mapped_column(ForeignKey("rfx.id"))
    line_no: Mapped[int] = mapped_column(Integer)
    sku_code: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    item_type: Mapped[str] = mapped_column(String)
    dims_mm: Mapped[dict] = mapped_column(JSON)
    blank_size_mm: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ply: Mapped[int] = mapped_column(Integer)
    flute_profile: Mapped[str] = mapped_column(String)
    layers: Mapped[list] = mapped_column(JSON)
    printing: Mapped[dict] = mapped_column(JSON, default=dict)
    annual_qty: Mapped[int] = mapped_column(Integer)
    reference_unit_weight_g: Mapped[str | None] = mapped_column(String, nullable=True)
    reference_weight_source: Mapped[str | None] = mapped_column(String, nullable=True)
    food_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_fsc: Mapped[bool] = mapped_column(Boolean, default=False)
    source_evidence: Mapped[list] = mapped_column(JSON, default=list)
    __table_args__ = (UniqueConstraint("rfx_id", "line_no"),)


class Question(_Id, Base):
    __tablename__ = "question"
    rfx_id: Mapped[int] = mapped_column(ForeignKey("rfx.id"))
    no: Mapped[str] = mapped_column(String, default="")
    section: Mapped[str] = mapped_column(String)
    requirement_key: Mapped[str] = mapped_column(String)
    applicability: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    answer_type: Mapped[str] = mapped_column(String)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    pass_rule: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence_required: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_doc_type: Mapped[str | None] = mapped_column(String, nullable=True)


class Term(_Id, Base):
    __tablename__ = "term"
    rfx_id: Mapped[int] = mapped_column(ForeignKey("rfx.id"))
    type: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)


# --- Vendors, mail, responses --------------------------------------------------------------
class Vendor(_Id, Base):
    __tablename__ = "vendor"
    name: Mapped[str] = mapped_column(String)
    contact_email: Mapped[str] = mapped_column(String)


class Invitation(_Id, Base):
    __tablename__ = "invitation"
    rfx_id: Mapped[int] = mapped_column(ForeignKey("rfx.id"))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, default="AWAITING_RESPONSE")


class OutboxMessage(_Id, Base):
    __tablename__ = "outbox_message"
    kind: Mapped[str] = mapped_column(String, default="RFX")
    to_addr: Mapped[str] = mapped_column(String)
    subject: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    attachments: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class InboxMessage(_Id, Base):
    __tablename__ = "inbox_message"
    from_addr: Mapped[str] = mapped_column(String)
    subject: Mapped[str] = mapped_column(String)
    storage_path: Mapped[str] = mapped_column(String)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Response(_Id, Base):
    __tablename__ = "response"
    rfx_id: Mapped[int] = mapped_column(ForeignKey("rfx.id"))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    status: Mapped[str] = mapped_column(String, default="received")
    coverage_count: Mapped[int] = mapped_column(Integer, default=0)
    submissions: Mapped[list] = mapped_column(JSON, default=list)  # DL-23
    __table_args__ = (UniqueConstraint("rfx_id", "vendor_id"),)


class ProcessingSet(_Id, Base):
    __tablename__ = "processing_set"
    rfx_id: Mapped[int] = mapped_column(ForeignKey("rfx.id"))
    phase_b_status: Mapped[str] = mapped_column(String, default="pending")
    last_recompute_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot_hash: Mapped[str | None] = mapped_column(String, nullable=True)


class Document(_Id, Base):
    __tablename__ = "document"
    response_id: Mapped[int | None] = mapped_column(ForeignKey("response.id"), nullable=True)
    rfx_id: Mapped[int | None] = mapped_column(ForeignKey("rfx.id"), nullable=True)  # brief-pack docs
    filename: Mapped[str] = mapped_column(String)
    mime: Mapped[str] = mapped_column(String)
    sha256: Mapped[str] = mapped_column(String)
    storage_path: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    parse_status: Mapped[str] = mapped_column(String, default="pending")
    failure_reason: Mapped[str | None] = mapped_column(String, nullable=True)


class EvidenceUnit(Base):
    __tablename__ = "evidence_unit"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id"))
    kind: Mapped[str] = mapped_column(String)
    locator: Mapped[dict] = mapped_column(JSON)
    text: Mapped[str] = mapped_column(Text)
    ocr_confidence: Mapped[float | None] = mapped_column(nullable=True)


# --- Extraction ----------------------------------------------------------------------------
class ExtractionRun(_Id, Base):
    __tablename__ = "extraction_run"
    response_id: Mapped[int] = mapped_column(ForeignKey("response.id"))
    model: Mapped[str] = mapped_column(String)
    prompt_version: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    token_usage: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RawLineQuote(_Id, Base):
    __tablename__ = "raw_line_quote"
    run_id: Mapped[int] = mapped_column(ForeignKey("extraction_run.id"))
    payload: Mapped[dict] = mapped_column(JSON)  # full DocumentExtraction line record
    raw_fingerprint: Mapped[str] = mapped_column(String)


class DocumentTerm(_Id, Base):
    __tablename__ = "document_term"
    run_id: Mapped[int | None] = mapped_column(ForeignKey("extraction_run.id"), nullable=True)
    type: Mapped[str] = mapped_column(String)
    value: Mapped[str | None] = mapped_column(String, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    scope: Mapped[dict] = mapped_column(JSON, default=dict)
    text: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String, default="EXTRACTED")


class Reference(_Id, Base):
    __tablename__ = "reference"
    run_id: Mapped[int | None] = mapped_column(ForeignKey("extraction_run.id"), nullable=True)
    rfx_id: Mapped[int | None] = mapped_column(ForeignKey("rfx.id"), nullable=True)
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendor.id"), nullable=True)
    type: Mapped[str] = mapped_column(String)
    interpretation: Mapped[str] = mapped_column(String, default="AMBIGUOUS")
    scope_prices: Mapped[list] = mapped_column(JSON, default=list)
    scope_terms: Mapped[list] = mapped_column(JSON, default=list)
    text: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    candidates: Mapped[list] = mapped_column(JSON, default=list)
    confirmation_resolution_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class QuestionAnswer(_Id, Base):
    __tablename__ = "question_answer"
    run_id: Mapped[int] = mapped_column(ForeignKey("extraction_run.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"))
    answer_value: Mapped[str | None] = mapped_column(String, nullable=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    attachment_ids: Mapped[list] = mapped_column(JSON, default=list)


class DocumentFact(_Id, Base):
    __tablename__ = "document_fact"
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"))
    rfx_id: Mapped[int | None] = mapped_column(ForeignKey("rfx.id"), nullable=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("document.id"), nullable=True)
    filename: Mapped[str | None] = mapped_column(String, nullable=True)
    doc_type: Mapped[str | None] = mapped_column(String, nullable=True)
    standard: Mapped[str | None] = mapped_column(String, nullable=True)
    certificate_number: Mapped[str | None] = mapped_column(String, nullable=True)
    entity_name: Mapped[str | None] = mapped_column(String, nullable=True)
    issue_date: Mapped[str | None] = mapped_column(String, nullable=True)
    expiry_date: Mapped[str | None] = mapped_column(String, nullable=True)
    fact_status: Mapped[str] = mapped_column(String, default="EXTRACTED")
    evidence: Mapped[list] = mapped_column(JSON, default=list)


class LineMatch(_Id, Base):
    __tablename__ = "line_match"
    raw_line_quote_id: Mapped[int] = mapped_column(ForeignKey("raw_line_quote.id"))
    rfx_line_id: Mapped[int | None] = mapped_column(ForeignKey("rfx_line.id"), nullable=True)
    confidence: Mapped[str] = mapped_column(String)
    rationale: Mapped[str] = mapped_column(Text, default="")
    compliance: Mapped[str] = mapped_column(String)
    spec_diffs: Mapped[list] = mapped_column(JSON, default=list)


# --- Normalisation, statuses, assumptions -------------------------------------------------
class NormalizedQuote(_Id, Base):
    __tablename__ = "normalized_quote"
    rfx_line_id: Mapped[int] = mapped_column(ForeignKey("rfx_line.id"))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"))
    response_version: Mapped[int] = mapped_column(Integer, default=1)
    unit_price_inr_ex_gst: Mapped[str | None] = mapped_column(String, nullable=True)
    unit_status: Mapped[str] = mapped_column(String)
    unit_reasons: Mapped[list] = mapped_column(JSON, default=list)
    landed_inr_ex_gst: Mapped[str | None] = mapped_column(String, nullable=True)
    landed_status: Mapped[str] = mapped_column(String)
    freight_basis: Mapped[str] = mapped_column(String)
    freight_inr_per_box: Mapped[str | None] = mapped_column(String, nullable=True)
    weight_source: Mapped[str | None] = mapped_column(String, nullable=True)
    weight_g: Mapped[str | None] = mapped_column(String, nullable=True)
    constant_set_version: Mapped[str | None] = mapped_column(String, nullable=True)
    flags: Mapped[list] = mapped_column(JSON, default=list)
    trace: Mapped[list] = mapped_column(JSON, default=list)
    assumption_ids: Mapped[list] = mapped_column(JSON, default=list)
    fingerprint: Mapped[str] = mapped_column(String, default="")
    __table_args__ = (UniqueConstraint("rfx_line_id", "vendor_id"),)


class PhaseACell(_Id, Base):
    """Phase A output per vendor × line (DL-9): the input to every global recompute."""
    __tablename__ = "phase_a_cell"
    rfx_id: Mapped[int] = mapped_column(ForeignKey("rfx.id"))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"))
    line_no: Mapped[int] = mapped_column(Integer)
    cell: Mapped[dict] = mapped_column(JSON)
    inputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # raw normalisation inputs (re-normalise on FX/constants)
    __table_args__ = (UniqueConstraint("rfx_id", "vendor_id", "line_no"),)


class Resolution(_Id, Base):
    __tablename__ = "resolution"
    target: Mapped[dict] = mapped_column(JSON)
    type: Mapped[str] = mapped_column(String)
    value: Mapped[str | None] = mapped_column(String, nullable=True)
    choice: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_fingerprint: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(String, default="active")
    actor: Mapped[str] = mapped_column(String)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Assumption(_Id, Base):
    __tablename__ = "assumption"
    type: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    value: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    accepted_by: Mapped[str | None] = mapped_column(String, nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FxRate(Base):
    __tablename__ = "fx_rate"
    currency: Mapped[str] = mapped_column(String, primary_key=True)
    rate_to_inr: Mapped[str] = mapped_column(String)
    as_of: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    set_by: Mapped[str] = mapped_column(String)


class ConstantSet(Base):
    __tablename__ = "constant_set"
    version: Mapped[str] = mapped_column(String, primary_key=True)
    content_hash: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    constants: Mapped[list] = mapped_column(JSON)
    activated_by: Mapped[str | None] = mapped_column(String, nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BaselinePrice(_Id, Base):
    __tablename__ = "baseline_price"
    rfx_line_sku: Mapped[str] = mapped_column(String)
    vendor_name: Mapped[str] = mapped_column(String)  # required (DL-8)
    unit_price_inr_ex_gst: Mapped[str] = mapped_column(String)
    freight_basis: Mapped[str] = mapped_column(String)
    spec_signature: Mapped[str] = mapped_column(String)
    period: Mapped[str] = mapped_column(String)
    awarded: Mapped[bool] = mapped_column(Boolean)
    source: Mapped[str] = mapped_column(String)


class BaselineTerm(_Id, Base):
    __tablename__ = "baseline_term"
    vendor_name: Mapped[str] = mapped_column(String)  # required (DL-20)
    term_type: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(String)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    period: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)


class EligibilityResult(_Id, Base):
    __tablename__ = "eligibility_result"
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"))
    state: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text, default="")
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    override: Mapped[bool] = mapped_column(Boolean, default=False)


class ReviewItem(_Id, Base):
    __tablename__ = "review_item"
    target: Mapped[dict] = mapped_column(JSON)
    reason_code: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    suggested_resolution: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    money_at_risk: Mapped[str | None] = mapped_column(String, nullable=True)
    sensitivity: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    state: Mapped[str] = mapped_column(String, default="open")


class ClarificationPack(_Id, Base):
    __tablename__ = "clarification_pack"
    rfx_id: Mapped[int | None] = mapped_column(ForeignKey("rfx.id"), nullable=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"))
    content_hash: Mapped[str] = mapped_column(String, default="")
    outbox_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    items: Mapped[list] = mapped_column(JSON, default=list)
    generated_body: Mapped[str] = mapped_column(Text)
    edited_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="draft")
    created_by: Mapped[str] = mapped_column(String)
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Scenario(_Id, Base):
    __tablename__ = "scenario"
    rfx_id: Mapped[int | None] = mapped_column(ForeignKey("rfx.id"), nullable=True)
    name: Mapped[str] = mapped_column(String)
    context: Mapped[str] = mapped_column(String)
    params: Mapped[dict] = mapped_column(JSON)
    needs_review_override_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    freight_dependency_ack_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cells_used_fingerprints: Mapped[dict] = mapped_column(JSON, default=dict)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stale: Mapped[bool] = mapped_column(Boolean, default=False)


class AwardDecision(_Id, Base):
    __tablename__ = "award_decision"
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenario.id"))
    memo: Mapped[str] = mapped_column(Text)
    readiness_items: Mapped[list] = mapped_column(JSON, default=list)
    acknowledged_by: Mapped[str | None] = mapped_column(String, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded: Mapped[bool] = mapped_column(Boolean, default=False)


class AnalystAnswerRecord(_Id, Base):
    """Stored analyst answers so tables are exported from server-side results, never from client input (EXP-3)."""
    __tablename__ = "analyst_answer"
    rfx_id: Mapped[int] = mapped_column(Integer)
    session_id: Mapped[str] = mapped_column(String)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[dict] = mapped_column(JSON)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class FindingReview(_Id, Base):
    """Latest human review state of a derived finding (history lives in the append-only audit log)."""
    __tablename__ = "finding_review"
    rfx_id: Mapped[int] = mapped_column(Integer)
    finding_id: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)  # open / confirmed / rejected / clarification_requested / not_applicable
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("rfx_id", "finding_id"),)


# --- Append-only logs ---------------------------------------------------------------------
class AuditEvent(_Id, Base):
    __tablename__ = "audit_event"
    actor: Mapped[str] = mapped_column(String)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    action: Mapped[str] = mapped_column(String)
    target: Mapped[dict] = mapped_column(JSON)
    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class LlmCall(_Id, Base):
    __tablename__ = "llm_call"
    route: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    effort: Mapped[str] = mapped_column(String)
    prompt_version: Mapped[str] = mapped_column(String, default="")
    input_sha256: Mapped[str] = mapped_column(String)
    request_summary: Mapped[str] = mapped_column(Text)
    stop_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ConversationMessage(Base):
    __tablename__ = "conversation_message"
    conversation_id: Mapped[str] = mapped_column(String, primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[str] = mapped_column(String)
    content_json: Mapped[str] = mapped_column(Text)  # exact JSON of the content as sent/returned
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


APPEND_ONLY_TABLES = ("audit_event", "conversation_message", "llm_call")
