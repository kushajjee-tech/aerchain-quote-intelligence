"""M8a: bounded analyst loop — run_scenario/query tools, grounding check with appended regeneration,
SQL guard, tool-call cap, code-added exclusions. Model mocked."""
import json

import anthropic
import httpx2 as httpx
import pytest

from app.analysis.grounding import check_grounding
from app.analysis.sql_tool import SqlRejected, check_sql
from app.llm.gateway import LLMGateway
from tests.test_comparison_m5a import setup

SCEN = {"strategy": "cheapest_per_line", "vendor_id": None, "context": "formal", "include_needs_review": False, "exclude_vendor_ids": []}


def msg(content, stop="end_turn"):
    return {"id": "m", "type": "message", "role": "assistant", "model": "claude-opus-5-5", "content": content,
            "stop_reason": stop, "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}}


def tool(name, inp, tid="tu1"):
    return msg([{"type": "tool_use", "id": tid, "name": name, "input": inp}], "tool_use")


def text(t):
    return msg([{"type": "text", "text": t}])


class Model:
    def __init__(self, outs):
        self.outs, self.requests = list(outs), []

    def __call__(self, req):
        self.requests.append(json.loads(req.content))
        return httpx.Response(200, json=self.outs.pop(0))


def analyst_client(tmp_path, outs):
    c, rid, v1, v5, v2 = setup(tmp_path, final=True)
    model = Model(outs)
    client = anthropic.Anthropic(api_key="k", http_client=httpx.Client(transport=httpx.MockTransport(model)))
    c.app.state.gateway_factory = lambda: LLMGateway(c.app.state.session_factory, client=client)
    return c, rid, model


GOOD = "Splitting cheapest per line costs ₹20,000 a year on the unit basis: V5 ₹8,000 and V1 ₹12,000. Line 3 has no includable quote."


def test_grounded_answer_with_code_added_exclusions(tmp_path):
    c, rid, model = analyst_client(tmp_path, [tool("run_scenario", SCEN), text(GOOD)])
    a = c.post("/analyst/ask", json={"rfx_id": rid, "question": "What if we split it, cheapest per line?"}).json()
    assert a["grounded"] is True and a["regenerated"] is False and a["narrative"] == GOOD
    assert a["tool_calls"][0]["tool"] == "run_scenario"
    assert any(e["reason"] == "NEEDS_REVIEW" for e in a["exclusions"]) and a["awaiting_response"] == ["V2"]
    assert a["caveats"]["uncovered_lines"] == [3] and a["caveats"]["method"].startswith("run_scenario")
    assert model.requests[0]["tools"][1]["strict"] is True and model.requests[0]["output_config"]["effort"] == "medium"


def test_invented_number_triggers_appended_regeneration(tmp_path):
    bad = "The split costs ₹19,500 a year."
    c, rid, model = analyst_client(tmp_path, [tool("run_scenario", SCEN), text(bad), text(GOOD)])
    a = c.post("/analyst/ask", json={"rfx_id": rid, "question": "Cost of the split?"}).json()
    assert a["regenerated"] is True and a["grounded"] is True
    third = model.requests[2]["messages"]
    assert third[:4] == model.requests[1]["messages"] + [{"role": "assistant", "content": [{"type": "text", "text": bad}]}]
    assert third[-1]["role"] == "user" and "19,500" in third[-1]["content"]  # feedback appended, history untouched


def test_still_ungrounded_is_flagged(tmp_path):
    c, rid, _ = analyst_client(tmp_path, [text("It costs ₹99,999."), text("Still ₹99,999.")])
    a = c.post("/analyst/ask", json={"rfx_id": rid, "question": "Cost?"}).json()
    assert a["grounded"] is False and a["ungrounded_numbers"] == ["99,999"]


def test_query_tool_and_sql_guard(tmp_path):
    outs = [msg([{"type": "tool_use", "id": "a", "name": "query", "input": {"sql": "SELECT vendor, COUNT(*) AS n FROM v_quotes GROUP BY vendor ORDER BY vendor"}},
                 {"type": "tool_use", "id": "b", "name": "query", "input": {"sql": "DELETE FROM normalized_quote"}}], "tool_use"),
            text("V1 and V5 each have 3 quote cells.")]
    c, rid, model = analyst_client(tmp_path, outs)
    a = c.post("/analyst/ask", json={"rfx_id": rid, "question": "How many cells per vendor?"}).json()
    assert [t["error"] for t in a["tool_calls"]] == [False, True]
    results = model.requests[1]["messages"][-1]["content"]
    assert json.loads(results[0]["content"])["rows"] == [{"vendor": "V1", "n": 3}, {"vendor": "V5", "n": 3}]
    assert results[1]["is_error"] is True and a["grounded"] is True


@pytest.mark.parametrize("sql", ["SELECT * FROM normalized_quote", "SELECT 1; SELECT 2", "PRAGMA table_info(vendor)",
                                 "UPDATE vendor SET name='x'", "WITH x AS (SELECT * FROM audit_event) SELECT * FROM x"])
def test_sql_guard_rejects(sql):
    with pytest.raises(SqlRejected):
        check_sql(sql)


def test_sql_guard_adds_limit():
    assert check_sql("SELECT * FROM v_lines").endswith("LIMIT 1000")


def test_tool_call_cap(tmp_path):
    outs = [tool("query", {"sql": "SELECT 1 AS x FROM v_lines"}, f"t{i}") for i in range(9)] + [text("Done.")]
    c, rid, _ = analyst_client(tmp_path, outs)
    a = c.post("/analyst/ask", json={"rfx_id": rid, "question": "loop"}).json()
    assert len(a["tool_calls"]) == 9 and a["tool_calls"][-1]["error"] is True


def test_grounding_unit_cases():
    res = [{"total": "4,00,00,000", "x": "1234567.8912"}]
    assert check_grounding("Total ₹4.00 crore, also 1,234,567.89 and 12.3 lakh", res, "q") == []
    assert check_grounding("about ₹4.5 crore", res, "q") == ["4.5 crore"]
    assert check_grounding("line 7 and 25 lines", res, "q") == []


def test_grounding_allows_difference_of_two_result_values_only():
    from decimal import Decimal
    res = [{"tool": "run_scenario", "result": {"split_total": 37053770, "single_vendor": 34924460}}]
    # saving = difference of two values that both appear in this turn's results
    assert check_grounding("saves ₹2129310 against it", res, "q") == []
    # a figure that is not a difference or sum of two result values is still flagged
    assert check_grounding("saves ₹123456 against it", res, "q") == ["123456"]
