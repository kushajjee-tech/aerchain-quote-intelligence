"""Baseline references (PRD §5.8; DL-5, DL-8, DL-20).

Reading A (prices): a candidate exists only in the SAME vendor's row for the SAME line with a
matching spec signature. Another vendor's price is never a candidate.
Reading B (terms): the same vendor's last-year terms for term types not stated this year — never
freight. Nothing is applied until the buyer records a confirmation.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal


def spec_signature(line: dict) -> str:
    dims = line.get("dims_mm") or {}
    layers = line.get("layers") or []
    sig = {
        "item_type": line["item_type"], "dims": [dims.get("L"), dims.get("W"), dims.get("H") or None],
        "ply": line["ply"], "flute_profile": line["flute_profile"], "gsm": [l.get("gsm") for l in layers],
        "bf": [l.get("bf") for l in layers], "printing": line.get("printing") or {},
    }
    return hashlib.sha256(json.dumps(sig, sort_keys=True).encode()).hexdigest()[:16]


@dataclass
class PriceCandidate:
    line_no: int
    candidate: Decimal | None
    reason: str  # REFERENCE_AMBIGUOUS (has candidate) / BASELINE_SPEC_CHANGED / BASELINE_NOT_FOR_VENDOR
    baseline_freight_basis: str | None = None
    source: str | None = None


def price_candidates(lines: list[dict], scope: list[int], vendor_name: str, rows: list[dict]) -> dict[int, PriceCandidate]:
    by_no = {l["line_no"]: l for l in lines}
    out = {}
    for n in scope:
        line = by_no[n]
        own = [r for r in rows if r["vendor"] == vendor_name and r["sku"] == line["sku_code"]]
        if not own:
            out[n] = PriceCandidate(n, None, "BASELINE_NOT_FOR_VENDOR")
            continue
        r = own[0]
        if r["spec_signature"] != spec_signature(line):
            out[n] = PriceCandidate(n, None, "BASELINE_SPEC_CHANGED", r.get("freight_basis"), r.get("source"))
            continue
        out[n] = PriceCandidate(n, Decimal(str(r["unit_price_inr_ex_gst"])), "REFERENCE_AMBIGUOUS", r.get("freight_basis"), r.get("source"))
    return out


REQUIRED_TERM_TYPES = ("PAYMENT", "VALIDITY", "LEAD_TIME", "MOQ", "FREIGHT")


def term_candidates(vendor_name: str, stated_types: set[str], term_rows: list[dict]) -> list[dict]:
    """Reading B: unstated term types with the vendor's own last-year value. FREIGHT is excluded (DL-8)."""
    out = []
    for t in term_rows:
        if t["vendor"] != vendor_name or t["term_type"] == "FREIGHT" or t["term_type"] in stated_types:
            continue
        out.append({"term_type": t["term_type"], "candidate": t["value"], "unit": t.get("unit"), "source": t.get("source"),
                    "status": "UNRESOLVED", "applied": False})
    return out
