"""Deterministic evidence verification (architecture §7.3) — the main defence against invented values.

- every cited unit exists; the verbatim quote appears in the cited text; value_as_stated appears in
  the quote; the parsed number equals `value`  → otherwise EVIDENCE_NOT_FOUND (blocking)
- unit inheritance (DL-12): the source quote exists, contains a unit token, sits in the same or an
  adjacent unit of the same document, and no other unit token lies between source and price
  → otherwise the unit becomes UNKNOWN (UNIT_UNKNOWN)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.ingest.evidence import EvidenceUnit
from app.ingest.schemas import Evidence, LineQuote, Price
from app.ingest.units import UNIT_TOKEN, cross_check, has_unit_token

_CURRENCY = re.compile(r"(rs\.?|inr)\s*", re.I)


def norm(text: str) -> str:
    t = _CURRENCY.sub("₹", text)
    t = re.sub(r"(?<=\d),(?=\d)", "", t)
    return " ".join(t.split()).lower()


def parse_number(s: str) -> float | None:
    m = re.search(r"-?\d+(?:\.\d+)?", norm(s).replace("₹", ""))
    return float(m.group()) if m else None


@dataclass
class EvidenceCheck:
    ok: bool
    reasons: list[str] = field(default_factory=list)


def check_evidence(ev: Evidence, units: dict[str, EvidenceUnit], must_contain: str | None = None) -> EvidenceCheck:
    cited = [units.get(i) for i in ev.unit_ids]
    if not ev.unit_ids or any(u is None for u in cited):
        return EvidenceCheck(False, ["EVIDENCE_NOT_FOUND"])
    joined = norm(" ".join(u.text for u in cited))
    if norm(ev.quote) not in joined:
        return EvidenceCheck(False, ["EVIDENCE_NOT_FOUND"])
    if must_contain is not None and norm(must_contain) not in norm(ev.quote):
        return EvidenceCheck(False, ["EVIDENCE_NOT_FOUND"])
    return EvidenceCheck(True)


def check_price(p: Price, units: dict[str, EvidenceUnit]) -> EvidenceCheck:
    chk = check_evidence(p.evidence, units, must_contain=p.value_as_stated)
    if not chk.ok:
        return chk
    parsed = parse_number(p.value_as_stated)
    if parsed is None or (p.value is not None and abs(parsed - p.value) > 1e-9):
        return EvidenceCheck(False, ["EVIDENCE_NOT_FOUND"])
    return chk


PRICE_WORD = re.compile(r"\b(rate|rates|price|prices|amount|cost)\b", re.I)
DECLARATION = re.compile(r"\ball (prices|rates)\b|\b(prices|rates) are (in|quoted|per)\b", re.I)


def _header_or_declaration(src: EvidenceUnit, price: EvidenceUnit) -> bool:
    """A unit stated once for many prices (tables, letters): a column header above the price in the same sheet or
    table, naming a price/rate with a unit; or a sentence in the same document declaring the unit of all prices.
    Deterministic; the result is still an inference (ASSUMED, UNIT_INHERITED), never STATED."""
    if src.document_ref != price.document_ref or not UNIT_TOKEN.search(src.text):
        return False
    if DECLARATION.search(src.text):
        return True
    ls, lp = src.locator, price.locator
    if not PRICE_WORD.search(src.text):
        return False
    if "sheet" in ls and ls.get("sheet") == lp.get("sheet") and "row" in ls and "row" in lp:
        return ls["row"] < lp["row"] and ls.get("col", 0) <= lp.get("col", 0)
    if "table" in ls and ls.get("table") == lp.get("table"):
        return ls.get("row", 0) == 1 and ls.get("col") == lp.get("col") and lp.get("row", 0) > 1
    return False


def _adjacent(a: EvidenceUnit, b: EvidenceUnit) -> bool:
    if a.document_ref != b.document_ref:
        return False
    if a.id == b.id:
        return True
    la, lb = a.locator, b.locator
    if "line_no" in la and "line_no" in lb:
        return abs(la["line_no"] - lb["line_no"]) <= 1
    if "row" in la and "row" in lb and la.get("sheet") == lb.get("sheet"):
        return abs(la["row"] - lb["row"]) <= 1
    return False


def check_inheritance(lq: LineQuote, units: dict[str, EvidenceUnit]) -> EvidenceCheck:
    src = lq.unit_inherited_from
    price = lq.price or (lq.slabs[0].price if lq.slabs else None)  # slab-only lines inherit like single prices
    if src is None or price is None:
        return EvidenceCheck(False, ["UNIT_UNKNOWN"])
    if not check_evidence(src, units).ok or not has_unit_token(src.quote):
        return EvidenceCheck(False, ["UNIT_UNKNOWN"])
    src_unit, price_unit = units[src.unit_ids[0]], units[price.evidence.unit_ids[0]]
    if _header_or_declaration(src_unit, price_unit):
        return EvidenceCheck(True, ["UNIT_INHERITED"])  # table header / document-wide statement (still ASSUMED)
    if not _adjacent(src_unit, price_unit):
        return EvidenceCheck(False, ["UNIT_UNKNOWN"])
    if src_unit.id == price_unit.id:
        text = norm(src_unit.text)
        s_end = text.find(norm(src.quote))
        p_start = text.find(norm(price.evidence.quote), s_end + 1 if s_end >= 0 else 0)
        if s_end < 0 or p_start < 0:
            return EvidenceCheck(False, ["UNIT_UNKNOWN"])
        between = text[s_end + len(norm(src.quote)):p_start]
        if UNIT_TOKEN.search(between):
            return EvidenceCheck(False, ["UNIT_UNKNOWN"])
    return EvidenceCheck(True, ["UNIT_INHERITED"])


@dataclass
class VerifiedLine:
    quote: LineQuote
    unit_class: str
    reasons: list[str]
    flags: list[str]


def verify_line(lq: LineQuote, units: dict[str, EvidenceUnit]) -> VerifiedLine:
    reasons: list[str] = []
    flags: list[str] = list(lq.flags)
    prices = ([lq.price] if lq.price else []) + [s.price for s in lq.slabs]
    if not prices:
        reasons.append("EVIDENCE_NOT_FOUND")
    for p in prices:
        reasons += check_price(p, units).reasons
    unit_class = lq.unit_class
    if lq.unit_source == "INHERITED_FROM_CONTEXT":
        chk = check_inheritance(lq, units)
        reasons += chk.reasons
        if not chk.ok:
            unit_class = "UNKNOWN"
    elif lq.unit_source == "NONE" or unit_class == "UNKNOWN":
        unit_class = "UNKNOWN"
        reasons.append("UNIT_UNKNOWN")
    else:
        unit_class, extra = cross_check(unit_class, lq.unit_as_stated)
        flags += [f for f in extra if f == "UNIT_DICT_UNSEEN"]
        if unit_class == "UNKNOWN":
            reasons.append("UNIT_UNKNOWN")
    return VerifiedLine(lq, unit_class, sorted(set(reasons)), flags)
