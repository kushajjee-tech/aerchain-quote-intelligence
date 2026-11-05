"""Scenario engine (AWD-1/2, PRD §5.4, §5.9; DL-6, DL-16, DL-25, DL-28, DL-29, DL-30, DL-31).

Deterministic: identical inputs → identical output. Per line, candidates are cells that pass
  request exclusions ∧ strategy ∧ alternates toggle ∧ vendor eligibility (scope, mode) ∧ line-level
  food-grade/FSC gating ∧ the canonical inclusion policy ∧ availability on the basis.
Basis `freight_aware` (formal default) decides on landed cost where calculable; an UNKNOWN-freight
candidate competes on its unit price as a lower bound and, if it wins only that way, the line is
FREIGHT_DEPENDENT with break-even = best_K − best_U. Tie-break (disclosed): lower price, then
eligibility Pass over Unverified, then VERIFIED over other statuses, then lower vendor id.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import EligibilityResult, Invitation, NormalizedQuote, Question, Response, RfxLine, Vendor
from app.domain.enums import ValueStatus as S
from app.eligibility.rules import FAIL, LINE_FLAG, NA, PASS, UNVERIFIED, QResult, label, line_gate, roll_up
from app.normalize.money import line_total, q4
from app.validate.status import Policy, includable

TIE_BREAK = "lower price → eligibility Passed over Unverified → VERIFIED over other statuses → lower vendor id"
BASES = ("freight_aware", "unit", "landed")


@dataclass
class ScenarioParams:
    strategy: str = "cheapest_per_line"  # or single_vendor
    vendor_id: int | None = None  # for single_vendor
    context: str = "formal"
    include_needs_review: bool = False
    override_id: int | None = None
    exclude_vendor_ids: list[int] = field(default_factory=list)
    line_nos: list[int] | None = None
    basis: str | None = None  # default: freight_aware (formal) / unit (exploratory)
    eligibility_mode: str = "strict"  # strict / inclusive / none
    eligibility_scope: str = "quality"  # quality / all_mandatory
    include_alternates: bool = False

    def __post_init__(self):
        if self.basis is None:
            self.basis = "freight_aware" if self.context == "formal" else "unit"
        if self.basis not in BASES:
            raise ValueError(f"basis must be one of {BASES}")
        if self.strategy not in ("cheapest_per_line", "single_vendor"):
            raise ValueError("strategy must be cheapest_per_line or single_vendor")
        if self.strategy == "single_vendor" and self.vendor_id is None:
            raise ValueError("single_vendor needs vendor_id")
        if self.eligibility_mode not in ("strict", "inclusive", "none"):
            raise ValueError("eligibility_mode must be strict, inclusive or none")
        if self.eligibility_scope not in ("quality", "all_mandatory"):
            raise ValueError("eligibility_scope must be quality or all_mandatory")


def cell_fingerprint(q: NormalizedQuote) -> str:
    raw = [q.unit_price_inr_ex_gst, q.unit_status, q.unit_reasons, q.landed_inr_ex_gst, q.landed_status,
           q.freight_basis, q.freight_inr_per_box, q.flags]
    return hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()[:16]


# --- eligibility --------------------------------------------------------------------------------
def vendor_eligibility(s: Session, rfx_id: int, vendor_ids: list[int], scope: str) -> dict[int, dict]:
    qs = list(s.scalars(select(Question).where(Question.rfx_id == rfx_id)))
    if not qs:
        return {v: {"state": PASS, "reasons": [], "results": [], "configured": False} for v in vendor_ids}
    by_id = {q.id: q for q in qs}
    out = {}
    for v in vendor_ids:
        rows = {r.question_id: r for r in s.scalars(select(EligibilityResult).where(EligibilityResult.vendor_id == v,
                                                                                    EligibilityResult.question_id.in_(list(by_id))))}
        results = []
        for q in qs:
            if not q.mandatory:
                continue
            r = rows.get(q.id)
            results.append(QResult(q.requirement_key, q.section, r.state if r else UNVERIFIED,
                                   r.reason if r else "no answer on record", LINE_FLAG.get(q.applicability)))
        state, why = roll_up(results, "QUALITY" if scope == "quality" else None)
        out[v] = {"state": state, "reasons": [f"{r.key}: {r.reason}" for r in why], "results": results, "configured": True}
    return out


def _elig_rank(state: str) -> int:
    return 0 if state == PASS else 1


# --- per-line selection -------------------------------------------------------------------------
def _pick(cands: list[dict]) -> dict | None:
    return min(cands, key=lambda c: (c["price"], c["elig_rank"], 0 if c["status"] == S.VERIFIED else 1, c["vendor_id"]),
               default=None)


def _select(cands: list[dict], basis: str) -> tuple[dict | None, dict]:
    """Returns (winner, freight info) per PRD §5.4."""
    if basis != "freight_aware":
        return _pick(cands), {"freight_status": None}
    K = [c for c in cands if c["kind"] == "K"]
    U = [c for c in cands if c["kind"] == "U"]
    bk, bu = _pick(K), _pick(U)
    if bk and (bu is None or bk["price"] <= bu["price"]):
        return bk, {"freight_status": "ROBUST" if bu else "LANDED"}
    if bu and bk is None:
        return bu, {"freight_status": "FREIGHT_UNKNOWN_ALL"}
    if bu is None:
        return None, {"freight_status": None}
    return bu, {"freight_status": "FREIGHT_DEPENDENT", "break_even_inr_per_box": str(q4(bk["price"] - bu["price"])),
                "against_vendor_id": bk["vendor_id"]}


def _basis_price(q: NormalizedQuote, basis: str, unit_value: Decimal | None = None) -> tuple[Decimal | None, str | None]:
    """Price of a cell on the basis, and its kind (K = landed known, U = unit as lower bound)."""
    unit = unit_value if unit_value is not None else (Decimal(q.unit_price_inr_ex_gst) if q.unit_price_inr_ex_gst else None)
    if unit is None:
        return None, None
    freight = Decimal(q.freight_inr_per_box) if q.freight_inr_per_box else Decimal(0)
    known = q.freight_basis == "INCLUDED" or (q.freight_basis in ("STATED", "ESTIMATED") and q.freight_inr_per_box is not None)
    if basis == "unit":
        return unit, "unit"
    if basis == "landed":
        return (q4(unit + freight), "K") if known else (None, None)
    return (q4(unit + freight), "K") if known else (unit, "U")


def _candidate_value(q: NormalizedQuote) -> tuple[Decimal | None, str]:
    """An uncertain cell's alternative value: unit suggestion, else the withheld candidate (DL-28 (a)/(b))."""
    if q.unit_price_inr_ex_gst:
        return Decimal(q.unit_price_inr_ex_gst), "needs-review value"
    sug = next((t.get("suggestion") for t in q.trace or [] if t.get("suggestion")), None)
    if sug:
        return Decimal(sug["suggested_unit_price"]), f"unit suggestion ÷{sug['divide_by']}"
    cand = next((t.get("candidate") for t in reversed(q.trace or []) if t.get("candidate")), None)
    return (Decimal(cand), "withheld candidate") if cand else (None, "")


def run_scenario(sf: sessionmaker[Session], rfx_id: int, p: ScenarioParams, baseline: dict[int, dict] | None = None) -> dict:
    """baseline: {line_no: {"unit_price_inr_ex_gst": str, "freight_basis": str}} (awarded rows, §5.9)."""
    policy = Policy(p.context, p.include_needs_review)
    baseline = baseline or {}
    with sf() as s:
        lines = list(s.scalars(select(RfxLine).where(RfxLine.rfx_id == rfx_id).order_by(RfxLine.line_no)))
        vendors = {v.id: v.name for v in s.scalars(select(Vendor))}
        invited = [i.vendor_id for i in s.scalars(select(Invitation).where(Invitation.rfx_id == rfx_id))]
        responded = {r.vendor_id: r for r in s.scalars(select(Response).where(Response.rfx_id == rfx_id))}
        quotes = list(s.scalars(select(NormalizedQuote).where(NormalizedQuote.rfx_line_id.in_([l.id for l in lines]))))
        elig = vendor_eligibility(s, rfx_id, sorted(responded), p.eligibility_scope)
        for q in quotes:
            s.expunge(q)
    by_line: dict[int, list[NormalizedQuote]] = {}
    for q in quotes:
        by_line.setdefault(q.rfx_line_id, []).append(q)
    awaiting = sorted(v for v in invited if v not in responded)

    # vendor-level eligibility (Failed and Unverified listed separately, DL-3)
    allowed_states = {"strict": {PASS}, "inclusive": {PASS, UNVERIFIED}, "none": {PASS, FAIL, UNVERIFIED}}[p.eligibility_mode]
    ineligible = {"failed": [], "unverified": []}
    for v in sorted(responded):
        e = elig[v]
        if e["state"] not in allowed_states:
            ineligible["failed" if e["state"] == FAIL else "unverified"].append(
                {"vendor_id": v, "vendor": vendors[v], "state": label(e["state"]), "reasons": e["reasons"]})

    awards, uncovered, exclusions, cells_used, line_info = [], [], [], [], []
    nr_cells, per_line_cands = [], {}
    for l in lines:
        if p.line_nos and l.line_no not in p.line_nos:
            continue
        cands, uncertain = [], []
        flags_needed = [f for f in ("food_contact", "requires_fsc") if getattr(l, f, False)]
        for q in sorted(by_line.get(l.id, []), key=lambda q: q.vendor_id):
            v = q.vendor_id
            why = None
            if v in p.exclude_vendor_ids:
                why = {"reason": "excluded by request"}
            elif "ALTERNATE" in (q.flags or []) and not p.include_alternates:
                why = {"reason": "alternate spec (DL-6)"}
            elif p.eligibility_mode != "none" and elig[v]["state"] not in allowed_states:
                why = {"reason": f"eligibility {label(elig[v]['state'])} ({p.eligibility_scope}, {p.eligibility_mode})"}
            elif p.eligibility_mode != "none" and any(not line_gate(elig[v]["results"], f, p.eligibility_mode) for f in flags_needed):
                why = {"reason": "line-level food-grade/FSC requirement not met (DL-29)"}
            if why:
                exclusions.append({"line_no": l.line_no, "vendor": vendors[v], **why})
                continue
            st = S(q.unit_status)
            if not includable(st, policy, p.override_id):
                exclusions.append({"line_no": l.line_no, "vendor": vendors[v], "reason": st.value,
                                   "detail": ", ".join(q.unit_reasons or [])})
                cv, how = _candidate_value(q)
                if cv is not None and st in (S.UNRESOLVED, S.NEEDS_REVIEW):
                    uncertain.append((q, cv, how))
                continue
            price, kind = _basis_price(q, p.basis)
            if price is None:
                exclusions.append({"line_no": l.line_no, "vendor": vendors[v], "reason": "landed cost not calculable",
                                   "detail": f"freight {q.freight_basis}"})
                continue
            if st == S.NEEDS_REVIEW:
                nr_cells.append({"line_no": l.line_no, "vendor": vendors[v], "value": str(price),
                                 "money_at_risk_inr": str(line_total(price, l.annual_qty))})
            cands.append({"vendor_id": v, "price": price, "kind": kind, "status": st,
                          "elig_rank": _elig_rank(elig[v]["state"]), "q": q})
        per_line_cands[l.line_no] = cands
        pool = [c for c in cands if p.strategy != "single_vendor" or c["vendor_id"] == p.vendor_id]
        win, finfo = _select(pool, p.basis)
        sens = _sensitivity(l, pool, win, finfo, uncertain, p, elig, vendors)
        line_info.append({"line_no": l.line_no, **finfo, "sensitivity": sens})
        if win is None:
            uncovered.append({"line_no": l.line_no, "sku": l.sku_code})
            continue
        q = win["q"]
        awards.append({"line_no": l.line_no, "sku": l.sku_code, "vendor_id": q.vendor_id, "vendor": vendors[q.vendor_id],
                       "unit_price_inr_ex_gst": q.unit_price_inr_ex_gst, "price_on_basis_inr": str(win["price"]),
                       "price_kind": {"K": "landed", "U": "unit (freight unknown: lower bound)", "unit": "unit"}[win["kind"]],
                       "status": q.unit_status, "annual_qty": l.annual_qty,
                       "annual_spend_inr": str(line_total(win["price"], l.annual_qty)), "freight_basis": q.freight_basis,
                       "freight_status": finfo["freight_status"], "break_even_inr_per_box": finfo.get("break_even_inr_per_box"),
                       "flags": q.flags, "reasons": q.unit_reasons, "weight_source": q.weight_source,
                       "spec_differences": next((t.get("differences") for t in q.trace or [] if t.get("step") == "spec_diff"
                                                 and t.get("verdict") == "ALTERNATE"), None),
                       "eligibility": label(elig[q.vendor_id]["state"])})
        cells_used.append({"line_no": l.line_no, "vendor_id": q.vendor_id, "status": q.unit_status,
                           "fingerprint": cell_fingerprint(q)})

    per_vendor: dict[str, Decimal] = {}
    for a in awards:
        per_vendor[a["vendor"]] = per_vendor.get(a["vendor"], Decimal(0)) + Decimal(a["annual_spend_inr"])
    total = sum(per_vendor.values(), Decimal(0))
    status_counts: dict[str, int] = {}
    for c in cells_used:
        status_counts[c["status"]] = status_counts.get(c["status"], 0) + 1
    dependent = [{"line_no": i["line_no"], "break_even_inr_per_box": i["break_even_inr_per_box"],
                  "vendor": next(a["vendor"] for a in awards if a["line_no"] == i["line_no"]),
                  "against": vendors[i["against_vendor_id"]]}
                 for i in line_info if i.get("freight_status") == "FREIGHT_DEPENDENT"]
    sensitive = [{"line_no": i["line_no"], **i["sensitivity"]} for i in line_info if i["sensitivity"]["sensitive"]]
    coverage = []
    for v in sorted(responded):
        cnt = responded[v].coverage_count
        if cnt is not None and cnt < len(lines):
            coverage.append(f"{vendors[v]}: {cnt}/{len(lines)} lines quoted")
    return {
        "params": asdict(p), "basis": p.basis, "label": "Exploratory" if p.context == "exploratory" else "Formal",
        "tie_break": TIE_BREAK,
        "awards": awards, "uncovered_lines": uncovered,
        "per_vendor_spend_inr": {k: str(v) for k, v in sorted(per_vendor.items())},
        "per_vendor_share_pct": {k: str((v / total * 100).quantize(Decimal("0.1"))) if total else "0"
                                 for k, v in sorted(per_vendor.items())},
        "total_annual_spend_inr": str(total),
        "exclusions": exclusions, "ineligible_vendors": ineligible,
        "awaiting_response": [vendors[v] for v in awaiting],
        "needs_review_cells_included": nr_cells,
        "freight_dependent_lines": dependent,
        "decision_sensitive_lines": sensitive,
        "savings": _savings(awards, lines, baseline, per_line_cands, p, vendors, total),
        "exposures": _exposures(awards),
        "caveats": {"status_counts": status_counts,
                    "freight_unknown_lines": [a["line_no"] for a in awards if a["freight_basis"] == "UNKNOWN"],
                    "mixed_freight_bases": sorted({a["freight_basis"] for a in awards}),
                    "coverage": coverage,
                    "eligibility": ("no questionnaire on this RFx" if not any(e["configured"] for e in elig.values())
                                    else f"scope {p.eligibility_scope}, mode {p.eligibility_mode}"),
                    "note": ("freight-aware: landed cost where calculable; unknown-freight cells compete on unit price as a lower bound"
                             if p.basis == "freight_aware" else f"{p.basis} basis")},
        "cells_used": cells_used,
    }


# --- decision sensitivity (DL-28) ---------------------------------------------------------------
def _sensitivity(l, pool, win, finfo, uncertain, p, elig, vendors) -> dict:
    inputs = []
    if finfo.get("freight_status") == "FREIGHT_DEPENDENT":
        inputs.append({"kind": "UNKNOWN_FREIGHT", "vendor": vendors[win["vendor_id"]],
                       "break_even_inr_per_box": finfo["break_even_inr_per_box"],
                       "detail": f"{vendors[win['vendor_id']]} wins unless its freight exceeds ₹{finfo['break_even_inr_per_box']}/box"})
    for q, cv, how in uncertain:  # (a) UNRESOLVED candidates, (b) excluded NEEDS_REVIEW values
        if p.strategy == "single_vendor" and q.vendor_id != p.vendor_id:
            continue
        price, kind = _basis_price(q, p.basis, unit_value=cv)
        if price is None:
            continue
        alt = {"vendor_id": q.vendor_id, "price": price, "kind": kind, "status": S(q.unit_status),
               "elig_rank": _elig_rank(elig[q.vendor_id]["state"]), "q": q}
        new_win, _ = _select(pool + [alt], p.basis)
        if new_win is not None and (win is None or new_win["vendor_id"] != win["vendor_id"]):
            delta = line_total(win["price"], l.annual_qty) - line_total(price, l.annual_qty) if win else line_total(price, l.annual_qty)
            inputs.append({"kind": "UNRESOLVED_CANDIDATE" if q.unit_status == "UNRESOLVED" else "EXCLUDED_NEEDS_REVIEW",
                           "vendor": vendors[q.vendor_id], "value": str(price), "how": how,
                           "annual_inr_delta": str(delta),
                           "detail": (f"if {vendors[q.vendor_id]}'s {how} (₹{price}/box) stands, it wins"
                                      + (f", saving ₹{delta}/yr" if win else " and covers this line"))})
    if win is not None and len(pool) >= 2:  # (c) ASSUMED FX / reference-weight on a candidate
        ranked = sorted(pool, key=lambda c: (c["price"], c["vendor_id"]))
        for c in pool:
            r = set(c["q"].unit_reasons or [])
            if c["status"] == S.ASSUMED and r & {"FX_RATE", "REFERENCE_WEIGHT"}:
                if c is win:
                    other = next(x for x in ranked if x is not c)
                    margin = (other["price"] / c["price"] - 1) * 100
                else:
                    margin = (1 - win["price"] / c["price"]) * 100
                inputs.append({"kind": "ASSUMED_" + ("FX" if "FX_RATE" in r else "WEIGHT"), "vendor": vendors[c["vendor_id"]],
                               "flip_margin_pct": str(margin.quantize(Decimal("0.01"))),
                               "detail": f"a {abs(margin.quantize(Decimal('0.01')))}% "
                                         f"{'rise' if c is win else 'fall'} in {vendors[c['vendor_id']]}'s price from its assumed "
                                         f"{'exchange rate' if 'FX_RATE' in r else 'reference weight'} changes the winner"})
    return {"sensitive": bool(inputs), "inputs": inputs}


def _inr(x) -> str:
    from app.award.memo import inr
    return inr(x)


# --- savings (§5.9) -----------------------------------------------------------------------------
def _savings(awards, lines, baseline, per_line_cands, p, vendors, total) -> dict:
    qty = {l.line_no: l.annual_qty for l in lines}
    A = {a["line_no"]: a for a in awards}
    comparable, no_base, caveat_lines = [], [], []
    for n, a in A.items():
        b = baseline.get(n)
        if b is None or (p.basis in ("landed", "freight_aware") and b.get("freight_basis") not in ("INCLUDED",)):
            no_base.append(n)
            continue
        comparable.append(n)
        if "FREIGHT_BASIS_CHANGED" in (a["flags"] or []) or (p.basis == "unit" and a["freight_basis"] != b.get("freight_basis")):
            caveat_lines.append(n)
    base_spend = sum((line_total(Decimal(baseline[n]["unit_price_inr_ex_gst"]), qty[n]) for n in comparable), Decimal(0))
    awarded_on_b = sum((Decimal(A[n]["annual_spend_inr"]) for n in comparable), Decimal(0))
    dep = [n for n in comparable if A[n]["freight_status"] == "FREIGHT_DEPENDENT" or A[n]["price_kind"].startswith("unit (")]
    vs_last = {
        "lines": len(comparable), "of_awarded": len(A), "baseline_spend_inr": str(base_spend),
        "scenario_spend_on_lines_inr": str(awarded_on_b), "savings_inr": str(base_spend - awarded_on_b),
        "savings_pct": str(((base_spend - awarded_on_b) / base_spend * 100).quantize(Decimal("0.01"))) if base_spend else None,
        "statement": (f"on {len(comparable)} of {len(A)} awarded lines, covering {_inr(awarded_on_b)} "
                      f"({(awarded_on_b / total * 100).quantize(Decimal('0.1')) if total else 0}%) of scenario spend"),
        "lines_without_comparable_baseline": sorted(no_base), "freight_basis_caveat_lines": sorted(caveat_lines),
        "freight_unknown_lines": sorted(dep),
        "bound_note": (f"{len(dep)} line(s) are priced without freight (unknown): their spend is a lower bound, "
                       "so savings on them are at most the figure shown" if dep else None)}
    # vs best single vendor: same filters; comparator = max coverage, then lowest total, then lower id
    cover: dict[int, dict[int, Decimal]] = {}
    for n in A:
        for c in per_line_cands.get(n, []):
            cover.setdefault(c["vendor_id"], {})[n] = c["price"]
    best = None
    for v, per in cover.items():
        tot = sum((line_total(pr, qty[n]) for n, pr in per.items()), Decimal(0))
        key = (-len(per), tot, v)
        if best is None or key < best[0]:
            best = (key, v, per, tot)
    vs_single = None
    if best:
        _, v, per, tot = best
        awarded_on_c = sum((Decimal(A[n]["annual_spend_inr"]) for n in per), Decimal(0))
        vs_single = {"vendor": vendors[v], "lines": len(per), "of_awarded": len(A), "vendor_spend_inr": str(tot),
                     "savings_inr": str(tot - awarded_on_c),
                     "statement": f"vs {vendors[v]} on the {len(per)} of {len(A)} awarded lines {vendors[v]} covers",
                     "lines_not_covered": sorted(n for n in A if n not in per)}
    return {"vs_last_year": vs_last, "vs_best_single_vendor": vs_single}


# --- exposures (DL-30/31) -----------------------------------------------------------------------
def _exposures(awards) -> dict:
    fx: dict[str, Decimal] = {}
    for a in awards:
        if "FX" in (a["flags"] or []):
            fx[a["vendor"]] = fx.get(a["vendor"], Decimal(0)) + Decimal(a["annual_spend_inr"])
    kg = [a for a in awards if a["weight_source"]]
    kg_spend = sum((Decimal(a["annual_spend_inr"]) for a in kg), Decimal(0))
    return {
        "fx": [{"vendor": v, "awarded_spend_inr": str(s), "per_1pct_inr": str((s / 100).quantize(Decimal(1))),
                "statement": f"each 1% USD/INR move changes {v}-awarded spend by ₹{(s / 100).quantize(Decimal(1))}"}
               for v, s in sorted(fx.items())],
        "billed_weight": {"lines": [a["line_no"] for a in kg], "awarded_spend_inr": str(kg_spend),
                          "per_1pct_inr": str((kg_spend / 100).quantize(Decimal(1))),
                          "statement": (f"billed-weight exposure: ₹{(kg_spend / 100).quantize(Decimal(1))} per 1% weight variance "
                                        f"across {len(kg)} per-kg lines") if kg else None},
    }


# --- readiness (AWD-3) --------------------------------------------------------------------------
def readiness_items(sf, rfx_id: int, result: dict) -> list[dict]:
    items = []
    p = result["params"]
    if p["include_needs_review"] and result["needs_review_cells_included"]:
        items.append({"kind": "NEEDS_REVIEW_OVERRIDE", "override_id": p["override_id"], "cells": result["needs_review_cells_included"]})
    if result["awaiting_response"]:
        items.append({"kind": "AWAITING_RESPONSE", "vendors": result["awaiting_response"]})
    with sf() as s:
        line_ids = {l.id: l.line_no for l in s.scalars(select(RfxLine).where(RfxLine.rfx_id == rfx_id))}
        names = {v.id: v.name for v in s.scalars(select(Vendor))}
        ref = [{"line_no": line_ids[q.rfx_line_id], "vendor": names[q.vendor_id]}
               for q in s.scalars(select(NormalizedQuote).where(NormalizedQuote.rfx_line_id.in_(list(line_ids))))
               if "REFERENCE_AMBIGUOUS" in (q.unit_reasons or [])]
    if ref:
        items.append({"kind": "REFERENCE_AMBIGUOUS", "cells": sorted(ref, key=lambda r: (r["vendor"], r["line_no"]))})
    if result["freight_dependent_lines"]:
        items.append({"kind": "FREIGHT_DEPENDENT", "lines": result["freight_dependent_lines"]})
    if result["decision_sensitive_lines"]:
        items.append({"kind": "DECISION_SENSITIVE", "lines": result["decision_sensitive_lines"]})
    if result["exposures"]["fx"]:
        items.append({"kind": "FX_EXPOSURE", "exposures": result["exposures"]["fx"]})
    if result["exposures"]["billed_weight"]["lines"]:
        items.append({"kind": "BILLED_WEIGHT_EXPOSURE", **result["exposures"]["billed_weight"]})
    warn = [a["line_no"] for a in result["awards"] if "NEW_WARNING_AFTER_REVIEW" in (a["flags"] or [])]
    if warn:
        items.append({"kind": "NEW_WARNING_AFTER_REVIEW", "lines": warn})
    return items
