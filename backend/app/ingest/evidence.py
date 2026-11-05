"""EvidenceUnits: the provenance atoms every extracted value must cite (architecture §6.1)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvidenceUnit:
    id: str  # short, stable, citable: "D2:Quotation!C8", "D1:l1"
    document_ref: str  # "D1", "D2", ...
    kind: str  # email_line / cell / paragraph / table_cell / text_block / ocr_line
    locator: dict[str, Any]
    text: str


@dataclass
class ParsedDocument:
    ref: str
    filename: str
    mime: str
    kind: str  # email_body / xlsx / pdf / docx / image / csv / other
    units: list[EvidenceUnit] = field(default_factory=list)
    parse_status: str = "parsed"  # parsed / failed / deferred
    failure_reason: str | None = None
    data: bytes = b""
    meta: dict[str, Any] = field(default_factory=dict)


def render_units(doc: ParsedDocument) -> str:
    """Compact, citable rendering of a document's units for the model prompt."""
    lines = [f"### Document {doc.ref}: {doc.filename} ({doc.kind})"]
    lines += [f"[{u.id}] {u.text}" for u in doc.units]
    return "\n".join(lines)
