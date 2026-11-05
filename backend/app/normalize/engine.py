"""Phase A cell normalisation (PRD §5.5/§6.3; architecture §8). Pure function, Decimal arithmetic.

Order: as quoted → slab → qty/weight conversion → (discounts, FX: M2b) → GST → unit_price_inr_ex_gst
→ + freight (if the basis allows) → landed. Every step is a trace entry. Status comes only from
validate.status. Phase A never promotes to VERIFIED; Phase B decides that after plausibility checks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.enums import ValueStatus
from app.normalize.constants import CONSTANT_SET_V1, ConstantSet
from app.normalize.freight import freight_basis, freight_currency
from app.normalize.gst import gst_reasons
from app.normalize.money import q4
from app.normalize.slabs import select_slab, slab_value
from app.normalize.units import to_per_box
from app.normalize.weight import resolve_weight
from app.validate.status import status_from

ENGINE_VERSION = "m2a-1"


@dataclass
class QuoteInput:
    quoted: bool = True
    value: Decimal | None = None  # as stated, before conversion
    unit_class: str = "UNKNOWN"
    verification_reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    slabs: list[dict] = field(default_factory=list)
    vendor_weight_g: Decimal | None = None
    image_sourced: bool = False
    reference: bool = False  # "same as last year"-type reference (DL-20)
    reference_reason: str | None = None  # REFERENCE_AMBIGUOUS / BASELINE_SPEC_CHANGED / BASELINE_NOT_FOR_VENDOR
    reference_candidate: Decimal | None = None
    reference_confirmed: bool = False  # buyer recorded "prices" (or "both")
    baseline_freight_basis: str | None = None
    currency: str = "INR"


@dataclass
class ResponseContext:
    gst_statement: str = "SILENT"
    gst_stated_exclusive: bool | None = None
    rfx_gst_basis: str | None = None
    freight_terms: list[dict] = field(default_factory=list)
    discounts: list[dict] = field(default_factory=list)  # [{"pct": Decimal, "scope": "all" | {"ply": n}, "text": str}]
    fx_rates: dict = field(default_factory=dict)  # {"USD": {"rate": Decimal, "as_of": str, "source": str}}
    constants: ConstantSet = CONSTANT_SET_V1


@dataclass
class NormalizedCell:
    unit_price_inr_ex_gst: Decimal | None
    unit_status: ValueStatus
    reasons: list[str]
    flags: list[str]
    freight_basis: str
    freight_inr_per_box: Decimal | None
    landed_inr_ex_gst: Decimal | None
    landed_status: ValueStatus
    weight_source: str | None
    weight_g: Decimal | None
    constant_set_version: str
    auto_verify_candidate: bool
    trace: list[dict]
    engine_version: str = ENGINE_VERSION


def normalize_cell(line: dict, q: QuoteInput, ctx: ResponseContext) -> NormalizedCell:
    cs = ctx.constants
    trace: list[dict] = []
    reasons = list(q.verification_reasons)
    flags = list(q.flags)
    weight_source = weight_g = None
    price: Decimal | None = None

    basis, freight, fterm = freight_basis(ctx.freight_terms)
    trace.append({"step": "freight_basis", "basis": basis, "from_term": (fterm or {}).get("text"),
                  "label": "this year's response only; history never used"})
    if basis == "STATED" and fterm is not None and freight_currency(fterm) != "INR":
        cur = freight_currency(fterm)
        fx = ctx.fx_rates.get(cur)
        if fx is None:  # never add foreign-currency freight as rupees: landed is not calculable until a rate is set
            trace.append({"step": "freight_fx", "currency": cur, "amount": str(freight), "label": "no FX rate: landed not calculable"})
            freight = None
        else:
            trace.append({"step": "freight_fx", "currency": cur, "amount": str(freight), "rate": str(fx["rate"]),
                          "output": str(q4(freight * Decimal(str(fx["rate"]))))})
            freight = q4(freight * Decimal(str(fx["rate"])))

    if not q.quoted:
        return _done(line, None, [], flags, basis, freight, None, None, cs, False,
                     [{"step": "missing", "label": "not quoted"}] + trace, quoted=False)

    if q.reference and not (q.reference_confirmed and q.reference_candidate is not None
                            and (q.reference_reason or "REFERENCE_AMBIGUOUS") == "REFERENCE_AMBIGUOUS"):
        reasons.append(q.reference_reason or "REFERENCE_AMBIGUOUS")
        trace.append({"step": "reference", "label": "nothing applied before buyer confirmation (DL-20)",
                      "candidate": str(q.reference_candidate) if q.reference_candidate is not None else None,
                      "reason": q.reference_reason or "REFERENCE_AMBIGUOUS",
                      "baseline_freight_basis": q.baseline_freight_basis})
    elif q.reference:
        price = q.reference_candidate
        reasons.append("BASELINE_REFERENCE")
        trace.append({"step": "reference", "label": "buyer confirmed 'prices': vendor's own last-year price for the same spec (DL-8)",
                      "output": str(price)})
        if q.baseline_freight_basis == "INCLUDED" and basis != "INCLUDED":
            flags.append("FREIGHT_BASIS_CHANGED")
    else:
        value = q.value
        if q.slabs:
            idx, why = select_slab(q.slabs, line["annual_qty"])
            if why:
                reasons.append(why)
            else:
                value = slab_value(q.slabs[idx])
                trace.append({"step": "slab", "chosen": idx, "annual_qty": line["annual_qty"],
                              "slab": {k: q.slabs[idx].get(k) for k in ("min_qty", "max_qty")}, "output": str(value)})
        if value is not None:
            trace.insert(0, {"step": "as_quoted", "value": str(value), "unit_class": q.unit_class})
            if q.unit_class == "PER_KG":
                w = resolve_weight(line, cs, q.vendor_weight_g)
                reasons += w.reasons
                flags += w.flags
                trace += w.trace
                weight_source, weight_g = w.source, w.grams
                if w.grams is not None:
                    price = value * w.grams / Decimal(1000)
                    trace.append({"step": "weight_conversion", "op": "₹/kg × kg", "inputs": {"rate": str(value), "weight_g": str(w.grams)},
                                  "output": str(q4(price))})
            elif q.unit_class == "UNKNOWN":
                reasons.append("UNIT_UNKNOWN")
            else:
                price = to_per_box(value, q.unit_class)
                if price is not None and q.unit_class not in ("PER_BOX", "PER_SET"):
                    flags.append("CONVERTED")
                    trace.append({"step": "qty_conversion", "op": f"÷ {q.unit_class}", "output": str(q4(price))})
        if price is not None:
            for d in ctx.discounts:  # document-level discounts within scope, applied once each
                sc = d.get("scope", "all")
                if sc == "all" or (isinstance(sc, dict) and sc.get("ply") == line.get("ply")):
                    before = price
                    price = price * (1 - Decimal(str(d["pct"])) / 100)
                    trace.append({"step": "discount", "pct": str(d["pct"]), "scope": sc, "from_term": d.get("text"),
                                  "input": str(q4(before)), "output": str(q4(price))})
            if q.currency != "INR":
                fx = ctx.fx_rates.get(q.currency)
                if fx is None:
                    reasons.append("FX_RATE_MISSING")
                else:
                    original = price
                    price = price * Decimal(str(fx["rate"]))
                    reasons.append("FX_RATE")
                    flags.append("FX")
                    trace.append({"step": "fx", "currency": q.currency, "original": str(q4(original)), "rate": str(fx["rate"]),
                                  "as_of": fx.get("as_of"), "source": fx.get("source"), "output": str(q4(price))})

    greasons, gtrace = gst_reasons(ctx.gst_statement, ctx.rfx_gst_basis, ctx.gst_stated_exclusive)
    reasons += greasons
    trace.append(gtrace)

    blocking_present = status_from(reasons) in (ValueStatus.UNRESOLVED, ValueStatus.NOT_CONVERTIBLE)
    if blocking_present:
        if price is not None:
            trace.append({"step": "candidate", "label": "number not used: blocking reason present", "candidate": str(q4(price))})
        price = None
    unit_price = q4(price) if price is not None else None
    landed = None
    if unit_price is not None and basis in ("INCLUDED", "STATED", "ESTIMATED") and (basis == "INCLUDED" or freight is not None):
        landed = q4(unit_price + (freight or Decimal(0)))
    auto_ok = (not reasons and not q.image_sourced and "UNIT_DICT_UNSEEN" not in flags
               and not any(f in flags for f in ("ambiguous_unit", "illegible", "conflicting_values", "unclear_scope")))
    return _done(line, unit_price, sorted(set(reasons)), flags, basis, freight, landed, weight_source, cs, auto_ok,
                 trace, weight_g=weight_g, image=q.image_sourced)


def _done(line, unit_price, reasons, flags, basis, freight, landed, weight_source, cs, auto_ok, trace,
          quoted=True, weight_g=None, image=False) -> NormalizedCell:
    unit_status = status_from(reasons, quoted=quoted, cap_extracted=True)  # Phase A caps at EXTRACTED
    if unit_price is None and unit_status in (ValueStatus.EXTRACTED, ValueStatus.ASSUMED, ValueStatus.NEEDS_REVIEW):
        unit_status = ValueStatus.UNRESOLVED  # a status that implies a number must have one
        reasons = sorted(set(reasons) | {"EVIDENCE_NOT_FOUND"})
    if unit_status in (ValueStatus.MISSING, ValueStatus.NOT_CONVERTIBLE, ValueStatus.UNRESOLVED):
        landed_status = unit_status
    elif landed is None:
        landed_status = ValueStatus.NOT_CONVERTIBLE  # FREIGHT_UNKNOWN on the landed basis
    else:
        landed_status = unit_status
    return NormalizedCell(unit_price, unit_status, reasons, sorted(set(flags)), basis, freight, landed, landed_status,
                          weight_source, q4(weight_g) if weight_g is not None else None, cs.version,
                          auto_ok and not image, trace)
