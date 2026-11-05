"""Parser dispatch: eml, xlsx, docx and text-layer PDF. Images, scanned PDFs, xls and csv arrive in M3b
and are marked `deferred` (not failed) until then, so nothing is silently treated as empty."""
from __future__ import annotations

from app.ingest.evidence import ParsedDocument
from app.ingest.parsers.docx_ import DOCX_MIME, parse_docx
from app.ingest.parsers.eml import ParsedMessage, parse_eml
from app.ingest.parsers.image import parse_image
from app.ingest.parsers.pdf import parse_pdf
from app.ingest.parsers.xlsx import parse_xlsx

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
M3B_KINDS = {"application/pdf": "pdf", "image/jpeg": "image", "image/png": "image", "image/heic": "image",
             "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
             "application/vnd.ms-excel": "xls", "text/csv": "csv"}


def parse_attachment(ref: str, filename: str, mime: str, data: bytes) -> ParsedDocument:
    if mime == XLSX_MIME or filename.lower().endswith(".xlsx"):
        return parse_xlsx(ref, filename, data, mime)
    if mime == DOCX_MIME or filename.lower().endswith(".docx"):
        return parse_docx(ref, filename, data, mime)
    if mime.startswith("image/") or filename.lower().endswith((".jpg", ".jpeg", ".png")):
        return parse_image(ref, filename, data, mime)
    if mime == "application/pdf" or filename.lower().endswith(".pdf"):
        return parse_pdf(ref, filename, data, mime)
    kind = M3B_KINDS.get(mime, "other")
    return ParsedDocument(ref=ref, filename=filename, mime=mime, kind=kind, data=data,
                          parse_status="deferred", failure_reason=f"{kind} parser arrives in M3b")


def parse_message(data: bytes) -> tuple[ParsedMessage, list[ParsedDocument]]:
    """Returns the message and its documents: D1 = body, D2.. = attachments in order."""
    msg = parse_eml("D1", data)
    docs = [msg.body] + [parse_attachment(f"D{i}", fn, mime, b) for i, (fn, mime, b) in enumerate(msg.attachments, start=2)]
    return msg, docs
