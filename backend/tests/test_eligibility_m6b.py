"""M6b: co-pilot questionnaire drafting (validated against brief-pack citations, all-or-nothing, audited),
questionnaire conformance (RFX-10), and eligibility from verified answers + document facts (ELG, DL-3/14/24/29)."""
import copy
from datetime import date

import pytest

from app.eligibility.evaluate import evaluate_vendor, resolve_expiry, verify_fact
from app.ingest.evidence import EvidenceUnit
from app.ingest.schemas import Answer, AttachedDocument, Evidence
from tests.test_rfx_m6a import GAP_PATCH, BUYER, MAPPING, _start, add_questionnaire, env, questionnaire_output  # noqa: F401

ON = date(2026, 11, 5)


@pytest.mark.parametrize("expiry,issue,expected", [
    ("2027-08-18", None, ("DATE", "2027-08-18")),
    ("12 months from date tested", "2026-07-09", ("DATE", "2027-07-09")),
    ("2 years from issue", "29/02/2024", ("DATE", "2026-02-28")),
    ("Superseded by a newer declaration", "2026-03-02", ("NO_EXPIRY", None)),
    ("31 March 2027", None, ("DATE", "2027-03-31")),
    ("12 months from date tested", None, ("UNREADABLE", None)),
    ("soon", None, ("UNREADABLE", None)),
    (None, "2026-01-01", ("NONE_STATED", None)),
])
def test_resolve_expiry(expiry, issue, expected):
    assert resolve_expiry(expiry, issue) == expected


UNITS = {u.id: u for u in [
    EvidenceUnit("D3:p1l4", "D3", "text_block", {}, "Acme Boards Pvt. Ltd."),
    EvidenceUnit("D3:p1l11", "D3", "text_block", {}, "Valid until 2027-08-18"),
    EvidenceUnit("D3:p1l12", "D3", "text_block", {}, "Valid until 2025-01-31"),
    EvidenceUnit("D2:Q!C3", "D2", "cell", {}, "Yes"),
    EvidenceUnit("D2:Q!C4", "D2", "cell", {}, "No"),
    EvidenceUnit("D2:Q!C5", "D2", "cell", {}, "180"),
]}
FILES = {"D3": "cert.pdf"}
Q_ISO = {"no": "Q1", "requirement_key": "QC-01", "section": "QUALITY", "applicability": "ALL", "pass_rule": {"op": "==", "value": "yes"},
         "evidence_required": True, "evidence_doc_type": "ISO_9001_CERTIFICATE"}
Q_CAP = {"no": "Q4", "requirement_key": "QC-04", "section": "QUALITY", "applicability": "ALL", "pass_rule": {"op": ">=", "value": 250},
         "evidence_required": False, "evidence_doc_type": None}
Q_PAY = {"no": "Q6", "requirement_key": "CP-01", "section": "COMMERCIAL", "applicability": "ALL", "pass_rule": {"op": "==", "value": "yes"},
         "evidence_required": False, "evidence_doc_type": None}
Q_FOOD = {"no": "Q3", "requirement_key": "QC-03", "section": "QUALITY", "applicability": "LINES_WITH_FLAG(food_contact)",
          "pass_rule": {"op": "==", "value": "yes"}, "evidence_required": False, "evidence_doc_type": None}


def _doc(entity="Acme Boards Pvt. Ltd.", valid_unit="D3:p1l11", expiry="2027-08-18", quote=None):
    return AttachedDocument(document_ref="D3", doc_type="ISO_9001_CERTIFICATE", entity_name=entity, expiry_as_stated=expiry,
                            evidence=Evidence(unit_ids=["D3:p1l4", valid_unit], quote=quote or "Acme Boards Pvt. Ltd."))


def _ans(no, unit, value, refs=()):
    return Answer(question_no=no, answer_value=value, answer_text=value, evidence=Evidence(unit_ids=[unit], quote=value),
                  attachment_refs=list(refs)), []


def _states(results):
    return {q["requirement_key"]: (r.state, r.reason) for q, r, _ in results}


def test_eligibility_rules_over_verified_facts():
    fact = verify_fact(_doc(), UNITS, FILES)
    assert fact.readable and fact.expiry_date == "2027-08-18"
    res = _states(evaluate_vendor([Q_ISO, Q_CAP, Q_PAY, Q_FOOD],
                                  [_ans("Q1", "D2:Q!C3", "Yes", ["cert.pdf"]), _ans("Q4", "D2:Q!C5", "180"), _ans("Q6", "D2:Q!C4", "No")],
                                  [fact], "Acme Boards Pvt Ltd", set(), ON))
    assert res["QC-01"][0] == "PASS"
    assert res["QC-04"][0] == "FAIL" and res["CP-01"][0] == "FAIL"
    assert res["QC-03"][0] == "NOT_APPLICABLE"  # vendor quotes no food-contact line (DL-29)


@pytest.mark.parametrize("doc,why", [
    (dict(valid_unit="D3:p1l12", expiry="2025-01-31"), "expired"),
    (dict(entity="Other Corrugators Ltd"), "could not be read"),         # value not in the cited text
    (dict(quote="Fabricated certificate text"), "could not be read"),   # citation does not verify
    (dict(expiry="until the moon"), "could not be read"),
])
def test_bad_evidence_is_unverified_never_failed(doc, why):
    fact = verify_fact(_doc(**doc), UNITS, FILES)
    (q, r, _), = evaluate_vendor([Q_ISO], [_ans("Q1", "D2:Q!C3", "Yes", ["cert.pdf"])], [fact], "Acme Boards Pvt. Ltd.", set(), ON)
    assert r.state == "UNVERIFIED" and why in r.reason


def test_document_in_another_entitys_name():
    other = {**{u: UNITS[u] for u in UNITS}, "D3:p1l4": EvidenceUnit("D3:p1l4", "D3", "text_block", {}, "Other Corrugators Ltd")}
    fact = verify_fact(_doc(entity="Other Corrugators Ltd", quote="Other Corrugators Ltd"), other, FILES)
    (_, r, _), = evaluate_vendor([Q_ISO], [_ans("Q1", "D2:Q!C3", "Yes", ["cert.pdf"])], [fact], "Acme Boards Pvt. Ltd.", set(), ON)
    assert r.state == "UNVERIFIED" and "another entity" in r.reason


def test_unanswered_and_unverified_answer():
    bad_answer = (Answer(question_no="Q6", answer_value="Yes", answer_text="Yes",
                         evidence=Evidence(unit_ids=["D2:Q!C4"], quote="Yes")), ["EVIDENCE_NOT_FOUND"])
    res = _states(evaluate_vendor([Q_CAP, Q_PAY], [bad_answer], [], "Acme", set(), ON))
    assert res["QC-04"][0] == "UNVERIFIED" and res["CP-01"][0] == "UNVERIFIED"  # never Failed


def _rfx_with_gaps(c, model):
    rfx_id = _start(c, model)["rfx_id"]
    c.post(f"/rfx/{rfx_id}/mapping/confirm", json={"mapping": MAPPING})
    c.post(f"/rfx/{rfx_id}/gaps/apply", json={"patch": GAP_PATCH, "source_text": BUYER})
    return rfx_id


def test_invalid_questionnaire_is_never_partially_applied(env):
    c, app, model, data = env
    rfx_id = _rfx_with_gaps(c, model)
    good = questionnaire_output(data)
    bad = copy.deepcopy(good)
    cap = next(q for q in bad["questions"] if q["requirement_key"] == "QC-04")
    cap["pass_value"] = "300"                                                   # threshold not in the source
    pay = next(q for q in bad["questions"] if q["requirement_key"] == "CP-01")
    pay["source"]["quote"] = "Payment terms: 90 days from invoice."              # fabricated quote
    gst = next(q for q in bad["questions"] if q["requirement_key"] == "CP-03")
    gst["requirement_key"] = "CP-09"                                             # key not in the cited text
    model.outputs.append(bad)
    prop = c.post(f"/rfx/{rfx_id}/questionnaire/propose").json()
    problems = {v["key"]: v["problems"] for v in prop["validation"] if not v["ok"]}
    assert problems == {"QC-04": ["threshold not stated in the cited source"], "CP-01": ["EVIDENCE_NOT_FOUND"],
                        "CP-09": ["requirement key not in the cited source"]}
    r = c.post(f"/rfx/{rfx_id}/questionnaire/apply", json={"draft": prop["draft"]})
    assert r.status_code == 422
    from app.db.models import Question
    with app.state.session_factory() as s:
        assert s.query(Question).count() == 0
    # the model never saw the canonical spec: only the brief-pack documents (PRD AI-17)
    sent = model.requests[-1]["messages"][0]["content"]
    assert "Buyer requirement documents" in sent and "pass_rule" not in sent and "canonical" not in sent.lower()


@pytest.mark.parametrize("mutate,expected", [
    (lambda qs: qs.__setitem__(2, {**qs[2], "applicability": "ALL"}),
     [{"question": "QC-03", "field": "applicability", "draft": "ALL", "canonical": "LINES_WITH_FLAG(food_contact)"}]),
    # dropping a question also shifts the numbers vendors answer by: reported, never hidden
    (lambda qs: qs.pop(4), [{"question": "QC-05", "difference": "missing from draft"},
                            {"question": "CP-01", "field": "no", "draft": "Q5", "canonical": "Q6"},
                            {"question": "CP-02", "field": "no", "draft": "Q6", "canonical": "Q7"},
                            {"question": "CP-03", "field": "no", "draft": "Q7", "canonical": "Q8"}]),
])
def test_questionnaire_conformance_reports_exactly_the_difference(env, mutate, expected):
    c, app, model, data = env
    rfx_id = _rfx_with_gaps(c, model)
    out = questionnaire_output(data)
    mutate(out["questions"])
    model.outputs.append(out)
    prop = c.post(f"/rfx/{rfx_id}/questionnaire/propose").json()
    assert c.post(f"/rfx/{rfx_id}/questionnaire/apply", json={"draft": prop["draft"]}).status_code == 200
    conf = c.post(f"/rfx/{rfx_id}/conformance").json()
    assert conf["conforms"] is False and conf["differences"] == expected


def test_questionnaire_locked_after_approval_and_audited(env):
    c, app, model, data = env
    rfx_id = _rfx_with_gaps(c, model)
    prop = add_questionnaire(c, model, rfx_id, data)
    assert c.post(f"/rfx/{rfx_id}/conformance").json()["conforms"] is True
    assert c.post(f"/rfx/{rfx_id}/approve").status_code == 200
    assert c.post(f"/rfx/{rfx_id}/questionnaire/apply", json={"draft": prop["draft"]}).status_code == 409
    from app.db.models import AuditEvent
    with app.state.session_factory() as s:
        ev = s.query(AuditEvent).filter_by(action="QUESTIONNAIRE_APPLIED").one()
        assert len(ev.after["questions"]) == 8 and all(q["source"]["unit_ids"] for q in ev.after["questions"])



def test_question_numbers_assigned_by_code_not_file_order(env):
    """Live finding: the model numbered the commercial policy first because its file sorts first."""
    c, app, model, data = env
    rfx_id = _rfx_with_gaps(c, model)
    out = questionnaire_output(data)
    shuffled = list(reversed(out["questions"]))
    for i, q in enumerate(shuffled, start=1):
        q["no"] = f"Q{i}"                      # whatever the model numbered
    model.outputs.append({**out, "questions": shuffled})
    prop = c.post(f"/rfx/{rfx_id}/questionnaire/propose").json()
    assert [(q["no"], q["requirement_key"]) for q in prop["draft"]["questions"]] == [
        ("Q1", "QC-01"), ("Q2", "QC-02"), ("Q3", "QC-03"), ("Q4", "QC-04"), ("Q5", "QC-05"),
        ("Q6", "CP-01"), ("Q7", "CP-02"), ("Q8", "CP-03")]
