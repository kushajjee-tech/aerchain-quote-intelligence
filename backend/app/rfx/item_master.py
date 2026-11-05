"""Deterministic item-master import with AI-assisted column mapping (DL-27, RFX-9).

The model sees ONLY the header row and 3 sample rows and proposes a column → field mapping with a
confidence. The buyer confirms it. Rows are then imported by code: values are copied exactly,
categorical values are normalised by fixed rules, and anything unrecognised becomes a gap. The model
never outputs line values.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import BytesIO
from typing import Literal, Optional

from openpyxl import load_workbook
from pydantic import BaseModel, Field

from app.llm.gateway import LLMGateway
from app.normalize.weight import construction_gaps

TARGET_FIELDS = [
    "sku_code", "description", "item_type", "dim_L", "dim_W", "dim_H", "blank_L", "blank_W", "ply",
    "flute_profile", *[f"gsm_layer_{i}" for i in range(1, 8)], "bf_liner", "bf_medium", "printing",
    "annual_qty", "reference_unit_weight_g", "reference_weight_source", "food_contact", "ignore",
]
FieldLit = Literal[tuple(TARGET_FIELDS)]  # type: ignore[valid-type]
REQUIRED_FIELDS = {"sku_code", "description", "item_type", "ply", "annual_qty"}


class ColumnMapping(BaseModel):
    column: str = Field(description="Header text exactly as in the file")
    field: FieldLit
    confidence: Literal["HIGH", "LOW"]
    note: Optional[str] = None


class MappingProposal(BaseModel):
    mappings: list[ColumnMapping]
    questions: list[str] = Field(default_factory=list, description="Anything the buyer must clarify about the columns")


MAPPING_SYSTEM = """You map the columns of a buyer's packaging item master to RFx line fields.
You see only the header row and a few sample rows. For each column choose exactly one target field
(or 'ignore'), with HIGH confidence only when the header and samples make the meaning unambiguous.
gsm_layer_N is the paper GSM of layer N counted from the outside. Never output row values."""


@dataclass
class Sheet:
    headers: list[str]
    rows: list[list]  # data rows
    first_data_row: int = 2


def read_item_master(data: bytes) -> Sheet:
    ws = load_workbook(BytesIO(data), data_only=True).worksheets[0]
    all_rows = [list(r) for r in ws.iter_rows(values_only=True)]
    headers = [str(h).strip() if h is not None else "" for h in all_rows[0]]
    rows = [r for r in all_rows[1:] if any(v not in (None, "") for v in r)]
    return Sheet(headers, rows)


def propose_mapping(gw: LLMGateway, sheet: Sheet) -> MappingProposal:
    sample = "\n".join(" | ".join("" if v is None else str(v) for v in r) for r in sheet.rows[:3])
    content = f"Columns:\n{' | '.join(sheet.headers)}\n\nSample rows (3):\n{sample}"
    return gw.structured("copilot_mapping", MappingProposal, [{"role": "user", "content": content}],
                         system=MAPPING_SYSTEM, prompt_version="mapping_v1")


class MappingNotConfirmed(ValueError):
    pass


def validate_confirmed(mapping: dict[str, str], headers: list[str]) -> None:
    unknown = set(mapping) - set(headers)
    if unknown:
        raise MappingNotConfirmed(f"mapping names columns not in the file: {sorted(unknown)}")
    used = [f for f in mapping.values() if f != "ignore"]
    dupes = {f for f in used if used.count(f) > 1}
    if dupes:
        raise MappingNotConfirmed(f"fields mapped twice: {sorted(dupes)}")
    missing = REQUIRED_FIELDS - set(used)
    if missing:
        raise MappingNotConfirmed(f"required fields unmapped: {sorted(missing)}")


# --- deterministic value rules ---------------------------------------------------------------
ITEM_TYPE_RULES = [(r"\brsc\b", "RSC"), (r"die[\s-]*cut", "DIE_CUT"), (r"partition", "PARTITION"), (r"\bpad\b|sheet", "PAD")]


def norm_item_type(v) -> str | None:
    t = str(v or "").lower()
    hits = {kind for pat, kind in ITEM_TYPE_RULES if re.search(pat, t)}
    return hits.pop() if len(hits) == 1 else None


def norm_print(v) -> dict | None:
    t = str(v or "").strip().lower()
    if t in ("plain", "none", "0", "no print", "unprinted"):
        return {"colours": 0, "type": "plain"}
    m = re.match(r"(\d)\s*c(olou?r)?s?\b", t)
    return {"colours": int(m.group(1)), "type": "flexo"} if m else None


def norm_bool(v) -> bool | None:
    t = str(v or "").strip().lower()
    return True if t in ("y", "yes", "true", "1") else (False if t in ("n", "no", "false", "0", "") else None)


def as_int(v) -> int | None:
    if v in (None, ""):
        return None
    try:
        f = float(str(v).replace(",", ""))
    except ValueError:
        return None
    return int(f) if f == int(f) else None


@dataclass
class ImportResult:
    lines: list[dict]
    line_gaps: dict[int, list[str]] = field(default_factory=dict)


def import_rows(sheet: Sheet, mapping: dict[str, str]) -> ImportResult:
    validate_confirmed(mapping, sheet.headers)
    col = {f: sheet.headers.index(h) for h, f in mapping.items() if f != "ignore"}
    get = lambda r, f: (r[col[f]] if f in col and col[f] < len(r) else None)
    res = ImportResult([])
    for i, r in enumerate(sheet.rows, start=1):
        gaps: list[str] = []
        excel_row = sheet.first_data_row + i - 1
        ply = as_int(get(r, "ply"))
        item_type = norm_item_type(get(r, "item_type"))
        if item_type is None:
            gaps.append(f"item type '{get(r, 'item_type')}' not recognised")
        printing = norm_print(get(r, "printing")) if "printing" in col else {"colours": 0, "type": "plain"}
        if printing is None:
            gaps.append(f"printing '{get(r, 'printing')}' not recognised")
        layers = []
        for pos in range(1, (ply or 0) + 1):
            gsm = as_int(get(r, f"gsm_layer_{pos}"))
            liner = pos % 2 == 1
            layers.append({"position": pos, "role": "liner" if liner else "medium", "gsm": gsm,
                           "bf": as_int(get(r, "bf_liner" if liner else "bf_medium"))})
        dims = {k: as_int(get(r, f"dim_{k}")) for k in ("L", "W", "H")}
        bl, bw = as_int(get(r, "blank_L")), as_int(get(r, "blank_W"))
        ref_w = as_int(get(r, "reference_unit_weight_g"))
        food = norm_bool(get(r, "food_contact")) if "food_contact" in col else False
        line = {
            "line_no": i, "sku_code": str(get(r, "sku_code") or "").strip(),
            "description": str(get(r, "description") or "").strip(), "item_type": item_type,
            "dims_mm": dims, "blank_size_mm": {"L": bl, "W": bw} if bl and bw else None, "ply": ply,
            "flute_profile": str(get(r, "flute_profile") or "").strip().upper(), "layers": layers, "printing": printing,
            "annual_qty": as_int(get(r, "annual_qty")), "reference_unit_weight_g": ref_w,
            "reference_weight_source": (str(get(r, "reference_weight_source")).strip() if ref_w and get(r, "reference_weight_source") else None),
            "food_contact": bool(food), "requires_fsc": False,
            "source_evidence": [{"sheet": "item master", "row": excel_row}],
        }
        if ref_w and not line["reference_weight_source"]:
            gaps.append("reference weight has no source")
        if line["annual_qty"] is None:
            gaps.append("annual quantity")
        if item_type == "RSC":
            gaps += construction_gaps(line)
        res.lines.append(line)
        if gaps:
            res.line_gaps[i] = gaps
    return res
