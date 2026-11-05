"""Primary-RFx flow for the vertical slice (DL-19, DL-27): brief pack → AI column mapping → buyer
confirmation → deterministic import → gap questions/answers → conformance → approve → send →
deliver messages one at a time (DL-23 submission linking). Questionnaire drafting: rfx/questionnaire.py."""
from __future__ import annotations

import email
import email.utils
import hashlib
import json
from datetime import datetime, timezone
from email import policy
from typing import Literal, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import (AuditEvent, Document, InboxMessage, Invitation, OutboxMessage, Response, Rfx, RfxLine, Vendor)
from app.llm.gateway import LLMGateway
from app.rfx.item_master import MappingProposal, import_rows, propose_mapping, read_item_master
from app.storage import Storage

BRIEF_PACK = "seed/brief_pack"
ITEM_MASTER_HINT = ".xlsx"
RFX_LEVEL_FIELDS = ["delivery_location", "dimension_convention", "validity_days", "gst_treatment", "unit", "currency", "freight_basis"]


class FlowError(RuntimeError):
    """Raised when a step is attempted out of order (maps to HTTP 409)."""


def _audit(s: Session, action: str, target: dict, before=None, after=None, reason=None, actor="buyer"):
    s.add(AuditEvent(actor=actor, action=action, target=target, before=before, after=after, reason=reason))


# --- 1. start: brief pack + mapping proposal -------------------------------------------------
def start_primary_rfx(sf: sessionmaker[Session], storage: Storage, gw: LLMGateway, title: str,
                      sandbox: bool = False) -> tuple[int, MappingProposal]:
    files = list(storage.iter_files(BRIEF_PACK))
    im = next((f for f in files if f.endswith(ITEM_MASTER_HINT)), None)
    if im is None:
        raise FlowError("brief pack has no item master (.xlsx)")
    sheet = read_item_master(storage.read_bytes(im))
    proposal = propose_mapping(gw, sheet)
    with sf.begin() as s:
        rfx = Rfx(title=title, kind="sandbox" if sandbox else "primary", origin="SANDBOX" if sandbox else "COPILOT_LIVE",
                  status="draft", response_basis={}, conformance=None)
        s.add(rfx)
        s.flush()
        for f in files:
            data = storage.read_bytes(f)
            s.add(Document(rfx_id=rfx.id, filename=f.split("/")[-1], mime="application/octet-stream",
                           sha256=hashlib.sha256(data).hexdigest(), storage_path=f, kind="brief_pack", parse_status="parsed"))
        _audit(s, "MAPPING_PROPOSED", {"rfx_id": rfx.id}, after=proposal.model_dump())
        return rfx.id, proposal


# --- 2. confirm mapping → deterministic import -------------------------------------------------
def confirm_mapping(sf: sessionmaker[Session], storage: Storage, rfx_id: int, mapping: dict[str, str]) -> dict:
    im = next(f for f in storage.iter_files(BRIEF_PACK) if f.endswith(ITEM_MASTER_HINT))
    result = import_rows(read_item_master(storage.read_bytes(im)), mapping)
    with sf.begin() as s:
        rfx = s.get(Rfx, rfx_id)
        if rfx is None or rfx.status != "draft":
            raise FlowError("RFx must exist and be a draft")
        for l in result.lines:
            s.add(RfxLine(rfx_id=rfx_id, line_no=l["line_no"], sku_code=l["sku_code"], description=l["description"],
                          item_type=l["item_type"] or "UNKNOWN", dims_mm=l["dims_mm"], blank_size_mm=l["blank_size_mm"],
                          ply=l["ply"] or 0, flute_profile=l["flute_profile"], layers=l["layers"], printing=l["printing"] or {},
                          annual_qty=l["annual_qty"] or 0,
                          reference_unit_weight_g=str(l["reference_unit_weight_g"]) if l["reference_unit_weight_g"] else None,
                          reference_weight_source=l["reference_weight_source"], food_contact=l["food_contact"],
                          requires_fsc=False, source_evidence=l["source_evidence"]))
        _audit(s, "MAPPING_CONFIRMED_AND_IMPORTED", {"rfx_id": rfx_id}, after={"mapping": mapping, "lines": len(result.lines)})
    return {"lines": len(result.lines), "line_gaps": result.line_gaps, "rfx_gaps": rfx_gaps(sf, rfx_id)}


def rfx_gaps(sf: sessionmaker[Session], rfx_id: int) -> list[str]:
    with sf() as s:
        rfx = s.get(Rfx, rfx_id)
        basis = dict(rfx.response_basis or {})
        basis["delivery_location"] = rfx.delivery_location
        basis["scope"] = rfx.scope
        return [f for f in ["scope"] + RFX_LEVEL_FIELDS if basis.get(f) in (None, "")]


# --- 3. gap answers → patch (AI reads the buyer's words + the commercial policy) -------------
class Quoted(BaseModel):
    value: str
    quote: str = Field(description="Verbatim words from the buyer's reply or the policy text")


class GapPatch(BaseModel):
    scope: Optional[Quoted] = Field(None, description="One sentence: what is being bought, how much, for what period")
    delivery_location: Optional[Quoted] = None
    dimension_convention: Optional[Quoted] = Field(None, description="'internal' or 'external'")
    validity_days: Optional[Quoted] = None
    gst_treatment: Optional[Quoted] = Field(None, description="e.g. 'prices exclusive of GST'")
    unit: Optional[Quoted] = None
    currency: Optional[Quoted] = None
    freight_basis: Optional[Quoted] = None


GAP_SYSTEM = """You turn a buyer's reply and their commercial policy into the RFx scope and response-basis values.
Fill a field only if the buyer or the policy states it; quote the exact words. Leave others null.
scope: one sentence saying what is being bought, roughly how much, and for what period."""


def policy_text(storage: Storage) -> str:
    """The buyer's own policy documents: the second source a gap answer may quote (besides the buyer's reply)."""
    import docx
    from io import BytesIO
    out = []
    for f in sorted(storage.iter_files(BRIEF_PACK)):
        if f.endswith(".docx"):
            out += [p.text for p in docx.Document(BytesIO(storage.read_bytes(f))).paragraphs if p.text.strip()]
    return "\n".join(out)


def propose_gap_patch(gw: LLMGateway, sf, storage: Storage, rfx_id: int, buyer_text: str) -> GapPatch:
    gaps = rfx_gaps(sf, rfx_id)
    content = f"Open fields: {', '.join(gaps)}\n\nBuyer reply:\n{buyer_text}\n\nPolicy text:\n" + policy_text(storage)
    return gw.structured("copilot", GapPatch, [{"role": "user", "content": content}], system=GAP_SYSTEM, prompt_version="gaps_v1")


def apply_gap_patch(sf, rfx_id: int, patch: GapPatch, source_text: str) -> list[str]:
    """Buyer-accepted patch. A value is applied only if its quote really appears in the source text."""
    applied, rejected = {}, []
    for f, q in patch.model_dump().items():
        if q is None:
            continue
        if " ".join(q["quote"].lower().split()) not in " ".join(source_text.lower().split()):
            rejected.append(f)
            continue
        applied[f] = q["value"]
    with sf.begin() as s:
        rfx = s.get(Rfx, rfx_id)
        before = {"response_basis": dict(rfx.response_basis or {}), "delivery_location": rfx.delivery_location,
                  "scope": rfx.scope}
        basis = dict(rfx.response_basis or {})
        for f, v in applied.items():
            if f == "delivery_location":
                rfx.delivery_location = v
            elif f == "scope":
                rfx.scope = v
            elif f == "validity_days":
                basis[f] = int("".join(ch for ch in v if ch.isdigit()) or 0) or v
            else:
                basis[f] = v
        rfx.response_basis = basis
        _audit(s, "GAP_PATCH_APPLIED", {"rfx_id": rfx_id}, before=before, after={"applied": applied, "rejected": rejected})
    return rejected


# --- 4. conformance (RFX-10; line + basis part in M6a) ---------------------------------------
LINE_FIELDS = ["item_type", "dims_mm", "blank_size_mm", "ply", "flute_profile", "annual_qty", "reference_unit_weight_g", "food_contact"]


def _line_view(l: dict) -> dict:
    v = {k: l.get(k) for k in LINE_FIELDS}
    v["gsm"] = [x.get("gsm") for x in l.get("layers") or []]
    v["printing_colours"] = (l.get("printing") or {}).get("colours")
    if v["reference_unit_weight_g"] is not None:
        v["reference_unit_weight_g"] = int(v["reference_unit_weight_g"])
    return v


def conformance(sf, rfx_id: int, canonical: dict) -> dict:
    with sf.begin() as s:
        rfx = s.get(Rfx, rfx_id)
        lines = {l.sku_code: {"item_type": l.item_type, "dims_mm": l.dims_mm, "blank_size_mm": l.blank_size_mm, "ply": l.ply,
                              "flute_profile": l.flute_profile, "annual_qty": l.annual_qty, "layers": l.layers, "printing": l.printing,
                              "reference_unit_weight_g": l.reference_unit_weight_g, "food_contact": l.food_contact}
                 for l in s.scalars(select(RfxLine).where(RfxLine.rfx_id == rfx_id))}
        canon = {l["sku_code"]: l for l in canonical["lines"]}
        diffs = [{"sku": k, "difference": "missing from draft"} for k in sorted(set(canon) - set(lines))]
        diffs += [{"sku": k, "difference": "not in canonical spec"} for k in sorted(set(lines) - set(canon))]
        for sku in sorted(set(canon) & set(lines)):
            a, b = _line_view(lines[sku]), _line_view(canon[sku])
            for f in a:
                if a[f] != b[f]:
                    diffs.append({"sku": sku, "field": f, "draft": a[f], "canonical": b[f]})
        basis = dict(rfx.response_basis or {})
        cb = canonical["response_basis"]
        for f, cv in [("delivery_location", canonical["delivery_location"]), ("dimension_convention", canonical["dimension_convention"]),
                      ("validity_days", cb["validity_days"]), ("gst_treatment", cb["gst_treatment"])]:
            dv = rfx.delivery_location if f == "delivery_location" else basis.get(f)
            if str(dv).strip().lower() != str(cv).strip().lower():
                diffs.append({"field": f, "draft": dv, "canonical": cv})
        from app.rfx.questionnaire import questionnaire_differences
        diffs += questionnaire_differences(s, rfx_id, canonical)
        result = {"conforms": not diffs, "differences": diffs, "checked_at": datetime.now(timezone.utc).isoformat(),
                  "scope": "lines, response basis and questionnaire"}
        rfx.conformance = result
        _audit(s, "CONFORMANCE_CHECKED", {"rfx_id": rfx_id}, after={"conforms": result["conforms"], "n": len(diffs)})
        return result


# --- 5. approve, send, deliver ------------------------------------------------------------------
def approve(sf, rfx_id: int) -> None:
    with sf.begin() as s:
        rfx = s.get(Rfx, rfx_id)
        if rfx.kind != "sandbox" and not (rfx.conformance or {}).get("conforms"):
            raise FlowError("RFx must pass the conformance check before approval")
        rfx.status = "approved"
        _audit(s, "RFX_APPROVED", {"rfx_id": rfx_id})


def send(sf, storage: Storage, rfx_id: int) -> int:
    vendors = json.loads(storage.read_text("seed/vendors.json"))
    with sf.begin() as s:
        rfx = s.get(Rfx, rfx_id)
        if rfx.status != "approved":
            raise FlowError("only an approved RFx can be sent")
        for v in vendors:
            vendor = s.scalar(select(Vendor).where(Vendor.contact_email == v["email"])) or Vendor(name=v["name"], contact_email=v["email"])
            s.add(vendor)
            s.flush()
            s.add(Invitation(rfx_id=rfx_id, vendor_id=vendor.id, sent_at=datetime.now(timezone.utc), status="AWAITING_RESPONSE"))
            s.add(OutboxMessage(to_addr=v["email"], subject=f"RFx: {rfx.title}",
                                body=f"Dear {v['name']},\n\nPlease find our RFx attached. Reply in any format.\n", attachments=["rfx.pdf"]))
        rfx.status = "sent"
        _audit(s, "RFX_SENT", {"rfx_id": rfx_id}, after={"vendors": len(vendors)})
    return len(vendors)


def deliver_next(sf, storage: Storage, rfx_id: int) -> dict | None:
    """Deliver the next prepared message. Refused unless the RFx conforms (DL-19)."""
    with sf.begin() as s:
        rfx = s.get(Rfx, rfx_id)
        if rfx.kind == "sandbox":
            raise FlowError("the sandbox never receives the prepared responses (DL-17); upload files instead")
        if rfx.status != "sent" or not (rfx.conformance or {}).get("conforms"):
            raise FlowError("prepared responses can only be delivered to a sent, conforming RFx")
        delivered = {sub["path"] for r in s.scalars(select(Response).where(Response.rfx_id == rfx_id))
                     for sub in (r.submissions or [])}  # per RFx: the fallback and the live draft each get the inbox
        pending = [f for f in storage.iter_files("inbox") if f.endswith(".eml") and f not in delivered]
        if not pending:
            return None
        path = pending[0]
        msg = email.message_from_bytes(storage.read_bytes(path), policy=policy.default)
        addr = email.utils.parseaddr(str(msg["From"]))[1]
        vendor = s.scalar(select(Vendor).where(Vendor.contact_email == addr))
        if vendor is None:
            raise FlowError(f"sender {addr} is not an invited vendor")
        inbox = InboxMessage(from_addr=addr, subject=str(msg["Subject"]), storage_path=path)
        s.add(inbox)
        s.flush()
        resp = s.scalar(select(Response).where(Response.rfx_id == rfx_id, Response.vendor_id == vendor.id))
        kind = "QUOTE" if not resp else "OTHER"  # refined by extraction (questionnaire vs quote)
        if resp is None:
            resp = Response(rfx_id=rfx_id, vendor_id=vendor.id, status="received", submissions=[])
            s.add(resp)
        resp.submissions = list(resp.submissions or []) + [{"inbox_message_id": inbox.id, "path": path, "kind": kind}]
        resp.status = "received"
        inv = s.scalar(select(Invitation).where(Invitation.rfx_id == rfx_id, Invitation.vendor_id == vendor.id))
        if inv:
            inv.status = "RESPONDED"
        _audit(s, "MESSAGE_DELIVERED", {"rfx_id": rfx_id, "vendor_id": vendor.id}, after={"path": path})
        return {"path": path, "vendor": vendor.name, "submissions": len(resp.submissions)}


# --- 6. seeded fallback, sandbox, upload, header (RFX-8/11, DL-17, J8) ---------------------------------
CANONICAL = "seed/canonical_rfx.json"


def seeded_fallback(sf, storage: Storage, title: str | None = None) -> int:
    """RFX-8: the canonical spec loaded as a visibly labelled fallback (origin SEEDED_FALLBACK). Read-only use
    of the canonical file; the file itself is never changed."""
    canon = json.loads(storage.read_text(CANONICAL))
    from app.db.models import Question
    with sf.begin() as s:
        rfx = Rfx(title=title or f"{canon['title']} (seeded fallback)", scope=canon.get("scope"), kind="primary",
                  origin="SEEDED_FALLBACK", status="draft",
                  response_basis={k: canon["response_basis"][k] for k in ("validity_days", "gst_treatment", "unit", "currency",
                                                                           "freight_basis")}
                  | {"dimension_convention": canon["dimension_convention"]},
                  delivery_location=canon["delivery_location"], canonical_spec_version=canon["rfx_code"],
                  terms=[{"type": t["type"], "text": t["text"], "source": {"canonical_spec": canon["rfx_code"]}} for t in canon["terms"]])
        s.add(rfx)
        s.flush()
        for l in canon["lines"]:
            s.add(RfxLine(rfx_id=rfx.id, line_no=l["line_no"], sku_code=l["sku_code"], description=l["description"],
                          item_type=l["item_type"], dims_mm=l["dims_mm"], blank_size_mm=l["blank_size_mm"], ply=l["ply"],
                          flute_profile=l["flute_profile"], layers=l["layers"], printing=l["printing"], annual_qty=l["annual_qty"],
                          reference_unit_weight_g=str(l["reference_unit_weight_g"]) if l.get("reference_unit_weight_g") else None,
                          reference_weight_source=l.get("reference_weight_source"), food_contact=l["food_contact"],
                          requires_fsc=l.get("requires_fsc", False), source_evidence=[{"canonical_spec": canon["rfx_code"]}]))
        for q in canon["questionnaire"]:
            s.add(Question(rfx_id=rfx.id, no=q["no"], section=q["section"], requirement_key=q["requirement_key"],
                           applicability=q["applicability"], text=q["text"], answer_type=q["answer_type"], mandatory=q["mandatory"],
                           pass_rule=q["pass_rule"], evidence_required=q["evidence_required"], evidence_doc_type=q["evidence_doc_type"]))
        _audit(s, "SEEDED_FALLBACK_LOADED", {"rfx_id": rfx.id}, after={"canonical_spec": canon["rfx_code"]})
        rid = rfx.id
    conformance(sf, rid, canon)
    return rid


def create_sandbox(sf, title: str = "Sandbox RFx") -> int:
    """DL-17: free-form drafting happens here; it can receive uploads but never the prepared inbox."""
    with sf.begin() as s:
        rfx = Rfx(title=title, kind="sandbox", origin="SANDBOX", status="draft", response_basis={})
        s.add(rfx)
        s.flush()
        _audit(s, "SANDBOX_CREATED", {"rfx_id": rfx.id})
        return rfx.id


def upload_response(sf, storage: Storage, rfx_id: int, vendor_name: str, vendor_email: str, filename: str, data: bytes,
                    actor: str = "buyer") -> dict:
    """J8 / DIS: a response file uploaded by the buyer to an existing or new vendor; same pipeline after this."""
    import re
    from email.message import EmailMessage
    with sf.begin() as s:
        rfx = s.get(Rfx, rfx_id)
        if rfx is None:
            raise FlowError("no such RFx")
        if rfx.status != "sent" and rfx.kind != "sandbox":
            raise FlowError("responses can be uploaded only to a sent RFx (or the sandbox)")
        vendor = s.scalar(select(Vendor).where(Vendor.contact_email == vendor_email))
        if vendor is None:
            vendor = Vendor(name=vendor_name, contact_email=vendor_email)
            s.add(vendor)
            s.flush()
        if s.scalar(select(Invitation).where(Invitation.rfx_id == rfx_id, Invitation.vendor_id == vendor.id)) is None:
            s.add(Invitation(rfx_id=rfx_id, vendor_id=vendor.id, sent_at=None, status="AWAITING_RESPONSE"))
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename)[:80] or "upload"
        if safe.lower().endswith(".eml"):
            raw = data
        else:  # wrap a bare file as a message so it enters the same pipeline (D1 = note, D2 = the file)
            msg = EmailMessage()
            msg["From"], msg["To"], msg["Subject"] = vendor_email, "procurement@buyer.example", f"Upload: {safe}"
            msg.set_content(f"Uploaded by {actor}: {safe}")
            mime = {"xlsx": ("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                    "docx": ("application", "vnd.openxmlformats-officedocument.wordprocessingml.document"),
                    "pdf": ("application", "pdf"), "png": ("image", "png"), "jpg": ("image", "jpeg"),
                    "jpeg": ("image", "jpeg")}.get(safe.rsplit(".", 1)[-1].lower(), ("application", "octet-stream"))
            msg.add_attachment(data, maintype=mime[0], subtype=mime[1], filename=safe)
            raw = msg.as_bytes()
        n = len(list(s.scalars(select(InboxMessage)))) + 1
        path = f"uploads/rfx{rfx_id}/{n:03d}_{safe}" + ("" if safe.lower().endswith(".eml") else ".eml")
        storage.write_bytes(path, raw)
        inbox = InboxMessage(from_addr=vendor_email, subject=f"Upload: {safe}", storage_path=path)
        s.add(inbox)
        s.flush()
        resp = s.scalar(select(Response).where(Response.rfx_id == rfx_id, Response.vendor_id == vendor.id))
        if resp is None:
            resp = Response(rfx_id=rfx_id, vendor_id=vendor.id, status="received", submissions=[])
            s.add(resp)
        resp.submissions = list(resp.submissions or []) + [{"inbox_message_id": inbox.id, "path": path, "kind": "UPLOAD"}]
        resp.status = "received"
        inv = s.scalar(select(Invitation).where(Invitation.rfx_id == rfx_id, Invitation.vendor_id == vendor.id))
        inv.status = "RESPONDED"
        _audit(s, "RESPONSE_UPLOADED", {"rfx_id": rfx_id, "vendor_id": vendor.id}, after={"path": path, "filename": safe},
               actor=actor)
        return {"vendor_id": vendor.id, "path": path, "submissions": len(resp.submissions)}


def header(sf, rfx_id: int) -> dict:
    """RFX-11: origin, transcript (model calls), accepted patches and the conformance result."""
    from app.db.models import LlmCall
    with sf() as s:
        rfx = s.get(Rfx, rfx_id)
        if rfx is None:
            raise FlowError("no such RFx")
        patches = [{"action": e.action, "at": e.at.isoformat(), "actor": e.actor}
                   for e in s.scalars(select(AuditEvent).order_by(AuditEvent.id)) if (e.target or {}).get("rfx_id") == rfx_id
                   and e.action in ("MAPPING_PROPOSED", "MAPPING_CONFIRMED_AND_IMPORTED", "GAP_PATCH_APPLIED",
                                    "QUESTIONNAIRE_APPLIED", "SEEDED_FALLBACK_LOADED", "CONFORMANCE_CHECKED", "RFX_APPROVED", "RFX_SENT")]
        calls = [{"route": c.route, "status": c.status, "at": c.created_at.isoformat() if getattr(c, "created_at", None) else None}
                 for c in s.scalars(select(LlmCall).order_by(LlmCall.id)) if c.route.startswith("copilot")]
        return {"rfx_id": rfx.id, "title": rfx.title, "scope": rfx.scope, "kind": rfx.kind, "origin": rfx.origin, "status": rfx.status,
                "label": {"COPILOT_LIVE": "Drafted live by the co-pilot", "SEEDED_FALLBACK": "Seeded fallback (canonical spec)",
                          "SANDBOX": "Sandbox — free-form drafting"}[rfx.origin],
                "conformance": rfx.conformance, "terms": rfx.terms, "response_basis": rfx.response_basis,
                "delivery_location": rfx.delivery_location, "patches": patches, "copilot_calls": calls}
