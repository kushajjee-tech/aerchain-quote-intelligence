"""TEXT extraction stage (M3a): parsed documents → model extraction → deterministic verification."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.ingest.evidence import ParsedDocument, render_units
from app.ingest.schemas import DocumentExtraction
from app.ingest.wire import WireExtraction, WireFacts, WireLines, to_domain
from app.ingest.verify import VerifiedLine, check_evidence, verify_line
from app.llm.gateway import LLMGateway
from app.llm.prompts import EXTRACT_TEXT_SYSTEM, EXTRACT_TEXT_V1, extract_text_user


def rfx_context_text(rfx: dict) -> str:
    """Line list + questionnaire numbers. Contains the RFx only — never expected answers."""
    lines = [f"- line {l['line_no']}: {l['sku_code']} | {l['description']} | {l['item_type']} | "
             f"{l['ply']}-ply {l['flute_profile']} | {l['dims_mm']['L']}x{l['dims_mm']['W']}x{l['dims_mm']['H']} mm"
             for l in rfx["lines"]]
    qs = [f"- {q['no']} ({q['section']}): {q['text']}" for q in rfx["questionnaire"]]
    return "Lines:\n" + "\n".join(lines) + "\nQuestionnaire:\n" + "\n".join(qs)


@dataclass
class TextExtractionResult:
    extraction: DocumentExtraction
    lines: list[VerifiedLine]
    term_reasons: list[list[str]]
    answer_reasons: list[list[str]]
    units: dict = field(default_factory=dict)
    filenames: dict[str, str] = field(default_factory=dict)


LINES_MAX_TOKENS = 48000  # long price sheets + adaptive thinking (streams; see gateway.NON_STREAMING_MAX)


def run_text_extraction(gateway: LLMGateway, rfx: dict, docs: list[ParsedDocument]) -> TextExtractionResult:
    readable = [d for d in docs if d.parse_status == "parsed" and d.units]
    units = {u.id: u for d in readable for u in d.units}
    rendered = "\n\n".join(render_units(d) for d in readable)
    context = rfx_context_text(rfx)
    lines = gateway.structured(
        "extract_text", WireLines,
        [{"role": "user", "content": extract_text_user(context, rendered, part="lines")}],
        system=EXTRACT_TEXT_SYSTEM, prompt_version=EXTRACT_TEXT_V1,
        max_tokens=LINES_MAX_TOKENS,
    )
    facts = gateway.structured(
        "extract_text", WireFacts,
        [{"role": "user", "content": extract_text_user(context, rendered, part="facts")}],
        system=EXTRACT_TEXT_SYSTEM, prompt_version=EXTRACT_TEXT_V1,
    )
    extraction = WireExtraction(line_quotes=lines.line_quotes, **facts.model_dump())
    extraction: DocumentExtraction = to_domain(extraction)
    ocr_conf = {u.id: u.locator.get("ocr_conf") for u in units.values() if u.kind == "ocr_line"}
    lines = [verify_line(lq, units) for lq in extraction.line_quotes]
    for v in lines:  # image read by OCR only (no second read path in this build): single source → UNRESOLVED
        ids = [u for p in ([v.quote.price] if v.quote.price else []) + [s.price for s in v.quote.slabs] for u in p.evidence.unit_ids]
        if any(u in ocr_conf for u in ids):
            v.reasons.append("READ_SINGLE_SOURCE")
            if any((ocr_conf.get(u) or 0) < 80 for u in ids if u in ocr_conf):
                v.reasons.append("LOW_OCR_CONFIDENCE")
    terms = [check_evidence(t.evidence, units).reasons for t in extraction.document_terms]
    answers = [check_evidence(a.evidence, units).reasons for a in extraction.questionnaire_answers]
    return TextExtractionResult(extraction, lines, terms, answers, units, {d.ref: d.filename for d in docs})
