"""₹/kg → ₹/box weight-source hierarchy (PRD §5.2; DL-1, DL-12, DL-18, DL-31).

1 documented SKU reference weight → ASSUMED (REFERENCE_WEIGHT)
2 vendor-stated weight              → CONVERTED (vendor's billing basis); cross-check vs reference
3 estimate from approximate constants (RSC / flat blank only, complete construction)
                                    → NEEDS_REVIEW (WEIGHT_ESTIMATED) + METHOD_CONSTANTS
4 otherwise                          → NOT_CONVERTIBLE (missing input / unsupported item type)
Constants never fill a missing input.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.normalize.constants import ConstantSet

M2 = Decimal(1_000_000)


@dataclass
class WeightResult:
    grams: Decimal | None
    source: str | None
    reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)


def construction_gaps(line: dict) -> list[str]:
    """Missing inputs for a weight *estimate* (RFX-3 completeness, I5)."""
    gaps = []
    layers, ply, flute = line.get("layers") or [], line.get("ply"), line.get("flute_profile") or ""
    mediums = [l for l in layers if l.get("role") == "medium"]
    if ply not in (3, 5, 7):
        gaps.append("ply")
    if len(layers) != ply:
        gaps.append("layers")
    if any(l.get("gsm") in (None, "") for l in layers):
        gaps.append("layer GSM")
    if len(flute) != len(mediums) or (ply in (3, 5, 7) and len(flute) != (ply - 1) // 2):
        gaps.append("flute profile")
    t = line["item_type"]
    if t == "RSC":
        dims = line.get("dims_mm") or {}
        gaps += [f"dimension {k}" for k in ("L", "W", "H") if not dims.get(k)]
    elif t in ("DIE_CUT", "PAD") and not line.get("blank_size_mm"):
        gaps.append("blank size")
    return gaps


def grammage(line: dict, cs: ConstantSet) -> tuple[Decimal, list[dict]]:
    g, cited = Decimal(0), []
    mediums = [l for l in line["layers"] if l["role"] == "medium"]
    for l in line["layers"]:
        if l["role"] == "liner":
            g += Decimal(str(l["gsm"]))
    for medium, flute in zip(mediums, line["flute_profile"]):  # mediums in layer order ↔ flute chars
        g += Decimal(str(medium["gsm"])) * cs.get(f"takeup.{flute}")
        cited.append(cs.cite(f"takeup.{flute}"))
    return g, cited


def estimate_grams(line: dict, cs: ConstantSet) -> tuple[Decimal, list[dict]]:
    g, cited = grammage(line, cs)
    if line["item_type"] == "RSC":
        L, W, H = (Decimal(str(line["dims_mm"][k])) for k in ("L", "W", "H"))
        joint = cs.get("rsc.joint_allowance_mm")
        cited.append(cs.cite("rsc.joint_allowance_mm"))
        area = (2 * L + 2 * W + joint) * (W + H) / M2
        note = "RSC blank from internal dimensions; excludes caliper allowance and trim; may understate weight"
    else:
        b = line["blank_size_mm"]
        area = Decimal(str(b["L"])) * Decimal(str(b["W"])) / M2
        note = "flat blank"
    grams = area * g  # m² × g/m²
    return grams, [{"step": "weight_estimate", "label": note, "inputs": {"area_m2": str(area), "grammage_gsm": str(g)},
                    "op": "area × grammage", "constants": cited, "output_g": str(grams)}]


def resolve_weight(line: dict, cs: ConstantSet, vendor_weight_g: Decimal | None = None) -> WeightResult:
    ref = line.get("reference_unit_weight_g")
    tol = cs.get("tol.weight_mismatch_pct") / 100
    if ref not in (None, ""):
        ref = Decimal(str(ref))
        r = WeightResult(ref, "SKU_REFERENCE", ["REFERENCE_WEIGHT"], ["BILLED_WEIGHT_RISK"],
                         [{"step": "weight", "label": "documented SKU reference weight (assumed: vendors invoice on actual weight)",
                           "source": line.get("reference_weight_source"), "output_g": str(ref)}])
        if vendor_weight_g is not None and abs(vendor_weight_g - ref) > ref * tol:
            r.reasons.append("WEIGHT_MISMATCH")
            r.trace.append({"step": "weight_cross_check", "vendor_g": str(vendor_weight_g), "reference_g": str(ref),
                            "constants": [cs.cite("tol.weight_mismatch_pct")]})
        return r
    if vendor_weight_g is not None:
        return WeightResult(vendor_weight_g, "VENDOR_STATED", [], ["CONVERTED", "BILLED_WEIGHT_RISK"],
                            [{"step": "weight", "label": "vendor-stated weight", "output_g": str(vendor_weight_g)}])
    if line["item_type"] not in ("RSC", "DIE_CUT", "PAD"):
        return WeightResult(None, None, ["ITEM_TYPE_NOT_WEIGHT_COMPUTABLE"],
                            trace=[{"step": "weight", "label": f"{line['item_type']}: weight is never estimated"}])
    gaps = construction_gaps(line)
    if gaps:
        return WeightResult(None, None, ["MISSING_CONSTRUCTION_INPUT"],
                            trace=[{"step": "weight", "label": "not convertible", "missing": gaps}])
    grams, trace = estimate_grams(line, cs)
    return WeightResult(grams, "ESTIMATED_CONSTANTS", ["WEIGHT_ESTIMATED", "METHOD_CONSTANTS"], ["BILLED_WEIGHT_RISK"], trace)
