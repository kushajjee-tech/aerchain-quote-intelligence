"""M3a: TEXT extraction stage end to end with a mocked model (no network)."""
import json

from app.ingest.wire import to_wire
from tests.llm_mock import respond

import anthropic
import httpx2 as httpx

from app.ingest.extract import run_text_extraction
from app.ingest.parsers.eml import parse_eml
from app.llm.gateway import LLMGateway

SENTENCE = "₹42/kg for the 5-ply, 38 for the 3-ply, rest same as last year, freight extra."
RFX = {"lines": [{"line_no": 1, "sku_code": "S-1", "description": "box", "item_type": "RSC", "ply": 3,
                  "flute_profile": "B", "dims_mm": {"L": 1, "W": 2, "H": 3}}],
       "questionnaire": [{"no": "Q1", "section": "QUALITY", "text": "ISO?"}]}
EV = {"unit_ids": ["D1:l1"]}
MODEL_OUT = {
    "line_quotes": [
        {"vendor_line_ref": "5-ply", "description_as_stated": "5-ply", "unit_class": "PER_KG", "unit_source": "STATED",
         "unit_as_stated": "/kg", "price": {"value_as_stated": "42", "value": 42, "currency_as_stated": "₹",
         "currency_source": "STATED", "evidence": {**EV, "quote": "₹42/kg"}},
         "applies_to_group": {"attribute": "ply", "value": 5, "evidence": {**EV, "quote": "5-ply"}}},
        {"vendor_line_ref": "3-ply", "description_as_stated": "3-ply", "unit_class": "PER_KG",
         "unit_source": "INHERITED_FROM_CONTEXT", "unit_inherited_from": {**EV, "quote": "₹42/kg"},
         "price": {"value_as_stated": "38", "value": 38, "currency_source": "INHERITED_FROM_CONTEXT",
                   "evidence": {**EV, "quote": "38 for the 3-ply"}},
         "applies_to_group": {"attribute": "ply", "value": 3, "evidence": {**EV, "quote": "3-ply"}}},
    ],
    "document_terms": [{"type": "FREIGHT", "value": None, "scope": "all", "text": "freight extra",
                        "evidence": {**EV, "quote": "freight extra"}}],
    "references": [{"type": "PRIOR_UNSPECIFIED", "scope_text": "rest", "evidence": {**EV, "quote": "rest same as last year"}}],
    "questionnaire_answers": [], "gst_statement": "SILENT",
}


def test_v5_sentence_extraction_verified(session_factory):
    from email.message import EmailMessage
    m = EmailMessage(); m["From"] = "v5@x.example"; m.set_content(SENTENCE)
    body = parse_eml("D1", m.as_bytes()).body
    sent = []

    def handler(req):
        sent.append(json.loads(req.content))
        return respond(req, [{"type": "text", "text": json.dumps(to_wire(MODEL_OUT))}])
    client = anthropic.Anthropic(api_key="k", http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    res = run_text_extraction(LLMGateway(session_factory, client=client), RFX, [body])
    assert [l.unit_class for l in res.lines] == ["PER_KG", "PER_KG"]
    assert res.lines[0].reasons == [] and res.lines[1].reasons == ["UNIT_INHERITED"]
    assert res.term_reasons == [[]] and res.extraction.gst_statement == "SILENT"
    assert res.extraction.references[0].type == "PRIOR_UNSPECIFIED"
    prompt = sent[0]["messages"][0]["content"]
    assert "[D1:l1] " + SENTENCE in prompt and "S-1" in prompt
    assert sent[0]["output_config"]["effort"] == "high"



def test_line_extraction_streams_and_facts_do_not(session_factory):
    """Live finding: a 28-line sheet with slabs overflowed 16k/21k tokens; the lines call now streams a larger budget."""
    from email.message import EmailMessage
    m = EmailMessage(); m["From"] = "v5@x.example"; m.set_content(SENTENCE)
    body = parse_eml("D1", m.as_bytes()).body
    streamed = []

    def handler(req):
        streamed.append(bool(json.loads(req.content).get("stream")))
        return respond(req, [{"type": "text", "text": json.dumps(to_wire(MODEL_OUT))}])
    client = anthropic.Anthropic(api_key="k", http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    res = run_text_extraction(LLMGateway(session_factory, client=client), RFX, [body])
    assert streamed == [True, False] and len(res.lines) == 2
