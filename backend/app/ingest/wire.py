"""Wire schema for extraction (structured outputs). The API caps strict schemas at 24 optional and 16 union-typed
(nullable) parameters in total; the domain schema (`schemas.py`) has many nullable fields. The wire form therefore
has NO optional and NO nullable fields: "" means "not stated", 0 means "none", and a nested object that may be
absent is a list of zero or one item. Numbers are never taken from the model: they are parsed deterministically
from the text copied as written (`value_as_stated`). `to_domain` converts back, so verification, matching and
normalisation are unchanged."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.ingest.schemas import (AttachedDocument, Answer, DocTerm, DocTypeLit, DocumentExtraction, Evidence, FlagLit,
                                GroupScope, LineQuote, Price, RefItem, Slab, SourceLit, SpecStated, TermTypeLit, UnitClassLit)
from app.ingest.verify import parse_number


class WPrice(BaseModel):
    value_as_stated: str = Field(description="The number exactly as written, e.g. '42' or '4,800'")
    currency_as_stated: str = Field(description="Currency symbol/code as written, or \"\" if none")
    currency_source: SourceLit
    evidence: Evidence


class WSlab(BaseModel):
    min_qty: int = Field(description="Lower quantity bound, 0 if none")
    max_qty: int = Field(description="Upper quantity bound, 0 if open-ended")
    price: WPrice


class WGroup(BaseModel):
    attribute: Literal["ply"]
    value: int
    evidence: Evidence


class WSpec(BaseModel):
    ply: int = Field(description="0 if not stated")
    flute_profile: str = Field(description="\"\" if not stated")
    dims_as_stated: str = Field(description="\"\" if not stated")
    layer_gsm: list[int]
    bf_as_stated: str = Field(description="\"\" if not stated")
    evidence: Evidence


class WLine(BaseModel):
    vendor_line_ref: str
    description_as_stated: str
    item_code: str = Field(description="Buyer SKU/customer code if the vendor wrote one, else \"\"")
    price: list[WPrice] = Field(description="One single price, or empty if only slabs are given")
    slabs: list[WSlab]
    unit_as_stated: str = Field(description="\"\" if no unit is written")
    unit_class: UnitClassLit
    unit_source: SourceLit
    unit_inherited_from: list[Evidence] = Field(description="Only when unit_source is INHERITED_FROM_CONTEXT, else empty")
    applies_to_group: list[WGroup] = Field(description="Only for a price stated for a group, else empty")
    vendor_box_weight_g: str = Field(description="Box weight in grams as written, or \"\"")
    spec_as_stated: list[WSpec] = Field(description="Only if the vendor restates the construction, else empty")
    flags: list[FlagLit]


class WTerm(BaseModel):
    type: TermTypeLit
    value: str = Field(description="As written, or \"\"")
    unit: str = Field(description="As written, e.g. 'per box', 'USD per box', '%', 'days', or \"\"")
    scope: str = Field(description="'all', 'ply=5', 'lines: ...' or free text if unclear")
    text: str
    evidence: Evidence


class WAnswer(BaseModel):
    question_no: str = Field(description="The RFx question number, e.g. 'Q3'")
    answer_value: str = Field(description="The short answer as written, or \"\"")
    answer_text: str
    evidence: Evidence
    attachment_refs: list[str]


class WDoc(BaseModel):
    document_ref: str = Field(description="The document id, e.g. 'D3'")
    doc_type: DocTypeLit
    entity_name: str = Field(description="Organisation the document is issued to/for, as written, or \"\"")
    reference_no: str = Field(description="As written, or \"\"")
    standard: str = Field(description="As written, or \"\"")
    issue_date_as_stated: str = Field(description="Issue/test/declaration date exactly as written, or \"\"")
    expiry_as_stated: str = Field(description="The validity/expiry statement exactly as written, or \"\"")
    evidence: Evidence


class WireLines(BaseModel):
    """Call 1 of 2: prices only. The full schema exceeds the structured-output grammar limit, so it is split."""
    line_quotes: list[WLine]


class WireFacts(BaseModel):
    """Call 2 of 2: everything that is not a line price."""
    document_terms: list[WTerm]
    references: list[RefItem]
    questionnaire_answers: list[WAnswer]
    attached_documents: list[WDoc]
    gst_statement: Literal["SILENT", "STATED", "AMBIGUOUS"]


class WireExtraction(BaseModel):
    line_quotes: list[WLine]
    document_terms: list[WTerm]
    references: list[RefItem]
    questionnaire_answers: list[WAnswer]
    attached_documents: list[WDoc]
    gst_statement: Literal["SILENT", "STATED", "AMBIGUOUS"]


def _s(x: str) -> str | None:
    return x if x not in ("", None) else None


def _price(p: WPrice) -> Price:
    return Price(value_as_stated=p.value_as_stated, value=parse_number(p.value_as_stated),
                 currency_as_stated=_s(p.currency_as_stated), currency_source=p.currency_source, evidence=p.evidence)


def to_domain(w: WireExtraction) -> DocumentExtraction:
    lines = []
    for l in w.line_quotes:
        sp = l.spec_as_stated[0] if l.spec_as_stated else None
        g = l.applies_to_group[0] if l.applies_to_group else None
        lines.append(LineQuote(
            vendor_line_ref=l.vendor_line_ref, description_as_stated=l.description_as_stated, item_code=_s(l.item_code),
            price=_price(l.price[0]) if l.price else None,
            slabs=[Slab(min_qty=s.min_qty or None, max_qty=s.max_qty or None, price=_price(s.price)) for s in l.slabs],
            unit_as_stated=_s(l.unit_as_stated), unit_class=l.unit_class, unit_source=l.unit_source,
            unit_inherited_from=l.unit_inherited_from[0] if l.unit_inherited_from else None,
            applies_to_group=GroupScope(attribute=g.attribute, value=g.value, evidence=g.evidence) if g else None,
            vendor_box_weight_g=parse_number(l.vendor_box_weight_g) if l.vendor_box_weight_g else None,
            spec_as_stated=SpecStated(ply=sp.ply or None, flute_profile=_s(sp.flute_profile), dims_as_stated=_s(sp.dims_as_stated),
                                      layer_gsm=sp.layer_gsm, bf_as_stated=_s(sp.bf_as_stated), evidence=sp.evidence) if sp else None,
            flags=l.flags))
    return DocumentExtraction(
        line_quotes=lines,
        document_terms=[DocTerm(type=t.type, value=_s(t.value), unit=_s(t.unit), scope=t.scope, text=t.text, evidence=t.evidence)
                        for t in w.document_terms],
        references=w.references,
        questionnaire_answers=[Answer(question_no=a.question_no, answer_value=_s(a.answer_value), answer_text=a.answer_text,
                                      evidence=a.evidence, attachment_refs=a.attachment_refs) for a in w.questionnaire_answers],
        attached_documents=[AttachedDocument(document_ref=d.document_ref, doc_type=d.doc_type, entity_name=_s(d.entity_name),
                                             reference_no=_s(d.reference_no), standard=_s(d.standard),
                                             issue_date_as_stated=_s(d.issue_date_as_stated), expiry_as_stated=_s(d.expiry_as_stated),
                                             evidence=d.evidence) for d in w.attached_documents],
        gst_statement=w.gst_statement)


def to_wire(d: dict) -> dict:
    """Domain-shaped dict → wire dict (used by test mocks that describe what a correct model reads)."""
    def ev(e):
        return e

    def price(p):
        return {"value_as_stated": p["value_as_stated"], "currency_as_stated": p.get("currency_as_stated") or "",
                "currency_source": p["currency_source"], "evidence": p["evidence"]}
    lines = []
    for l in d.get("line_quotes", []):
        sp = l.get("spec_as_stated")
        lines.append({
            "vendor_line_ref": l["vendor_line_ref"], "description_as_stated": l["description_as_stated"],
            "item_code": l.get("item_code") or "", "price": [price(l["price"])] if l.get("price") else [],
            "slabs": [{"min_qty": s.get("min_qty") or 0, "max_qty": s.get("max_qty") or 0, "price": price(s["price"])}
                      for s in l.get("slabs", [])],
            "unit_as_stated": l.get("unit_as_stated") or "", "unit_class": l["unit_class"], "unit_source": l["unit_source"],
            "unit_inherited_from": [l["unit_inherited_from"]] if l.get("unit_inherited_from") else [],
            "applies_to_group": [l["applies_to_group"]] if l.get("applies_to_group") else [],
            "vendor_box_weight_g": str(l["vendor_box_weight_g"]) if l.get("vendor_box_weight_g") else "",
            "spec_as_stated": [{"ply": sp.get("ply") or 0, "flute_profile": sp.get("flute_profile") or "",
                                "dims_as_stated": sp.get("dims_as_stated") or "", "layer_gsm": sp.get("layer_gsm", []),
                                "bf_as_stated": sp.get("bf_as_stated") or "", "evidence": sp["evidence"]}] if sp else [],
            "flags": l.get("flags", [])})
    return {
        "line_quotes": lines,
        "document_terms": [{"type": t["type"], "value": t.get("value") or "", "unit": t.get("unit") or "", "scope": t["scope"],
                            "text": t["text"], "evidence": t["evidence"]} for t in d.get("document_terms", [])],
        "references": d.get("references", []),
        "questionnaire_answers": [{"question_no": a["question_no"], "answer_value": a.get("answer_value") or "",
                                   "answer_text": a["answer_text"], "evidence": a["evidence"],
                                   "attachment_refs": a.get("attachment_refs", [])} for a in d.get("questionnaire_answers", [])],
        "attached_documents": [{"document_ref": x["document_ref"], "doc_type": x["doc_type"], "entity_name": x.get("entity_name") or "",
                                "reference_no": x.get("reference_no") or "", "standard": x.get("standard") or "",
                                "issue_date_as_stated": x.get("issue_date_as_stated") or "",
                                "expiry_as_stated": x.get("expiry_as_stated") or "", "evidence": x["evidence"]}
                               for x in d.get("attached_documents", [])],
        "gst_statement": d.get("gst_statement", "SILENT")}
