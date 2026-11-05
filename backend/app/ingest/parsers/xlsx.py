"""xlsx → EvidenceUnits: one unit per non-empty cell, with sheet!cell locator and merged ranges."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

from openpyxl import load_workbook

from app.ingest.evidence import EvidenceUnit, ParsedDocument


def display(value) -> str:
    """Text as a person reads the cell (no float artefacts, no trailing .0)."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        d = Decimal(repr(value))
        return format(d.normalize(), "f") if d == d.to_integral_value() else format(d, "f")
    if isinstance(value, (datetime, date)):
        return value.isoformat()[:10]
    return str(value).strip()


def parse_xlsx(ref: str, filename: str, data: bytes, mime: str) -> ParsedDocument:
    doc = ParsedDocument(ref=ref, filename=filename, mime=mime, kind="xlsx", data=data)
    try:
        wb = load_workbook(BytesIO(data), data_only=True, read_only=False)
    except Exception as e:  # corrupt / not a workbook
        doc.parse_status, doc.failure_reason = "failed", f"unreadable workbook: {type(e).__name__}"
        return doc
    for ws in wb.worksheets:
        merged = {str(r): r for r in ws.merged_cells.ranges}
        merged_at = {}
        for name, r in merged.items():
            merged_at[(r.min_row, r.min_col)] = name
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is None or str(cell.value).strip() == "":
                    continue
                text = display(cell.value)
                loc = {"sheet": ws.title, "cell": cell.coordinate, "row": cell.row, "col": cell.column}
                if (cell.row, cell.column) in merged_at:
                    loc["merged"] = merged_at[(cell.row, cell.column)]
                doc.units.append(EvidenceUnit(f"{ref}:{ws.title}!{cell.coordinate}", ref, "cell", loc, text))
    if not doc.units:
        doc.parse_status, doc.failure_reason = "failed", "workbook has no readable cells"
    return doc
