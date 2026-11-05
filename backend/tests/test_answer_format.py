"""Answer-format guardrails: short direct answers, no markdown tables or internal codes, one chosen data table."""
from app.analysis.answer_format import format_problems, split_show, tidy
from tests.test_analyst_m8a import GOOD, SCEN, analyst_client, text, tool

BLOB = "\n".join(["## Summary", "| Vendor | Lines |", "|---|---|", "| V1 | 2 |"] +
                 [f"- point {i} about UNIT_INHERITED values" for i in range(7)] + ["word " * 160])


def test_problems_detects_tables_headings_length_codes_and_bullets():
    p = " ".join(format_problems(BLOB, "Summarize the responses"))
    for expected in ("markdown tables", "headings", "words", "bullets", "UNIT_INHERITED"):
        assert expected in p
    assert format_problems(GOOD + "\nSHOW: 0", "Cost of the split?") == []


def test_detail_requests_get_a_larger_budget():
    long = "Direct answer.\n" + "\n".join(f"- point {i}" for i in range(6)) + "\n" + "word " * 150
    assert format_problems(long, "Summarize")                      # too long and too many bullets
    assert not format_problems(long, "Give me a detailed breakdown")  # explicitly asked for detail


def test_show_marker_is_parsed_removed_and_bounded():
    assert split_show("Answer.\nSHOW: 1", 2) == ("Answer.", 1)
    assert split_show("Answer.\nSHOW: none", 2) == ("Answer.", None)
    assert split_show("Answer.\nSHOW: 7", 2) == ("Answer.", None)   # out of range → no table, never a wrong one
    assert split_show("Answer.", 2) == ("Answer.", None)


def test_tidy_removes_structure_without_rewording():
    out = tidy(BLOB, "Summarize")
    assert "|" not in out and "#" not in out and out.count("- point") == 4
    assert "point 0 about UNIT_INHERITED values" in out              # sentences are kept verbatim


def test_blob_answer_is_regenerated_and_table_choice_returned(tmp_path):
    c, rid, model = analyst_client(tmp_path, [tool("run_scenario", SCEN), text(BLOB), text(GOOD + "\nSHOW: 0")])
    a = c.post("/analyst/ask", json={"rfx_id": rid, "question": "What if we split it, cheapest per line?"}).json()
    assert a["regenerated"] is True and a["narrative"] == GOOD and a["display_table"] == 0 and a["format_issues"] == []
    assert "Format:" in model.requests[2]["messages"][-1]["content"]   # format feedback appended, not a new prompt
    assert "Answer format (strict" in model.requests[0]["system"][0]["text"] if isinstance(model.requests[0]["system"], list) \
        else "Answer format (strict" in model.requests[0]["system"]


def test_assistant_runs_on_the_configured_cheaper_model(tmp_path):
    c, rid, model = analyst_client(tmp_path, [tool("run_scenario", SCEN), text(GOOD)])
    c.post("/analyst/ask", json={"rfx_id": rid, "question": "What if we split it, cheapest per line?"})
    assert {r["model"] for r in model.requests} == {"claude-haiku-5-5"}
    assert all("fallbacks" not in r for r in model.requests)        # no server-side fallback on Haiku
