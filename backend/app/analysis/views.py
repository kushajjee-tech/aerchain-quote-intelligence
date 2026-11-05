"""Approved read-only views — the analyst's whole world (architecture §11.2; NLA-11). There is no view of
full document text: only cited evidence snippets, length-capped and marked as untrusted vendor content."""
from __future__ import annotations

from sqlalchemy import Engine, text

VIEWS = {
    "v_lines": """
        SELECT l.rfx_id, l.line_no, l.sku_code AS sku, l.description, l.item_type, l.ply, l.flute_profile,
               l.annual_qty, l.food_contact
        FROM rfx_line l""",
    "v_quotes": """
        SELECT l.rfx_id, l.line_no, l.sku_code AS sku, q.vendor_id, v.name AS vendor,
               q.unit_price_inr_ex_gst AS unit_price_inr, q.unit_status,
               CASE WHEN q.unit_status IN ('VERIFIED','EXTRACTED','ASSUMED') THEN 1 ELSE 0 END AS includable_formal,
               CASE WHEN q.unit_status = 'NEEDS_REVIEW' THEN 1 ELSE 0 END AS needs_review,
               q.landed_inr_ex_gst AS landed_inr, q.landed_status, q.freight_basis, q.weight_source,
               q.unit_reasons AS reasons, q.flags
        FROM normalized_quote q JOIN rfx_line l ON l.id = q.rfx_line_id JOIN vendor v ON v.id = q.vendor_id""",
    "v_answers": """
        SELECT q.rfx_id, e.vendor_id, v.name AS vendor, q.no AS question_no, q.requirement_key, q.section,
               q.applicability, q.text AS question_text, e.state, e.reason,
               json_extract(e.provenance, '$.answer.value') AS answer_value,
               json_extract(e.provenance, '$.answer.text') AS answer_text,
               '[vendor content] ' || substr(json_extract(e.provenance, '$.answer.evidence.quote'), 1, 200) AS evidence_snippet,
               'eligibility:' || e.id AS evidence_ref
        FROM eligibility_result e JOIN question q ON q.id = e.question_id JOIN vendor v ON v.id = e.vendor_id""",
    "v_doc_facts": """
        SELECT f.rfx_id, f.vendor_id, v.name AS vendor, f.filename, f.doc_type, f.standard, f.certificate_number,
               f.entity_name, f.issue_date, f.expiry_date, f.fact_status,
               json_extract(f.evidence, '$[1].expiry_kind') AS expiry_kind,
               CASE WHEN f.expiry_date IS NULL THEN NULL WHEN f.expiry_date >= date('now') THEN 1 ELSE 0 END AS valid_today,
               '[vendor content] ' || substr(json_extract(f.evidence, '$[0].quote'), 1, 200) AS evidence_snippet,
               'docfact:' || f.id AS evidence_ref
        FROM document_fact f JOIN vendor v ON v.id = f.vendor_id""",
    "v_vendors": """
        SELECT i.rfx_id, v.id AS vendor_id, v.name,
               CASE WHEN EXISTS (SELECT 1 FROM response r WHERE r.rfx_id = i.rfx_id AND r.vendor_id = v.id)
                    THEN 'RESPONDED' ELSE 'AWAITING_RESPONSE' END AS state,
               (SELECT r.coverage_count FROM response r WHERE r.rfx_id = i.rfx_id AND r.vendor_id = v.id) AS lines_quoted,
               (SELECT count(*) FROM rfx_line l WHERE l.rfx_id = i.rfx_id) AS lines_total
        FROM invitation i JOIN vendor v ON v.id = i.vendor_id""",
}


def ensure_views(engine: Engine) -> None:
    with engine.begin() as conn:
        for name, sql in VIEWS.items():
            conn.execute(text(f"DROP VIEW IF EXISTS {name}"))
            conn.execute(text(f"CREATE VIEW {name} AS {sql}"))
