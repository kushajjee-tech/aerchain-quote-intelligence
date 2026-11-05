"""Lossless JSON round trip for NormalizedCell (Decimals as text)."""
from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal

from app.domain.enums import ValueStatus
from app.normalize.engine import NormalizedCell

_DEC = ("unit_price_inr_ex_gst", "freight_inr_per_box", "landed_inr_ex_gst", "weight_g")


def to_json(c: NormalizedCell) -> dict:
    d = asdict(c)
    for k in _DEC:
        d[k] = None if d[k] is None else str(d[k])
    d["unit_status"], d["landed_status"] = str(c.unit_status), str(c.landed_status)
    return d


def from_json(d: dict) -> NormalizedCell:
    d = dict(d)
    for k in _DEC:
        d[k] = None if d[k] is None else Decimal(d[k])
    d["unit_status"], d["landed_status"] = ValueStatus(d["unit_status"]), ValueStatus(d["landed_status"])
    return NormalizedCell(**d)


# --- raw normalisation inputs (so FX / constant-set changes re-normalise without re-reading) ---------
from app.normalize.engine import QuoteInput, ResponseContext  # noqa: E402

_QDEC = ("value", "vendor_weight_g", "reference_candidate")


def input_to_json(q: QuoteInput) -> dict:
    d = asdict(q)
    for k in _QDEC:
        d[k] = None if d[k] is None else str(d[k])
    return d


def input_from_json(d: dict) -> QuoteInput:
    d = dict(d)
    for k in _QDEC:
        d[k] = None if d[k] is None else Decimal(d[k])
    return QuoteInput(**d)


def ctx_to_json(c: ResponseContext) -> dict:
    return {"gst_statement": c.gst_statement, "gst_stated_exclusive": c.gst_stated_exclusive, "rfx_gst_basis": c.rfx_gst_basis,
            "freight_terms": c.freight_terms,
            "discounts": [{**d, "pct": str(d["pct"])} for d in c.discounts]}


def ctx_from_json(d: dict, fx_rates: dict, constants) -> ResponseContext:
    return ResponseContext(gst_statement=d["gst_statement"], gst_stated_exclusive=d["gst_stated_exclusive"],
                           rfx_gst_basis=d["rfx_gst_basis"], freight_terms=d["freight_terms"],
                           discounts=[{**x, "pct": Decimal(x["pct"])} for x in d["discounts"]],
                           fx_rates=fx_rates, constants=constants)
