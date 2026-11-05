"""Phase B (DL-9), minimal slice version: global, order-independent cross-vendor checks.

Peers are leave-one-out medians of OTHER vendors' Phase A values (never Phase B results), so the
outcome does not depend on processing order. Unit-magnitude anomalies are never auto-fixed.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from statistics import median

from app.domain.enums import ValueStatus as S
from app.normalize.constants import CONSTANT_SET_V1, ConstantSet
from app.normalize.engine import NormalizedCell
from app.normalize.money import q4
from app.validate.status import status_from


def _suggest(price: Decimal, ref: Decimal) -> dict:
    best = min((Decimal(100), Decimal(1000), Decimal("0.01")), key=lambda f: abs((price / f) / ref - 1))
    return {"divide_by": str(best), "suggested_unit_price": str(q4(price / best))}


def phase_b(cells: dict[str, dict[int, NormalizedCell]], baseline: dict[int, Decimal] | None = None,
            cs: ConstantSet = CONSTANT_SET_V1) -> dict[str, dict[int, NormalizedCell]]:
    baseline = baseline or {}
    suspect, lo, hi = cs.get("check.unit_suspect_ratio"), cs.get("check.outlier_low"), cs.get("check.outlier_high")
    out: dict[str, dict[int, NormalizedCell]] = {v: {} for v in sorted(cells)}
    lines = sorted({n for per in cells.values() for n in per})
    for n in lines:
        phase_a_values = {v: cells[v][n].unit_price_inr_ex_gst for v in sorted(cells)
                          if n in cells[v] and cells[v][n].unit_price_inr_ex_gst is not None}
        for v in sorted(cells):
            if n not in cells[v]:
                continue
            c = cells[v][n]
            if c.unit_price_inr_ex_gst is None:
                out[v][n] = c
                continue
            peers = [p for k, p in phase_a_values.items() if k != v]
            ref, ref_kind = (Decimal(median(peers)), "peer_median") if len(peers) >= 2 else \
                ((baseline[n], "baseline") if n in baseline else (None, None))
            reasons, flags, trace = list(c.reasons), list(c.flags), list(c.trace)
            price = c.unit_price_inr_ex_gst
            if ref is None:
                flags.append("PLAUSIBILITY_UNCHECKED")
                trace.append({"step": "plausibility", "label": "no reference (fewer than 2 peers, no baseline)"})
            else:
                ratio = price / ref
                check = {"step": "plausibility", "reference": str(q4(ref)), "reference_kind": ref_kind, "ratio": str(q4(ratio)),
                         "constants": [cs.cite("check.unit_suspect_ratio"), cs.cite("check.outlier_low"), cs.cite("check.outlier_high")]}
                if ratio >= suspect or ratio <= 1 / suspect:
                    reasons.append("UNIT_SUSPECT")
                    check["suggestion"] = _suggest(price, ref)
                elif ratio < lo or ratio > hi:
                    reasons.append("OUTLIER")
                trace.append(check)
            status = status_from(reasons, cap_extracted=(ref is None or not c.auto_verify_candidate),
                                 auto_verify_ok=c.auto_verify_candidate and ref is not None)
            if status in (S.UNRESOLVED, S.NOT_CONVERTIBLE):
                trace.append({"step": "candidate", "label": "number withheld until resolved", "candidate": str(price)})
                price = None
            landed = c.landed_inr_ex_gst if price is not None else None
            if price is None:
                landed_status = status
            elif landed is None:
                landed_status = S.NOT_CONVERTIBLE  # FREIGHT_UNKNOWN on the landed basis
            else:
                landed_status = status
            out[v][n] = replace(c, unit_price_inr_ex_gst=price, unit_status=status, reasons=sorted(set(reasons)),
                                flags=sorted(set(flags)), trace=trace, landed_inr_ex_gst=landed, landed_status=landed_status)
    return out


def snapshot_hash(cells: dict[str, dict[int, NormalizedCell]]) -> str:
    rows = [[v, n, str(c.unit_price_inr_ex_gst), str(c.unit_status), c.reasons, c.flags, str(c.landed_inr_ex_gst),
             str(c.landed_status)] for v in sorted(cells) for n, c in sorted(cells[v].items())]
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()
