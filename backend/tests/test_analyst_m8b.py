"""M8b: read-only document facts and questionnaire answers with evidence refs (NLA-11), grounding of dates
and identifiers (NLA-12), "not in the data" (NLA-13), label lint (ELG-6), caveat engine incl. coverage and
excluded-value detection (NLA-4, EDGE-07)."""
import anthropic
import httpx2 as httpx
import pytest

from app.analysis.caveats import sql_caveats
from app.analysis.grounding import check_identifiers, label_lint
from app.analysis.sql_tool import run_sql
from app.llm.gateway import LLMGateway
from tests.test_analyst_m8a import Model, text, tool
from tests.test_review_m5b import processed  # noqa: F401  (fixture: slice data, both vendors processed)

ISO_SQL = "SELECT vendor, certificate_number, expiry_date, valid_today, evidence_ref FROM v_doc_facts WHERE doc_type = 'ISO_9001_CERTIFICATE' ORDER BY vendor"


def test_identifier_grounding():
    results = [{"rows": [{"expiry_date": "2027-08-18", "certificate_number": "ICS/QMS/24/55871"}]}]
    assert check_identifiers("Valid until 2027-08-18 (cert ICS/QMS/24/55871).", results, "q") == []
    assert check_identifiers("It expires on 18 August 2027.", results, "q") == []          # same date, other format
    assert check_identifiers("It expires on 2028-01-01.", results, "q") == ["2028-01-01"]
    assert check_identifiers("Certificate ICS/QMS/24/99999.", results, "q") == ["ICS/QMS/24/99999"]


def test_label_lint():
    assert label_lint("V2 failed the quality check.", [{"rows": [{"state": "UNVERIFIED"}]}])
    assert label_lint("V5 failed CP-01.", [{"rows": [{"state": "FAIL"}]}]) == []
    assert label_lint("V2 is Unverified on QC-01.", [{"rows": [{"state": "UNVERIFIED"}]}]) == []


def test_views_expose_facts_with_evidence_refs(processed):
    c, app, rid, v1, v5 = processed
    db = str(app.state.settings.db_path)
    iso = run_sql(db, ISO_SQL)["rows"]
    assert [(r["vendor"], r["expiry_date"], r["valid_today"]) for r in iso] == [
        ("Deccan Kraft & Board Pvt. Ltd.", "2028-11-01", 1), ("Sahyadri Paper Mills", "2027-08-18", 1)]
    assert all(r["evidence_ref"].startswith("docfact:") for r in iso)
    ans = run_sql(db, "SELECT vendor, requirement_key, state, answer_value, answer_text, evidence_snippet, evidence_ref "
                      "FROM v_answers WHERE requirement_key = 'CP-01' ORDER BY vendor")["rows"]
    v5row = next(r for r in ans if r["vendor"].startswith("Sahyadri"))
    assert v5row["state"] == "FAIL" and v5row["answer_value"] == "No" and "30 days" in v5row["answer_text"]
    assert v5row["evidence_snippet"].startswith("[vendor content] ")  # marked untrusted (AI-16)
    # NLA-13: a document that does not exist yields no rows; the analyst must say "not in the data"
    assert run_sql(db, "SELECT * FROM v_doc_facts WHERE doc_type = 'FSC_CERTIFICATE'")["rows"] == []
    with pytest.raises(Exception):
        run_sql(db, "SELECT * FROM document_fact")  # raw tables are not approved views
    cov = run_sql(db, "SELECT name, lines_quoted, lines_total FROM v_vendors ORDER BY name")["rows"]
    assert cov[0] == {"name": "Deccan Kraft & Board Pvt. Ltd.", "lines_quoted": 28, "lines_total": 30}


def test_sql_caveats_flag_excluded_values_and_coverage(processed):
    c, app, rid, v1, v5 = processed
    db = str(app.state.settings.db_path)
    res = run_sql(db, "SELECT line_no, vendor_id, unit_price_inr, landed_inr, unit_status FROM v_quotes WHERE unit_status = 'NEEDS_REVIEW'")
    cav = sql_caveats(app.state.session_factory, rid, res)
    assert cav["excluded_value_appeared_in_result"] and cav["status_counts"] == {"NEEDS_REVIEW": len(res["rows"])}
    allq = sql_caveats(app.state.session_factory, rid, run_sql(db, "SELECT line_no, vendor_id, unit_status FROM v_quotes"))
    assert "Deccan Kraft & Board Pvt. Ltd.: 28/30, missing lines 19, 20" in allq["coverage"]


def _analyst(app, outs):
    model = Model(outs)
    client = anthropic.Anthropic(api_key="k", http_client=httpx.Client(transport=httpx.MockTransport(model)))
    app.state.gateway_factory = lambda: LLMGateway(app.state.session_factory, client=client)
    return model


def test_fact_answer_grounded_with_sources(processed):
    c, app, rid, v1, v5 = processed
    _analyst(app, [tool("query", {"sql": ISO_SQL}),
                   text("Both ISO 9001 certificates are valid today: Deccan's until 2028-11-01 and Sahyadri's until 18 August 2027.")])
    a = c.post("/analyst/ask", json={"rfx_id": rid, "question": "Whose ISO 9001 certificate is still valid?"}).json()
    assert a["grounded"] is True and a["regenerated"] is False
    assert a["caveats"]["sources"] and all(s.startswith("docfact:") for s in a["caveats"]["sources"])
    assert a["results"][0]["result"]["rows"]                                    # show work (NLA-9)


def test_invented_date_and_false_failed_are_regenerated_then_bannered(processed):
    c, app, rid, v1, v5 = processed
    bad = "Sahyadri's certificate expires on 2026-12-31, so it failed the check."
    model = _analyst(app, [tool("query", {"sql": ISO_SQL}), text(bad), text(bad)])
    a = c.post("/analyst/ask", json={"rfx_id": rid, "question": "Whose ISO 9001 certificate is still valid?"}).json()
    assert a["regenerated"] is True and a["grounded"] is False and a["banner"]
    assert "2026-12-31" in a["ungrounded_numbers"] and a["lint"]
    feedback = model.requests[-1]["messages"][-1]["content"]
    assert "2026-12-31" in feedback and "FAIL" in feedback                     # appended, never edited history


def test_live_findings_exact_values_and_negated_failed():
    """Live run: exact 4-dp values from a query were rejected, and a sentence saying no vendor failed was linted."""
    from app.analysis.grounding import check_grounding
    results = [{"rows": [{"unit_price_inr": "4.5980"}, {"unit_price_inr": "17.3201"}]}]
    assert check_grounding('returns exactly "4.5980" for line 5 and "17.3201" for line 6', results, "q") == []
    assert check_grounding("about 4.60 a box", results, "q") == []
    assert check_grounding("it is 4.5990", results, "q") == ["4.5990"]
    unverified = [{"rows": [{"state": "UNVERIFIED"}]}]
    assert label_lint("No vendor has a FAIL result in the data, so none is described as failed.", unverified) == []
    assert label_lint("Malwa failed the quality check.", unverified)
