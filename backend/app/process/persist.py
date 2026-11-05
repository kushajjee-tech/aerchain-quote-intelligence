"""Persist Phase B results as NormalizedQuote rows + the processing-set snapshot (derived data:
replaced on every recompute; the audit trail lives in append-only tables)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import NormalizedQuote, ProcessingSet, Response
from app.normalize.engine import NormalizedCell
from app.process.phase_b import snapshot_hash


def _s(x):
    return None if x is None else str(x)


def persist(sf: sessionmaker[Session], rfx_id: int, vendor_ids: dict[str, int], line_ids: dict[int, int],
            cells: dict[str, dict[int, NormalizedCell]]) -> str:
    snap = snapshot_hash(cells)
    with sf.begin() as s:
        s.execute(delete(NormalizedQuote).where(NormalizedQuote.rfx_line_id.in_(list(line_ids.values()))))
        for v, per in cells.items():
            for n, c in per.items():
                s.add(NormalizedQuote(
                    rfx_line_id=line_ids[n], vendor_id=vendor_ids[v], unit_price_inr_ex_gst=_s(c.unit_price_inr_ex_gst),
                    unit_status=str(c.unit_status), unit_reasons=c.reasons, landed_inr_ex_gst=_s(c.landed_inr_ex_gst),
                    landed_status=str(c.landed_status), freight_basis=c.freight_basis,
                    freight_inr_per_box=_s(c.freight_inr_per_box), weight_source=c.weight_source, weight_g=_s(c.weight_g),
                    constant_set_version=c.constant_set_version, flags=c.flags, trace=c.trace, fingerprint=snap[:16]))
        ps = s.scalar(select(ProcessingSet).where(ProcessingSet.rfx_id == rfx_id))
        if ps is None:
            ps = ProcessingSet(rfx_id=rfx_id)
            s.add(ps)
        open_states = [r.status for r in s.scalars(select(Response).where(Response.rfx_id == rfx_id))
                       if r.status != "processed"]
        # Phase B over an incomplete set is provisional: a failed or unprocessed response is reported, not hidden
        ps.phase_b_status = "provisional" if open_states else "final"
        ps.snapshot_hash, ps.last_recompute_at = snap, datetime.now(timezone.utc)
    return snap
