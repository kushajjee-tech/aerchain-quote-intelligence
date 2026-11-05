"""Caveat engine (architecture §11.4; NLA-4): code-generated disclosures for every analyst answer. The
model never writes these; they are attached to the answer from the tool results and stored cells."""
from __future__ import annotations

from sqlalchemy import select

from app.db.models import NormalizedQuote, Response, RfxLine, Vendor
from app.domain.enums import ASSUMPTION_REASONS

INCLUDABLE = {"VERIFIED", "EXTRACTED", "ASSUMED"}


def _coverage(sf, rfx_id: int, vendor_ids: set[int]) -> list[str]:
    with sf() as s:
        lines = {l.id: l.line_no for l in s.scalars(select(RfxLine).where(RfxLine.rfx_id == rfx_id))}
        names = {v.id: v.name for v in s.scalars(select(Vendor))}
        responded = {r.vendor_id for r in s.scalars(select(Response).where(Response.rfx_id == rfx_id))}
        missing: dict[int, list[int]] = {}
        quoted: dict[int, int] = {}
        for q in s.scalars(select(NormalizedQuote).where(NormalizedQuote.rfx_line_id.in_(list(lines)))):
            if q.vendor_id not in vendor_ids:
                continue
            if q.unit_status == "MISSING":
                missing.setdefault(q.vendor_id, []).append(lines[q.rfx_line_id])
            else:
                quoted[q.vendor_id] = quoted.get(q.vendor_id, 0) + 1
    out = []
    for v in sorted(vendor_ids & responded):
        if missing.get(v):
            out.append(f"{names[v]}: {quoted.get(v, 0)}/{len(lines)}, missing lines {', '.join(map(str, sorted(missing[v])))}")
    return out


def scenario_caveats(sf, rfx_id: int, r: dict) -> dict:
    assumptions: dict[str, int] = {}
    for a in r["awards"]:
        for reason in a.get("reasons") or []:
            if reason in ASSUMPTION_REASONS:
                assumptions[reason] = assumptions.get(reason, 0) + 1
    with sf() as s:
        ids = {v.name: v.id for v in s.scalars(select(Vendor))}
    vendors_in = {a["vendor_id"] for a in r["awards"]} | {ids[e["vendor"]] for e in r["exclusions"] if e["vendor"] in ids}
    dep = r.get("freight_dependent_lines", [])
    sens = r.get("decision_sensitive_lines", [])
    return {
        "method": f"run_scenario: {r['params']['strategy']}, basis {r['basis']}, "
                  f"eligibility {r['params']['eligibility_scope']}/{r['params']['eligibility_mode']}, {r['label']} policy",
        "status_counts": r["caveats"]["status_counts"],
        "assumptions": assumptions,
        "mixed_freight_bases": r["caveats"]["mixed_freight_bases"] if len(r["caveats"]["mixed_freight_bases"]) > 1 else [],
        "alternates_included": [a["line_no"] for a in r["awards"] if "ALTERNATE" in (a.get("flags") or [])],
        "eligibility_excluded": {"failed": [x["vendor"] for x in r["ineligible_vendors"]["failed"]],
                                 "unverified": [x["vendor"] for x in r["ineligible_vendors"]["unverified"]]},
        "awaiting_response": r["awaiting_response"],
        "uncovered_lines": [u["line_no"] for u in r["uncovered_lines"]],
        "freight_dependent": [f"line {d['line_no']}: {d['vendor']} wins unless its freight exceeds ₹{d['break_even_inr_per_box']}/box"
                              for d in dep],
        "decision_sensitive_count": len(sens),
        "exposures": [x["statement"] for x in r["exposures"]["fx"]]
                     + ([r["exposures"]["billed_weight"]["statement"]] if r["exposures"]["billed_weight"]["statement"] else []),
        "coverage": _coverage(sf, rfx_id, vendors_in),
    }


def sql_caveats(sf, rfx_id: int, result: dict) -> dict:
    """Rows keyed by (line_no, vendor_id) are checked against stored cells; an excluded value in a result is flagged."""
    cols = result.get("columns", [])
    rows = result.get("rows", [])
    out = {"method": "query over approved views", "rows": len(rows), "truncated": len(rows) >= 1000}
    if rows and {"vendor_id", "unit_status"} <= set(cols):
        bad = [r for r in rows if r["unit_status"] not in INCLUDABLE and any(r.get(c) is not None for c in ("unit_price_inr", "landed_inr"))]
        if bad:
            out["excluded_value_appeared_in_result"] = [{"line_no": r.get("line_no"), "vendor_id": r["vendor_id"],
                                                         "status": r["unit_status"]} for r in bad]
        counts: dict[str, int] = {}
        for r in rows:
            counts[r["unit_status"]] = counts.get(r["unit_status"], 0) + 1
        out["status_counts"] = counts
    if rows and "vendor_id" in cols:
        out["coverage"] = _coverage(sf, rfx_id, {r["vendor_id"] for r in rows if r.get("vendor_id")})
    if rows and "evidence_ref" in cols:
        out["sources"] = sorted({r["evidence_ref"] for r in rows if r.get("evidence_ref")})
    return out
