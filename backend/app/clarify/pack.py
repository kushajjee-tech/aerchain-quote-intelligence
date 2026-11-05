"""Deterministic clarification pack (DL-32, DL-20, J9): one per vendor, template-generated, ordered by
decision sensitivity (DL-28). No AI, no reply parsing: the buyer edits, approves into the outbox, and
records the vendor's answers as resolutions. Same inputs → byte-identical body."""
from __future__ import annotations

import hashlib
from decimal import Decimal

from sqlalchemy import select

from app.analysis.scenario import ScenarioParams, run_scenario
from app.db.models import EligibilityResult, NormalizedQuote, Question, Reference, Rfx, RfxLine, Vendor

KIND_ORDER = ["REFERENCE", "UNIT", "READ", "PRICE_CONFLICT", "SLAB", "GST", "FREIGHT", "EVIDENCE", "UNCOVERED_LINE"]
REASON_KIND = {"UNIT_UNKNOWN": "UNIT", "UNIT_SUSPECT": "UNIT", "READ_DISAGREEMENT": "READ", "READ_SINGLE_SOURCE": "READ",
               "LOW_OCR_CONFIDENCE": "READ", "GST_UNCLEAR": "GST", "PRICE_CONFLICT": "PRICE_CONFLICT",
               "MATCH_CONFLICT": "PRICE_CONFLICT", "SLAB_AMBIGUOUS": "SLAB"}


def _q(line) -> str:
    return f"line {line.line_no} ({line.sku_code}, {line.description})"


TEMPLATES = {
    "UNIT": lambda it: (f"For {it['line']}, please confirm the pricing unit of your quoted figure"
                        + (f" ({it['as_stated']})" if it.get("as_stated") else "") + ": per box (piece), per 100, per 1000, or per kg?"
                        + (f" Our reading suggests ₹{it['suggested']}/box." if it.get("suggested") else "")),
    "READ": lambda it: f"For {it['line']}, we could not read your price with confidence. Please confirm the price per box.",
    "PRICE_CONFLICT": lambda it: f"Your response gives more than one price for {it['line']}. Please confirm which price applies.",
    "SLAB": lambda it: f"For {it['line']} (annual quantity {it['qty']:,}), please confirm which quantity slab applies.",
    "GST": lambda it: "Please confirm whether your prices are exclusive of GST, and the GST rate that applies.",
    "FREIGHT": lambda it: ("Your prices do not include freight. Please state freight to our plant per box for these lines "
                           "(most important first):\n" + "\n".join(
                               f"   - {x['line']}" + (f": our decision changes if freight exceeds ₹{x['break_even']}/box" if x.get("break_even") else "")
                               for x in it["lines"])),
    "EVIDENCE": lambda it: f"Question {it['no']} ({it['key']}): {it['reason']}. Please send the supporting document.",
    "UNCOVERED_LINE": lambda it: f"You did not quote {it['line']} (annual quantity {it['qty']:,}). Would you like to quote it?",
}


def build_items(sf, rfx_id: int, vendor_id: int) -> list[dict]:
    with sf() as s:
        lines = {l.id: l for l in s.scalars(select(RfxLine).where(RfxLine.rfx_id == rfx_id).order_by(RfxLine.line_no))}
        qs = {q.rfx_line_id: q for q in s.scalars(select(NormalizedQuote).where(NormalizedQuote.vendor_id == vendor_id,
                                                                                  NormalizedQuote.rfx_line_id.in_(list(lines))))}
        refs = list(s.scalars(select(Reference).where(Reference.rfx_id == rfx_id, Reference.vendor_id == vendor_id,
                                                      Reference.interpretation == "AMBIGUOUS")))
        questions = {q.id: q for q in s.scalars(select(Question).where(Question.rfx_id == rfx_id))}
        elig = [e for e in s.scalars(select(EligibilityResult).where(EligibilityResult.vendor_id == vendor_id,
                                                                     EligibilityResult.question_id.in_(list(questions))))
                if e.state == "UNVERIFIED" and questions[e.question_id].section == "QUALITY"]
        for x in list(lines.values()) + list(qs.values()) + refs:
            s.expunge(x)
        elig = [(questions[e.question_id].no, questions[e.question_id].requirement_key, e.reason) for e in elig]
    sc = run_scenario(sf, rfx_id, ScenarioParams())  # formal, freight-aware: the decision we are protecting
    sens = {d["line_no"]: d for d in sc["decision_sensitive_lines"]}
    dep = {d["line_no"]: d for d in sc["freight_dependent_lines"] if d["vendor"] == next(
        (a["vendor"] for a in sc["awards"] if a["line_no"] == d["line_no"]), None)}
    won = {a["line_no"] for a in sc["awards"] if a["vendor_id"] == vendor_id}
    uncovered = {u["line_no"] for u in sc["uncovered_lines"]}

    def impact(n: int) -> Decimal:
        d = sens.get(n)
        if not d:
            return Decimal(0)
        return max((abs(Decimal(i["annual_inr_delta"])) for i in d["inputs"] if i.get("annual_inr_delta")), default=Decimal(1))

    items = []
    by_line_no = {l.line_no: l for l in lines.values()}
    for lid, q in sorted(qs.items(), key=lambda kv: lines[kv[0]].line_no):
        l = lines[lid]
        kinds = sorted({REASON_KIND[r] for r in (q.unit_reasons or []) if r in REASON_KIND}, key=KIND_ORDER.index)
        for k in kinds:
            if k == "GST":
                continue  # one response-level GST item below
            sug = next((t.get("suggestion") for t in q.trace or [] if t.get("suggestion")), None)
            asq = next((t.get("unit_as_stated") for t in q.trace or [] if t.get("step") == "evidence"), None)
            items.append({"kind": k, "line_no": l.line_no, "line": _q(l), "qty": l.annual_qty, "as_stated": asq,
                          "suggested": sug["suggested_unit_price"] if sug else None, "impact": impact(l.line_no)})
        if q.freight_basis == "UNKNOWN" and q.unit_price_inr_ex_gst and (l.line_no in sens or l.line_no in dep) \
                and (l.line_no in won or l.line_no in sens):
            items.append({"kind": "FREIGHT", "line_no": l.line_no, "line": _q(l), "qty": l.annual_qty,
                          "break_even": dep.get(l.line_no, {}).get("break_even_inr_per_box"), "impact": impact(l.line_no)})
    freight = sorted((i for i in items if i["kind"] == "FREIGHT"), key=lambda i: (-i["impact"], i["line_no"]))
    if freight:  # one response-level question, lines listed by importance
        items = [i for i in items if i["kind"] != "FREIGHT"]
        items.append({"kind": "FREIGHT", "line_no": None, "impact": freight[0]["impact"],
                      "lines": [{"line_no": i["line_no"], "line": i["line"], "break_even": i["break_even"]} for i in freight]})
    if any("GST_UNCLEAR" in (q.unit_reasons or []) for q in qs.values()):
        items.append({"kind": "GST", "line_no": None, "impact": Decimal(0)})
    for no, key, reason in sorted(elig):
        items.append({"kind": "EVIDENCE", "no": no, "key": key, "reason": reason, "line_no": None, "impact": Decimal(0)})
    quoted = {lines[lid].line_no for lid, q in qs.items() if q.unit_status != "MISSING"}
    for n in sorted(uncovered - quoted):
        items.append({"kind": "UNCOVERED_LINE", "line_no": n, "line": _q(by_line_no[n]), "qty": by_line_no[n].annual_qty,
                      "impact": Decimal(0)})
    for ref in refs:
        quote = (ref.evidence[0] or {}).get("quote") if ref.evidence else None
        items.append({"kind": "REFERENCE", "line_no": None, "text": quote or ref.text, "candidates": ref.candidates,
                      "impact": max((impact(c["line_no"]) for c in ref.candidates if c.get("line_no")), default=Decimal(0)),
                      "lines": {c["line_no"]: _q(by_line_no[c["line_no"]]) for c in ref.candidates if c.get("line_no")}})
    # sensitivity first (DL-28), then the fixed kind order, then line number
    items.sort(key=lambda i: (-i["impact"], KIND_ORDER.index(i["kind"]), i.get("line_no") or 0, i.get("no") or ""))
    for rank, it in enumerate(items, start=1):
        it["sensitivity_rank"] = rank
        it["decision_sensitive"] = it["impact"] > 0
        it["impact"] = str(it["impact"])
    return items


TERM_LABEL = {"PAYMENT": "Payment", "VALIDITY": "Validity", "LEAD_TIME": "Lead time", "MOQ": "MOQ", "TOOLING": "Tooling",
              "ESCALATION": "Escalation", "DISCOUNT_PCT": "Discount", "GST": "GST"}


def _reference_section(it: dict) -> list[str]:
    out = [f'You wrote: "{it["text"]}". This can be read two ways, and we will not assume either:', "",
           "(A) Prices: the lines below at your own last-year price for the same specification:"]
    a = [c for c in it["candidates"] if c["reading"] == "A_prices"]
    for c in a:
        line = it["lines"][c["line_no"]]
        if c.get("reason") == "REFERENCE_AMBIGUOUS" and c.get("candidate"):
            out.append(f"   - {line}: last year ₹{c['candidate']}/box")
        elif c.get("reason") == "BASELINE_SPEC_CHANGED":
            out.append(f"   - {line}: the specification has changed since last year; please quote a price")
        else:
            out.append(f"   - {line}: we have no last-year price from you; please quote a price")
    b = [c for c in it["candidates"] if c["reading"] == "B_terms"]
    out += ["", "(B) Commercial terms: your last-year terms for the points this response does not state:"]
    out += [f"   - {TERM_LABEL.get(c['term_type'], c['term_type'].replace('_', ' ').capitalize())}: {c['candidate']} {c.get('unit') or ''}".rstrip()
            for c in b] or ["   - none"]
    out += ["", "Freight is never taken from last year: please state it for this RFx.",
            "Please confirm which reading you meant: prices, terms, both, or neither."]
    return out


def render(rfx_title: str, vendor_name: str, items: list[dict]) -> str:
    out = [f"Subject: Clarification requested — {rfx_title}", "", f"Dear {vendor_name},", "",
           "Thank you for your response. Before we can compare it, please clarify the points below "
           "(listed in order of importance to our decision).", ""]
    for n, it in enumerate(items, start=1):
        if it["kind"] == "REFERENCE":
            out += [f"{n}. \"Same as last year\""] + ["   " + x if x else "" for x in _reference_section(it)]
        else:
            out.append(f"{n}. {TEMPLATES[it['kind']](it)}")
        out.append("")
    out += ["Please reply to this email; we will record your answers against each point.", "", "Regards,", "Procurement"]
    return "\n".join(out)


def build_pack(sf, rfx_id: int, vendor_id: int) -> dict:
    items = build_items(sf, rfx_id, vendor_id)
    with sf() as s:
        title, vendor = s.get(Rfx, rfx_id).title, s.get(Vendor, vendor_id)
        name, email = vendor.name, vendor.contact_email
    body = render(title, name, items)
    return {"vendor": name, "to": email, "items": items, "body": body,
            "content_hash": hashlib.sha256(body.encode()).hexdigest()[:16]}
