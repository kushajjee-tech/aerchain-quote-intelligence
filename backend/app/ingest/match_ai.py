"""AI match proposal for vendor lines the deterministic pre-match left over (architecture §7.5).
The model proposes; code enforces one-to-one, never overrides a deterministic match, and keeps LOW as
UNRESOLVED (MATCH_LOW) until the buyer resolves it."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from app.ingest.verify import VerifiedLine
from app.llm.prompts import MATCH_SYSTEM, MATCH_V1, match_user


class MatchProposal(BaseModel):
    vendor_line_ref: str
    rfx_line_no: Optional[int] = None
    confidence: Literal["HIGH", "LOW"]
    reason: str


class MatchProposals(BaseModel):
    proposals: list[MatchProposal]


def _rfx_text(rfx_lines: list[dict]) -> str:
    return "\n".join(f"- line {l['line_no']}: {l['sku_code']} | {l['description']} | {l['item_type']} | {l['ply']}-ply "
                     f"{l.get('flute_profile') or ''} | {(l.get('dims_mm') or {}).get('L')}x{(l.get('dims_mm') or {}).get('W')}x"
                     f"{(l.get('dims_mm') or {}).get('H')} mm" for l in rfx_lines)


def propose_matches(gw, rfx_lines: list[dict], unmatched: list[VerifiedLine], taken: set[int]) -> dict[str, dict]:
    """Returns {vendor_line_ref: {"line_no", "confidence", "reason"}} for accepted proposals."""
    if not unmatched:
        return {}
    vtext = "\n".join(f"- ref {v.quote.vendor_line_ref}: {v.quote.description_as_stated}"
                      + (f" | code {v.quote.item_code}" if v.quote.item_code else "") for v in unmatched)
    out = gw.structured("match", MatchProposals, [{"role": "user", "content": match_user(_rfx_text(rfx_lines), vtext)}],
                        system=MATCH_SYSTEM, prompt_version=MATCH_V1)
    valid_refs = {v.quote.vendor_line_ref for v in unmatched}
    valid_lines = {l["line_no"] for l in rfx_lines}
    accepted: dict[str, dict] = {}
    for p in out.proposals:
        if p.vendor_line_ref not in valid_refs or p.rfx_line_no not in valid_lines or p.vendor_line_ref in accepted:
            continue
        accepted[p.vendor_line_ref] = {"line_no": p.rfx_line_no, "confidence": p.confidence, "reason": p.reason,
                                       "conflicts_with_deterministic": p.rfx_line_no in taken}
    return accepted
