"""Tables and charts for analyst answers (NLA-2, FN-13/14, SC-09). A chart spec never carries data: the
binder injects the referenced tool-result rows value for value, and rejects any spec that names a field
the result does not have or tries to supply its own values. Rows without a number are omitted and listed,
never drawn as zero. A point whose row status is not includable (e.g. NEEDS_REVIEW) keeps that status so the
chart marks it (EVAL-02)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

SCENARIO_COLUMNS = ["line_no", "sku", "vendor_id", "vendor", "price_on_basis_inr", "status", "annual_qty",
                    "annual_spend_inr", "freight_basis", "freight_status", "break_even_inr_per_box"]
CHART_TYPES = ("bar", "grouped_bar", "line")


class ChartRejected(ValueError):
    pass


def table_of(tool: str, result: dict) -> dict | None:
    if tool == "query":
        return {"columns": result["columns"], "rows": result["rows"], "source": "query", "sql": result.get("sql")}
    if tool == "run_scenario":
        return {"columns": SCENARIO_COLUMNS, "rows": [{c: a.get(c) for c in SCENARIO_COLUMNS} for a in result["awards"]],
                "source": "run_scenario"}
    return None


def _num(v) -> bool:
    if v is None or isinstance(v, bool):
        return False
    try:
        Decimal(str(v))
        return True
    except InvalidOperation:
        return False


def bind_chart(spec: dict, table: dict, table_index: int) -> dict:
    allowed = {"result_index", "type", "x", "y", "series", "title"}
    extra = set(spec) - allowed
    if extra:
        raise ChartRejected(f"chart spec may not contain {sorted(extra)}: data comes only from the tool result")
    if spec.get("type") not in CHART_TYPES:
        raise ChartRejected(f"type must be one of {CHART_TYPES}")
    cols = set(table["columns"])
    for f in ("x", "y") + (("series",) if spec.get("series") else ()):
        if spec.get(f) not in cols:
            raise ChartRejected(f"field '{spec.get(f)}' is not a column of result {table_index}")
    points, omitted = [], []
    for i, r in enumerate(table["rows"]):
        if not _num(r.get(spec["y"])):
            omitted.append({"row": i, "x": r.get(spec["x"]), "reason": "no number (excluded status or missing)"})
            continue
        st = r.get("unit_status", r.get("landed_status", r.get("status")))
        points.append({"x": r.get(spec["x"]), "y": r[spec["y"]], **({"series": r.get(spec["series"])} if spec.get("series") else {}),
                       **({"status": st} if st is not None else {})})
    if not points:
        raise ChartRejected("no numeric values to plot")
    flagged = [p for p in points if p.get("status") and p["status"] not in ("VERIFIED", "EXTRACTED", "ASSUMED")]
    return {"type": spec["type"], "flagged_points": len(flagged), "title": spec.get("title") or "", "x": spec["x"], "y": spec["y"],
            "series": spec.get("series"), "result_index": table_index, "data": points, "omitted": omitted}
