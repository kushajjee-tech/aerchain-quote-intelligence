"""Draft award memo (M9a): rendered by template from a stored scenario result. No model call; every
number is copied from the scenario. AI rationale arrives in M9b."""
from __future__ import annotations

from decimal import Decimal


def inr(x) -> str:
    d = Decimal(str(x))
    s = f"{d:.2f}" if d != d.to_integral_value() else f"{int(d)}"
    whole, _, frac = s.partition(".")
    neg = whole.startswith("-")
    whole = whole.lstrip("-")
    if len(whole) > 3:  # Indian grouping: 12,34,56,789
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        whole = ",".join(([head] if head else []) + groups + [tail])
    return ("-" if neg else "") + "₹" + whole + (("." + frac) if frac else "")


def render_memo(title: str, scenario_id: int, r: dict, readiness: list[dict] | None = None,
                acknowledged: tuple[str, str] | None = None) -> str:
    p = r["params"]
    status = (f"ACKNOWLEDGED by {acknowledged[0]} on {acknowledged[1]}" if acknowledged else "DRAFT — not acknowledged")
    out = [f"# {'Award recommendation' if acknowledged else 'Draft award recommendation'} — {title}", "",
           f"*Scenario #{scenario_id} · {r.get('label', p['context'])} · strategy: {p['strategy']} · basis: {r['basis']} · "
           f"eligibility: {p.get('eligibility_scope', 'quality')}, {p.get('eligibility_mode', 'strict')}*",
           f"*Status: {status}. Values needing review are "
           + ("included under an audited override." if p["include_needs_review"] else "excluded (formal policy).") + "*", "",
           "## Recommendation", "",
           f"Total annual spend: **{inr(r['total_annual_spend_inr'])}** across {len(r['awards'])} awarded lines.", ""]
    share = r.get("per_vendor_share_pct", {})
    out += [f"- {v}: {inr(amt)}" + (f" ({share[v]}%)" if v in share else "") for v, amt in r["per_vendor_spend_inr"].items()]
    sv = r.get("savings") or {}
    if sv:
        ly, bs = sv["vs_last_year"], sv["vs_best_single_vendor"]
        out += ["", "## Savings", "",
                f"- vs last year: {inr(ly['savings_inr'])}" + (f" ({ly['savings_pct']}%)" if ly["savings_pct"] else "")
                + f", {ly['statement']}."]
        if ly["lines_without_comparable_baseline"]:
            out.append(f"  - No comparable baseline: lines {', '.join(map(str, ly['lines_without_comparable_baseline']))}.")
        if ly["bound_note"]:
            out.append(f"  - {ly['bound_note']}.")
        if ly["freight_basis_caveat_lines"]:
            out.append(f"  - Freight basis differs from last year on lines {', '.join(map(str, ly['freight_basis_caveat_lines']))}.")
        if bs:
            out.append(f"- vs best single vendor: {inr(bs['savings_inr'])}, {bs['statement']}"
                       + (f"; not covered: lines {', '.join(map(str, bs['lines_not_covered']))}" if bs["lines_not_covered"] else "") + ".")
    out += ["", "## Line awards", "", "| Line | SKU | Vendor | ₹/box (basis) | Status | Annual qty | Annual spend | Freight |",
            "|---|---|---|---|---|---|---|---|"]
    for a in r["awards"]:
        fr = a["freight_basis"] + (f" · FREIGHT_DEPENDENT (break-even ₹{a['break_even_inr_per_box']}/box)"
                                   if a.get("freight_status") == "FREIGHT_DEPENDENT" else "")
        out.append(f"| {a['line_no']} | {a['sku']} | {a['vendor']} | {inr(a.get('price_on_basis_inr') or a['unit_price_inr_ex_gst'])} | "
                   f"{a['status']} | {a['annual_qty']:,} | {inr(a['annual_spend_inr'])} | {fr} |")
    alts = [a for a in r["awards"] if "ALTERNATE" in (a.get("flags") or [])]
    if p.get("include_alternates") and alts:  # AWD-5
        out += ["", "## Alternates included", ""]
        out += [f"- Line {a['line_no']} ({a['vendor']}): " + "; ".join(
            f"{d['field']} {d['rfx']} → {d['vendor']}" for d in (a.get("spec_differences") or [])) for a in alts]
    out += ["", "## Not awarded", ""]
    out += [f"- Line {u['line_no']} ({u['sku']}): no includable quote." for u in r["uncovered_lines"]] or ["- None."]
    if r["awaiting_response"]:
        out += ["", f"Awaiting response (not considered): {', '.join(r['awaiting_response'])}."]
    inel = r.get("ineligible_vendors") or {}
    if inel.get("failed") or inel.get("unverified"):
        out += ["", "## Eligibility", ""]
        out += [f"- Failed: {x['vendor']} — {'; '.join(x['reasons'])}" for x in inel.get("failed", [])]
        out += [f"- Unverified (not Failed): {x['vendor']} — {'; '.join(x['reasons'])}" for x in inel.get("unverified", [])]
    out += ["", "## Exclusions", ""]
    out += [f"- Line {e['line_no']}, {e['vendor']}: {e['reason']}" + (f" ({e['detail']})" if e.get("detail") else "")
            for e in r["exclusions"]] or ["- None."]
    if r.get("decision_sensitive_lines"):
        out += ["", "## Decision-sensitive lines", ""]
        out += [f"- Line {d['line_no']}: " + "; ".join(i["detail"] for i in d["inputs"]) for d in r["decision_sensitive_lines"]]
    ex = r.get("exposures") or {}
    if ex.get("fx") or (ex.get("billed_weight") or {}).get("statement"):
        out += ["", "## Exposures", ""]
        out += [f"- {x['statement']}." for x in ex.get("fx", [])]
        if ex["billed_weight"]["statement"]:
            out.append(f"- {ex['billed_weight']['statement']}.")
    if readiness:
        out += ["", "## Readiness items" + (" (acknowledged)" if acknowledged else " (to acknowledge)"), ""]
        out += [f"- {i['kind']}" for i in readiness]
    cav = r["caveats"]
    out += ["", "## Caveats", "",
            f"- Status of awarded cells: " + ", ".join(f"{k} {v}" for k, v in sorted(cav["status_counts"].items())),
            f"- Freight unknown on awarded lines: {', '.join(map(str, cav['freight_unknown_lines'])) or 'none'}.",
            f"- Tie-break: {r.get('tie_break', 'lower price, then lower vendor id')}.",
            f"- {cav['note']}", ""]
    return "\n".join(out)
