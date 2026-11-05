"""Original vendor documents (FN-10, REV-3): list each vendor's submissions and open any original file as received.
Read through the storage module only; served inline so PDFs and images open in the browser."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import select

from app.db.models import Response as VendorResponse
from app.ingest.parsers import parse_message

router = APIRouter(prefix="/rfx")
_PARSED: dict[str, tuple] = {}  # stored message path → parsed message (messages are immutable once stored)


def _submissions(request: Request, rfx_id: int, vendor_id: int):
    st = request.app.state
    with st.session_factory() as s:
        r = s.scalar(select(VendorResponse).where(VendorResponse.rfx_id == rfx_id, VendorResponse.vendor_id == vendor_id))
        subs = list(r.submissions or []) if r else []
    out = []
    for sub in subs:
        key = f"{st.settings.data_root}|{sub['path']}"
        if key not in _PARSED:
            _PARSED[key] = parse_message(st.storage.read_bytes(sub["path"]))
        msg, docs = _PARSED[key]
        out.append((sub, msg, docs))
    return out


@router.get("/{rfx_id}/vendors/{vendor_id}/documents")
def list_documents(rfx_id: int, vendor_id: int, request: Request):
    items = []
    for sub, msg, docs in _submissions(request, rfx_id, vendor_id):
        for d in docs:
            items.append({"message": sub["path"].split("/")[-1], "ref": d.ref, "filename": d.filename, "kind": d.kind,
                          "parse_status": d.parse_status, "failure_reason": d.failure_reason,
                          "ocr": {k: d.meta[k] for k in ("path", "mean_conf", "ocr_lines", "rotation_deg") if k in d.meta} or None,
                          "url": f"/api/rfx/{rfx_id}/vendors/{vendor_id}/file?name={quote(d.filename)}"})
    return items


@router.get("/{rfx_id}/vendors/{vendor_id}/file")
def open_file(rfx_id: int, vendor_id: int, name: str, request: Request):
    for sub, msg, docs in _submissions(request, rfx_id, vendor_id):
        for d in docs:
            if d.filename == name:
                if d.kind == "email_body":
                    text = "\n".join(u.text for u in d.units) or ""
                    return Response(f"From: {msg.from_addr}\nDate: {msg.date}\nSubject: {msg.subject}\n\n{text}".encode(),
                                    media_type="text/plain; charset=utf-8")
                return Response(d.data, media_type=d.mime or "application/octet-stream",
                                headers={"Content-Disposition": f'inline; filename="{quote(d.filename)}"'})
    raise HTTPException(404, "no such document for this vendor")
