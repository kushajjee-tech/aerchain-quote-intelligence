"""Line matching (architecture §7.5): deterministic pre-match (item code, exact dims) → AI proposals for
the leftovers (match_ai.py, passed in) → one-to-one check → group expansion → reference scope. Anything
not matched stays UNMATCHED (never placed by row position). Spec comparison: spec_diff.py."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.ingest.verify import VerifiedLine


@dataclass
class LineAssignment:
    rfx_line_no: int
    source: VerifiedLine
    how: str  # item_code / dims_ply / group
    confidence: str = "HIGH"


@dataclass
class MatchResult:
    individual: dict[int, list[LineAssignment]] = field(default_factory=dict)
    group: dict[int, LineAssignment] = field(default_factory=dict)
    unmatched: list[VerifiedLine] = field(default_factory=list)


def _norm_code(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _dims_in(text: str) -> tuple[int, ...] | None:
    m = re.search(r"(\d{2,4})\s*[x×*]\s*(\d{2,4})\s*[x×*]\s*(\d{2,4})", text)
    return tuple(int(x) for x in m.groups()) if m else None


def match_lines(rfx_lines: list[dict], verified: list[VerifiedLine], ai: dict[str, dict] | None = None) -> MatchResult:
    """ai: accepted AI proposals {vendor_line_ref: {line_no, confidence, reason}} for deterministic leftovers."""
    ai = ai or {}
    by_code = {_norm_code(l["sku_code"]): l for l in rfx_lines}
    res = MatchResult()
    for v in verified:
        q = v.quote
        if q.applies_to_group is not None:
            continue  # expanded below
        line = by_code.get(_norm_code(q.item_code)) if q.item_code else None
        how = "item_code"
        if line is None:
            dims = _dims_in(q.description_as_stated)
            cands = [l for l in rfx_lines if dims and (l["dims_mm"]["L"], l["dims_mm"]["W"], l["dims_mm"]["H"]) == dims]
            line, how = (cands[0], "dims_ply") if len(cands) == 1 else (None, "")
        if line is None and q.vendor_line_ref in ai:
            p = ai[q.vendor_line_ref]
            line, how = next(l for l in rfx_lines if l["line_no"] == p["line_no"]), "ai"
            res.individual.setdefault(line["line_no"], []).append(LineAssignment(line["line_no"], v, how, p["confidence"]))
            continue
        if line is None:
            res.unmatched.append(v)
            continue
        res.individual.setdefault(line["line_no"], []).append(LineAssignment(line["line_no"], v, how))
    for v in verified:
        g = v.quote.applies_to_group
        if g is None or g.attribute != "ply":
            continue
        for l in rfx_lines:  # every item type of that ply; convertibility is decided in normalisation
            if l["ply"] == g.value and l["line_no"] not in res.individual:
                res.group[l["line_no"]] = LineAssignment(l["line_no"], v, "group")
    return res


def reference_scope(rfx_lines: list[dict], match: MatchResult) -> list[int]:
    """Reading A of an ambiguous reference: RFx lines not priced by any other statement (DL-20)."""
    priced = set(match.individual) | set(match.group)
    return [l["line_no"] for l in rfx_lines if l["line_no"] not in priced]
