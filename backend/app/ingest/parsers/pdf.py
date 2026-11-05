"""PDF (text layer) → EvidenceUnits, one per text line (D3:p1l4). A PDF without a text layer is a scan:
it is marked `deferred` for the OCR/vision paths (M3b), never treated as empty."""
from __future__ import annotations

import io
import unicodedata

from pypdf import PdfReader

from app.ingest.evidence import EvidenceUnit, ParsedDocument


def parse_pdf(ref: str, filename: str, data: bytes, mime: str = "application/pdf") -> ParsedDocument:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [p.extract_text() or "" for p in reader.pages]
    except Exception as e:
        return ParsedDocument(ref, filename, mime, "pdf", parse_status="failed", failure_reason=f"unreadable pdf: {e}", data=data)
    units = []
    for pi, text in enumerate(pages, start=1):
        for li, line in enumerate((l for l in unicodedata.normalize("NFKC", text).splitlines() if l.strip()), start=1):
            units.append(EvidenceUnit(f"{ref}:p{pi}l{li}", ref, "text_block", {"page": pi, "line": li}, line.strip()))
    if not units:
        return ParsedDocument(ref, filename, mime, "pdf", parse_status="deferred", data=data,
                              failure_reason="no text layer (scanned PDF): OCR/vision path arrives in M3b",
                              meta={"pages": len(pages)})
    return ParsedDocument(ref, filename, mime, "pdf", units=units, data=data, meta={"pages": len(pages)})
