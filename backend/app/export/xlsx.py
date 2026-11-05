"""Exports (EXP-1/3). Built in memory and returned as bytes (no filesystem access). Values are written as
the exact stored Decimal text, so a re-read equals the source; excluded statuses are never exported as numbers."""
from __future__ import annotations

import csv
import io
import json

from openpyxl import Workbook
from openpyxl.styles import Font

from app.eligibility.rules import label

STATUS_LABEL = {"VERIFIED": "Verified", "EXTRACTED": "Extracted", "ASSUMED": "Assumed", "NEEDS_REVIEW": "Needs review",
                "UNRESOLVED": "Unresolved", "NOT_CONVERTIBLE": "Not convertible", "MISSING": "Missing"}
EXCLUDED = {"UNRESOLVED", "NOT_CONVERTIBLE", "MISSING"}


def _sheet(wb, title, header, rows):
    ws = wb.create_sheet(title)
    ws.append(header)
    for c in ws[1]:
        c.font = Font(bold=True)
    for r in rows:
        ws.append([json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for v in r])
    return ws


def cell_text(c: dict) -> tuple[str | None, str]:
    """(value, status label) exactly as the grid shows it."""
    if c.get("state") == "AWAITING_RESPONSE":
        return None, "Awaiting response"
    if c.get("state") == "PENDING_PROCESSING" or not c.get("status"):
        return None, "Processing"
    status = c["status"]
    if status in EXCLUDED or c.get("value") is None:
        return None, STATUS_LABEL[status]
    return c["value"], STATUS_LABEL[status]


def comparison_workbook(grid: dict, provenance: list[dict], eligibility: list[dict], exclusions: list[dict],
                        settings: dict) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    vendors = grid["vendors"]
    header = ["Line", "SKU", "Description", "Annual qty"]
    for v in vendors:
        header += [f"{v['name']} — ₹/box ({grid['basis']})", f"{v['name']} — status"]
    rows = []
    for r in grid["rows"]:
        row = [r["line_no"], r["sku_code"], r["description"], r["annual_qty"]]
        for v in vendors:
            cells = r["cells"]
            row += list(cell_text(cells.get(v["vendor_id"]) or cells[str(v["vendor_id"])]))
        rows.append(row)
    ws = _sheet(wb, "Comparison", header, rows)
    ws.append([])
    ws.append(["Basis: ex-GST ₹ per box. Excluded statuses (Unresolved, Not convertible, Missing) never carry a number."
               + (" PROVISIONAL: not all responses are processed." if grid["provisional"] else "")])
    _sheet(wb, "Sources", ["Line", "Vendor", "Role", "Quoted", "Unit id", "Document", "Unit text"],
           [[p["line_no"], p["vendor"], c["role"], c["quote"], u["id"], u["document"], u["text"]]
            for p in provenance if p.get("source") for c in p["source"]["cites"] for u in c["units"]])
    _sheet(wb, "Traces", ["Line", "Vendor", "#", "Step", "Detail"],
           [[p["line_no"], p["vendor"], i + 1, t.get("step"), {k: v for k, v in t.items() if k not in ("step", "cites")}]
            for p in provenance for i, t in enumerate(p["trace"]) if t.get("step") != "evidence"])
    _sheet(wb, "Assumptions", ["Line", "Vendor", "Assumption", "Status"],
           [[p["line_no"], p["vendor"], a, STATUS_LABEL.get(p["status"], p["status"])] for p in provenance for a in p["assumptions"]]
           + [[None, None, f"FX {k}: {v['rate']} as of {v['as_of']} ({v['source']})", None] for k, v in settings["fx"].items()]
           + [[None, None, f"Constant set {settings['constant_set']} — all values unvalidated unless marked", None]])
    _sheet(wb, "Eligibility", ["Vendor", "Section", "Question", "Key", "Result", "Reason"],
           [[e["vendor"], e["section"], e["no"], e["key"], label(e["state"]), e["reason"]] for e in eligibility])
    _sheet(wb, "Exclusions", ["Line", "Vendor", "Reason", "Detail"],
           [[e["line_no"], e["vendor"], e["reason"], e.get("detail")] for e in exclusions])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def table_workbook(columns: list[str], rows: list[dict], caveats: dict, exclusions: list[dict]) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    _sheet(wb, "Result", columns, [[r.get(c) for c in columns] for r in rows])
    _sheet(wb, "Caveats", ["Caveat", "Detail"], [[k, v] for k, v in caveats.items()])
    _sheet(wb, "Exclusions", ["Line", "Vendor", "Reason", "Detail"],
           [[e.get("line_no"), e.get("vendor"), e.get("reason"), e.get("detail")] for e in exclusions])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def table_csv(columns: list[str], rows: list[dict], caveats: dict) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(columns)
    for r in rows:
        w.writerow(["" if r.get(c) is None else r.get(c) for c in columns])
    w.writerow([])
    for k, v in caveats.items():
        w.writerow([f"# caveat: {k}", json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v])
    return buf.getvalue().encode("utf-8")


def audit_csv(events: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "at", "actor", "action", "target", "before", "after", "reason"])
    for e in events:
        w.writerow([e["id"], e["at"], e["actor"], e["action"], json.dumps(e["target"]), json.dumps(e["before"]),
                    json.dumps(e["after"], ensure_ascii=False), e["reason"] or ""])
    return buf.getvalue().encode("utf-8")
