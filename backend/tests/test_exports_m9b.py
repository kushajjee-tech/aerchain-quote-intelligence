"""M9b exports: comparison workbook equals the grid (EXP-1), memo Markdown + printable HTML (EXP-2), analyst
table export re-reads equal to the stored result (EXP-3), audit CSV (AUD-1)."""
import csv
import io

from openpyxl import load_workbook

from tests.test_analyst_m8b import ISO_SQL, _analyst
from tests.test_analyst_m8a import text, tool
from tests.test_review_m5b import SENTENCE, processed  # noqa: F401


def test_comparison_workbook_equals_grid(processed):
    c, app, rid, v1, v5 = processed
    r = c.get(f"/rfx/{rid}/export.xlsx")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/vnd.openxmlformats")
    wb = load_workbook(io.BytesIO(r.content))
    assert wb.sheetnames == ["Comparison", "Sources", "Traces", "Assumptions", "Eligibility", "Exclusions"]
    grid = c.get(f"/rfx/{rid}/comparison").json()
    ws = wb["Comparison"]
    header = [x.value for x in ws[1]]
    for i, row in enumerate(grid["rows"], start=2):
        values = [x.value for x in ws[i]]
        assert values[0] == row["line_no"] and values[1] == row["sku_code"]
        for v in grid["vendors"]:
            col = header.index(f"{v['name']} — ₹/box (unit)")
            cell = row["cells"][str(v["vendor_id"])]
            if cell["status"] in ("UNRESOLVED", "NOT_CONVERTIBLE", "MISSING"):
                assert values[col] is None                                  # never exported as a number
            else:
                assert values[col] == cell["value"]                         # exact Decimal text
    statuses = {x.value for row in ws.iter_rows(min_row=2) for x in row if isinstance(x.value, str) and x.value in
                ("Verified", "Extracted", "Assumed", "Needs review", "Unresolved", "Not convertible", "Missing")}
    assert {"Assumed", "Unresolved", "Missing"} <= statuses
    assert any(row[6].value == SENTENCE for row in wb["Sources"].iter_rows(min_row=2))
    elig = [[x.value for x in row] for row in wb["Eligibility"].iter_rows(min_row=2)]
    assert ["Sahyadri Paper Mills", "COMMERCIAL", "Q6", "CP-01", "Failed"] in [e[:5] for e in elig]
    assert all(e[4] in ("Passed", "Failed", "Unverified", "Not applicable") for e in elig)
    assert any("Constant set v1" in (row[2].value or "") for row in wb["Assumptions"].iter_rows(min_row=2))
    assert wb["Exclusions"].max_row > 1


def test_memo_markdown_and_printable_html(processed):
    c, app, rid, v1, v5 = processed
    sc = c.post(f"/rfx/{rid}/scenarios", json={}).json()
    md = c.get(f"/scenarios/{sc['scenario_id']}/memo.md")
    assert md.status_code == 200 and md.text.startswith("# Draft award recommendation") and "attachment" in md.headers["content-disposition"]
    page = c.get(f"/scenarios/{sc['scenario_id']}/memo.html").text
    assert page.startswith("<!doctype html>") and "<table>" in page and "<h2>Line awards</h2>" in page and "@media print" in page
    c.post(f"/scenarios/{sc['scenario_id']}/acknowledge", json={"actor": "priya"})
    assert "ACKNOWLEDGED by priya" in c.get(f"/scenarios/{sc['scenario_id']}/memo.md").text


def test_analyst_table_export_round_trip(processed):
    c, app, rid, v1, v5 = processed
    _analyst(app, [tool("query", {"sql": ISO_SQL}), text("Both certificates are valid: until 2028-11-01 and 2027-08-18.")])
    a = c.post("/analyst/ask", json={"rfx_id": rid, "question": "ISO validity?"}).json()
    rows = a["results"][0]["result"]["rows"]
    x = c.get(f"/analyst/answers/{a['answer_id']}/export?fmt=xlsx")
    wb = load_workbook(io.BytesIO(x.content))
    got = [[cell.value for cell in row] for row in wb["Result"].iter_rows(min_row=2)]
    cols = a["results"][0]["result"]["columns"]
    assert got == [[r[k] for k in cols] for r in rows]                         # same rows, same values
    assert wb["Caveats"].max_row > 1
    text_csv = c.get(f"/analyst/answers/{a['answer_id']}/export?fmt=csv").text
    parsed = list(csv.reader(io.StringIO(text_csv)))
    assert parsed[0] == cols and len([r for r in parsed[1:] if r and not r[0].startswith("#") and r[0]]) == len(rows)
    assert any(r and r[0].startswith("# caveat: sources") for r in parsed)
    assert c.get("/analyst/answers/999/export").status_code == 404


def test_audit_csv(processed):
    c, app, rid, v1, v5 = processed
    rows = list(csv.reader(io.StringIO(c.get(f"/rfx/{rid}/audit.csv").text)))
    assert rows[0] == ["id", "at", "actor", "action", "target", "before", "after", "reason"]
    assert {"QUESTIONNAIRE_APPLIED", "RFX_APPROVED", "ELIGIBILITY_EVALUATED", "RECOMPUTE"} <= {r[3] for r in rows[1:]}
