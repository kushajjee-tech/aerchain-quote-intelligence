"""IA-04/IA-05: analyst tables and charts (FN-13/14, NLA-2, SC-09). Chart data equals the tool-result rows
value for value; specs cannot carry their own data or name fields the result lacks; rows without a number
are omitted and listed, never plotted as zero."""
import io

import pytest
from openpyxl import load_workbook

from app.analysis.charts import ChartRejected, bind_chart, table_of
from tests.test_analyst_m8a import text, tool
from tests.test_analyst_m8b import _analyst
from tests.test_review_m5b import processed  # noqa: F401

TABLE = {"columns": ["vendor", "line_no", "unit_price_inr", "unit_status"],
         "rows": [{"vendor": "A", "line_no": 1, "unit_price_inr": "10.0000", "unit_status": "VERIFIED"},
                  {"vendor": "B", "line_no": 1, "unit_price_inr": None, "unit_status": "UNRESOLVED"},
                  {"vendor": "B", "line_no": 2, "unit_price_inr": "9.5000", "unit_status": "ASSUMED"}]}
SPEC = {"result_index": 0, "type": "grouped_bar", "x": "line_no", "y": "unit_price_inr", "series": "vendor", "title": "t"}


def test_binder_injects_rows_and_omits_non_numbers():
    c = bind_chart(SPEC, TABLE, 0)
    assert c["data"] == [{"x": 1, "y": "10.0000", "series": "A", "status": "VERIFIED"},
                         {"x": 2, "y": "9.5000", "series": "B", "status": "ASSUMED"}]
    nr = bind_chart(SPEC, {**TABLE, "rows": TABLE["rows"] + [{"vendor": "C", "line_no": 3, "unit_price_inr": "5.0000",
                                                             "unit_status": "NEEDS_REVIEW"}]}, 0)
    assert nr["flagged_points"] == 1 and nr["data"][-1]["status"] == "NEEDS_REVIEW"  # marked, never passed off as normal
    assert c["omitted"] == [{"row": 1, "x": 1, "reason": "no number (excluded status or missing)"}]


@pytest.mark.parametrize("bad", [
    dict(SPEC, data=[{"x": 1, "y": 99}]),          # inline values are never accepted
    dict(SPEC, y="landed_inr"),                    # not a column of the result
    dict(SPEC, type="pie"),
    dict(SPEC, y="unit_status"),                   # nothing numeric to plot
])
def test_binder_rejects(bad):
    with pytest.raises(ChartRejected):
        bind_chart(bad, TABLE, 0)


def test_scenario_result_becomes_a_table():
    t = table_of("run_scenario", {"awards": [{"line_no": 1, "sku": "S1", "vendor_id": 2, "vendor": "V", "price_on_basis_inr": "8.0000",
                                              "status": "ASSUMED", "annual_qty": 10, "annual_spend_inr": "80", "freight_basis": "UNKNOWN",
                                              "freight_status": "FREIGHT_DEPENDENT", "break_even_inr_per_box": "2.0000", "flags": []}]})
    assert t["rows"][0]["price_on_basis_inr"] == "8.0000" and "flags" not in t["columns"]


def test_analyst_chart_equals_result_rows(processed):
    c, app, rid, v1, v5 = processed
    sql = "SELECT vendor, line_no, unit_price_inr, unit_status FROM v_quotes WHERE line_no IN (1, 2, 15) ORDER BY line_no, vendor"
    model = _analyst(app, [tool("query", {"sql": sql}, "t1"),
                           tool("make_chart", {**SPEC, "title": "Unit price by line"}, "t2"),
                           text("The chart compares unit prices by vendor for these lines; one cell has no usable price.")])
    a = c.post("/analyst/ask", json={"rfx_id": rid, "question": "Chart unit prices for lines 1, 2 and 15"}).json()
    rows = a["results"][0]["result"]["rows"]
    assert a["tables"][0]["rows"] == rows and a["tables"][0]["columns"] == ["vendor", "line_no", "unit_price_inr", "unit_status"]
    chart = a["charts"][0]
    assert chart["data"] == [{"x": r["line_no"], "y": r["unit_price_inr"], "series": r["vendor"], "status": r["unit_status"]}
                             for r in rows if r["unit_price_inr"] is not None]
    assert [o["x"] for o in chart["omitted"]] == [r["line_no"] for r in rows if r["unit_price_inr"] is None]
    assert chart["omitted"]                                   # line 15 V5 is UNRESOLVED: listed, not drawn as 0
    assert a["grounded"] is True
    # the chart request carried no data of its own (strict tool schema)
    tool_def = next(t for t in model.requests[0]["tools"] if t["name"] == "make_chart")
    assert "data" not in tool_def["input_schema"]["properties"] and tool_def["input_schema"]["additionalProperties"] is False
    x = load_workbook(io.BytesIO(c.get(f"/analyst/answers/{a['answer_id']}/export?index=0").content))
    assert x["Result"].max_row == len(rows) + 1


def test_bad_chart_is_reported_to_the_model(processed):
    c, app, rid, v1, v5 = processed
    _analyst(app, [tool("make_chart", SPEC, "t1"), text("I could not chart that.")])
    a = c.post("/analyst/ask", json={"rfx_id": rid, "question": "chart?"}).json()
    assert a["charts"] == [] and a["tool_calls"][0]["error"] is True


def test_comparison_carries_answers_and_documents_fn_10(processed):
    c, app, rid, v1, v5 = processed
    vendors = {v["vendor_id"]: v for v in c.get(f"/rfx/{rid}/comparison").json()["vendors"]}
    assert vendors[v5]["eligibility"] == {"quality": "Passed", "commercial": "Failed"}
    assert vendors[v1]["eligibility"] == {"quality": "Passed", "commercial": "Passed"}
    docs = vendors[v5]["documents"]
    assert {d["doc_type"] for d in docs} == {"ISO_9001_CERTIFICATE", "BCT_ECT_TEST_REPORT", "FOOD_CONTACT_DECLARATION"}
    assert all(d["evidence_ref"].startswith("docfact:") for d in docs)
    iso = next(d for d in docs if d["doc_type"] == "ISO_9001_CERTIFICATE")
    assert iso["expiry_date"] == "2027-08-18" and iso["filename"] == "Sahyadri_ISO9001.pdf"
