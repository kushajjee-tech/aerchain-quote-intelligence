"""docx → EvidenceUnits: one unit per non-empty paragraph (D2:p3) and per table cell (D2:t1r2c3)."""
from __future__ import annotations

import io
import unicodedata

import docx

from app.ingest.evidence import EvidenceUnit, ParsedDocument

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def parse_docx(ref: str, filename: str, data: bytes, mime: str = DOCX_MIME) -> ParsedDocument:
    try:
        d = docx.Document(io.BytesIO(data))
    except Exception as e:  # corrupt or not a docx: failed, never silently empty
        return ParsedDocument(ref, filename, mime, "docx", parse_status="failed", failure_reason=f"unreadable docx: {e}", data=data)
    units = []
    for i, p in enumerate(d.paragraphs, start=1):
        t = unicodedata.normalize("NFKC", p.text).strip()
        if t:
            units.append(EvidenceUnit(f"{ref}:p{i}", ref, "paragraph", {"paragraph": i}, t))
    for ti, tbl in enumerate(d.tables, start=1):
        for ri, row in enumerate(tbl.rows, start=1):
            for ci, cell in enumerate(row.cells, start=1):
                t = unicodedata.normalize("NFKC", cell.text).strip()
                if t:
                    units.append(EvidenceUnit(f"{ref}:t{ti}r{ri}c{ci}", ref, "table_cell", {"table": ti, "row": ri, "col": ci}, t))
    return ParsedDocument(ref, filename, mime, "docx", units=units, data=data,
                          parse_status="parsed" if units else "failed", failure_reason=None if units else "no text in docx")
