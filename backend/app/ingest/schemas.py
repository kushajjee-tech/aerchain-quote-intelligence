"""Structured-output schemas for TEXT extraction (architecture §7.2). Values are copied AS STATED;
the model never converts units or currency. Nullable everywhere: "not found" beats a guess."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

UnitClassLit = Literal["PER_BOX", "PER_100", "PER_1000", "PER_DOZEN", "PER_KG", "PER_SET", "LUMP_SUM", "UNKNOWN"]
SourceLit = Literal["STATED", "INHERITED_FROM_CONTEXT", "NONE"]
FlagLit = Literal["ambiguous_unit", "illegible", "conflicting_values", "unclear_scope"]


class Evidence(BaseModel):
    unit_ids: list[str] = Field(description="EvidenceUnit ids that contain the quote")
    quote: str = Field(description="Verbatim text copied from the cited unit(s)")


class Price(BaseModel):
    value_as_stated: str = Field(description="The number exactly as written, e.g. '42' or '4,800'")
    value: Optional[float] = None
    currency_as_stated: Optional[str] = None
    currency_source: SourceLit
    evidence: Evidence


class Slab(BaseModel):
    min_qty: Optional[int] = None
    max_qty: Optional[int] = None
    price: Price


class GroupScope(BaseModel):
    attribute: Literal["ply"]
    value: int
    evidence: Evidence


class SpecStated(BaseModel):
    """The construction the vendor restates for its line, copied as written (null where not stated)."""
    ply: Optional[int] = None
    flute_profile: Optional[str] = None
    dims_as_stated: Optional[str] = Field(None, description="Dimensions exactly as written, e.g. '250x200x150 mm'")
    layer_gsm: list[int] = Field(default_factory=list, description="Layer GSMs in the order written")
    bf_as_stated: Optional[str] = Field(None, description="Bursting factor(s) as written")
    evidence: Evidence


class LineQuote(BaseModel):
    vendor_line_ref: str
    description_as_stated: str
    item_code: Optional[str] = Field(None, description="Buyer SKU/customer code if the vendor wrote one")
    price: Optional[Price] = Field(None, description="Single price; null if only slabs are given")
    slabs: list[Slab] = Field(default_factory=list)
    unit_as_stated: Optional[str] = None
    unit_class: UnitClassLit
    unit_source: SourceLit
    unit_inherited_from: Optional[Evidence] = None
    applies_to_group: Optional[GroupScope] = None
    vendor_box_weight_g: Optional[float] = None
    spec_as_stated: Optional[SpecStated] = Field(None, description="Only if the vendor restates the construction")
    flags: list[FlagLit] = Field(default_factory=list)


TermTypeLit = Literal["DISCOUNT_PCT", "DISCOUNT_ABS", "FREIGHT", "GST", "VALIDITY", "PAYMENT", "TOOLING",
                      "ESCALATION", "MOQ", "LEAD_TIME", "OTHER"]


class DocTerm(BaseModel):
    type: TermTypeLit
    value: Optional[str] = None
    unit: Optional[str] = None
    scope: str = Field(description="'all', 'ply=5', 'lines: ...' or free text if unclear")
    text: str
    evidence: Evidence


class RefItem(BaseModel):
    type: Literal["PRIOR_UNSPECIFIED", "OTHER"]
    scope_text: str
    evidence: Evidence


class Answer(BaseModel):
    question_no: str = Field(description="The RFx question number, e.g. 'Q3'")
    answer_value: Optional[str] = None
    answer_text: str
    evidence: Evidence
    attachment_refs: list[str] = Field(default_factory=list)


DocTypeLit = Literal["ISO_9001_CERTIFICATE", "BCT_ECT_TEST_REPORT", "FOOD_CONTACT_DECLARATION", "FSC_CERTIFICATE",
                     "GST_REGISTRATION", "OTHER"]


class AttachedDocument(BaseModel):
    """Facts a certificate / report / declaration states about itself. Dates are copied as written."""
    document_ref: str = Field(description="The document id, e.g. 'D3'")
    doc_type: DocTypeLit
    entity_name: Optional[str] = Field(None, description="The organisation the document is issued to or for, as written")
    reference_no: Optional[str] = None
    standard: Optional[str] = None
    issue_date_as_stated: Optional[str] = Field(None, description="Issue/test/declaration date exactly as written")
    expiry_as_stated: Optional[str] = Field(None, description="The validity/expiry statement exactly as written")
    evidence: Evidence


class DocumentExtraction(BaseModel):
    line_quotes: list[LineQuote] = Field(default_factory=list)
    document_terms: list[DocTerm] = Field(default_factory=list)
    references: list[RefItem] = Field(default_factory=list)
    questionnaire_answers: list[Answer] = Field(default_factory=list)
    attached_documents: list[AttachedDocument] = Field(default_factory=list)
    gst_statement: Literal["SILENT", "STATED", "AMBIGUOUS"] = "SILENT"
