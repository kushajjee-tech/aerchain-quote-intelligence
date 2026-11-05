"""eml → body document (one unit per non-empty line) + attachment payloads (architecture §6.1)."""
from __future__ import annotations

import email
from dataclasses import dataclass, field
from email import policy

from app.ingest.evidence import EvidenceUnit, ParsedDocument


@dataclass
class ParsedMessage:
    from_addr: str
    subject: str
    message_id: str
    in_reply_to: str | None
    date: str | None
    body: ParsedDocument
    attachments: list[tuple[str, str, bytes]] = field(default_factory=list)  # filename, mime, bytes


def parse_eml(ref: str, data: bytes) -> ParsedMessage:
    msg = email.message_from_bytes(data, policy=policy.default)
    part = msg.get_body(preferencelist=("plain", "html"))
    text = part.get_content() if part is not None else ""
    if part is not None and part.get_content_type() == "text/html":
        import re
        text = re.sub(r"<[^>]+>", " ", text)
    body = ParsedDocument(ref=ref, filename="(email body)", mime="text/plain", kind="email_body", data=text.encode())
    for i, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            body.units.append(EvidenceUnit(f"{ref}:l{i}", ref, "email_line", {"line_no": i}, line.strip()))
    atts = [(p.get_filename() or f"attachment-{i}", p.get_content_type(), p.get_payload(decode=True) or b"")
            for i, p in enumerate(msg.iter_attachments(), start=1)]
    return ParsedMessage(
        from_addr=str(msg.get("From", "")), subject=str(msg.get("Subject", "")),
        message_id=str(msg.get("Message-ID", "")), in_reply_to=msg.get("In-Reply-To"),
        date=msg.get("Date"), body=body, attachments=atts,
    )
