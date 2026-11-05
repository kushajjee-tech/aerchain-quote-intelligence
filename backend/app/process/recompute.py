"""Buyer resolutions and global recompute (PRD §6.5, VAL-5, REV-4; DL-7, DL-9, DL-20).

Phase A cells are stored once per processing run. Every recompute:
  1. loads the stored Phase A cells;
  2. applies active resolutions that change a Phase A value (Correct / Override / Mark missing /
     confirmed reference), so corrected values feed the peer medians (VAL-5);
  3. runs the full Phase B across vendors;
  4. re-applies every resolution after Phase B (sticky: a resolved cell is never downgraded; a new
     check failure adds NEW_WARNING_AFTER_REVIEW instead).
A resolution whose source fingerprint no longer matches the cell is marked stale
(STALE_SOURCE_CHANGED) and not applied; the review item reopens.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import delete, select

from app.db.models import AuditEvent, PhaseACell, Resolution, Scenario
from app.domain.enums import ASSUMPTION_REASONS, ValueStatus as S
from app.normalize.engine import NormalizedCell
from app.normalize.money import q4
from app.process.cells_io import from_json, to_json
from app.process.persist import persist
from app.process.phase_b import phase_b

CELL_TYPES = ("ACCEPT", "CORRECT", "MARK_MISSING", "OVERRIDE")
REFERENCE_CHOICES = ("prices", "terms", "both", "neither")


class ResolutionError(ValueError):
    pass


# --- fingerprints -----------------------------------------------------------------------------
def raw_fingerprint(c: NormalizedCell) -> str:
    """Source-side identity of a cell: what was stated, not what we derived from it (§6.5)."""
    quoted = next((t for t in c.trace if t.get("step") == "as_quoted"), {})
    ref = next((t for t in c.trace if t.get("step") == "reference"), {})
    ev = next((t for t in c.trace if t.get("step") == "evidence"), {})
    derived = {"OUTLIER", "UNIT_SUSPECT", "FX_RATE", "FX_RATE_MISSING", "WEIGHT_ESTIMATED", "METHOD_CONSTANTS",
               "WEIGHT_MISMATCH", "EVIDENCE_NOT_FOUND"}
    raw = [quoted.get("value"), quoted.get("unit_class"), ref.get("candidate"), ref.get("reason"),
           [x.get("quote") for x in ev.get("cites", [])], sorted(r for r in c.reasons if r not in derived)]
    return hashlib.sha256(json.dumps(raw).encode()).hexdigest()[:16]


def candidate_value(c: NormalizedCell) -> Decimal | None:
    if c.unit_price_inr_ex_gst is not None:
        return c.unit_price_inr_ex_gst
    v = next((t.get("candidate") for t in reversed(c.trace) if t.get("step") == "candidate" and t.get("candidate")), None)
    return Decimal(v) if v is not None else None


# --- storage of Phase A -----------------------------------------------------------------------
def store_phase_a(sf, rfx_id: int, per_vendor: dict[str, dict[int, NormalizedCell]], inputs: dict | None = None) -> None:
    with sf.begin() as s:
        s.execute(delete(PhaseACell).where(PhaseACell.rfx_id == rfx_id,
                                           PhaseACell.vendor_id.in_([int(v) for v in per_vendor])))
        for v, per in per_vendor.items():
            for n, c in per.items():
                s.add(PhaseACell(rfx_id=rfx_id, vendor_id=int(v), line_no=n, cell=to_json(c),
                                 inputs=((inputs or {}).get(v) or {}).get(n)))


def drop_vendor_cells(sf, rfx_id: int, vendor_id: int) -> None:
    with sf.begin() as s:
        s.execute(delete(PhaseACell).where(PhaseACell.rfx_id == rfx_id, PhaseACell.vendor_id == vendor_id))


def load_phase_a(sf, rfx_id: int) -> dict[str, dict[int, NormalizedCell]]:
    out: dict[str, dict[int, NormalizedCell]] = {}
    with sf() as s:
        for row in s.scalars(select(PhaseACell).where(PhaseACell.rfx_id == rfx_id)):
            out.setdefault(str(row.vendor_id), {})[row.line_no] = from_json(row.cell)
    return out


def _resolutions(s, rfx_id: int) -> list[Resolution]:
    return [r for r in s.scalars(select(Resolution).order_by(Resolution.id))
            if (r.target or {}).get("rfx_id") == rfx_id and r.state == "active"]


# --- applying resolutions ---------------------------------------------------------------------
def _with_landed(c: NormalizedCell, price: Decimal | None, status: S) -> NormalizedCell:
    if price is None:
        return replace(c, unit_price_inr_ex_gst=None, unit_status=status, landed_inr_ex_gst=None, landed_status=status)
    if c.freight_basis == "INCLUDED" or (c.freight_basis in ("STATED", "ESTIMATED") and c.freight_inr_per_box is not None):
        return replace(c, unit_price_inr_ex_gst=q4(price), unit_status=status,
                       landed_inr_ex_gst=q4(price + (c.freight_inr_per_box or Decimal(0))), landed_status=status)
    return replace(c, unit_price_inr_ex_gst=q4(price), unit_status=status, landed_inr_ex_gst=None,
                   landed_status=S.NOT_CONVERTIBLE)


def _confirm_reference(c: NormalizedCell) -> NormalizedCell | None:
    """Reading A (DL-20): only same-vendor, same-spec candidates (REFERENCE_AMBIGUOUS) become ASSUMED."""
    ref = next((t for t in c.trace if t.get("step") == "reference"), None)
    if not ref or ref.get("reason") != "REFERENCE_AMBIGUOUS" or not ref.get("candidate"):
        return None
    reasons = sorted((set(c.reasons) - {"REFERENCE_AMBIGUOUS", "EVIDENCE_NOT_FOUND"}) | {"BASELINE_REFERENCE"})
    flags = set(c.flags)
    if ref.get("baseline_freight_basis") == "INCLUDED" and c.freight_basis != "INCLUDED":
        flags.add("FREIGHT_BASIS_CHANGED")
    trace = c.trace + [{"step": "reference_confirmed", "output": ref["candidate"],
                        "label": "buyer confirmed 'prices': vendor's own last-year price, same spec; freight from this year only (DL-8)"}]
    out = replace(c, reasons=reasons, flags=sorted(flags), trace=trace, auto_verify_candidate=False)
    return _with_landed(out, Decimal(ref["candidate"]), S.ASSUMED)


def _pre_b(cells, res: list[Resolution]) -> tuple[dict, dict]:
    """Apply value-changing resolutions to Phase A; return (cells, sticky map for the post-B pass)."""
    cells = {v: dict(per) for v, per in cells.items()}
    sticky: dict[tuple[str, int], Resolution] = {}
    for r in res:
        t = r.target
        v = str(t["vendor_id"])
        if r.type == "FREIGHT_ESTIMATE":
            continue
        if r.type == "REFERENCE_CONFIRMATION":
            if r.choice in ("prices", "both"):
                for n, c in cells.get(v, {}).items():
                    nc = _confirm_reference(c)
                    if nc is not None:
                        cells[v][n] = nc
            continue
        n = int(t["line_no"])
        c = cells.get(v, {}).get(n)
        if c is None:
            continue
        if r.type == "MARK_MISSING":
            cells[v][n] = _with_landed(replace(c, reasons=[], trace=c.trace + [{"step": "resolution", "type": r.type}]),
                                       None, S.MISSING)
        elif r.type in ("CORRECT", "OVERRIDE"):
            keep = [x for x in c.reasons if x in ASSUMPTION_REASONS]
            flags = sorted(set(c.flags) | ({"OVERRIDE"} if r.type == "OVERRIDE" else set()))
            nc = replace(c, reasons=keep, flags=flags,
                         trace=c.trace + [{"step": "resolution", "type": r.type, "value": r.value, "reason": r.reason}])
            cells[v][n] = _with_landed(nc, Decimal(r.value), S.ASSUMED if keep else S.VERIFIED)
        sticky[(v, n)] = r
    return cells, sticky


def _post_b(final, pre, sticky: dict) -> dict:
    for (v, n), r in sticky.items():
        if r.type == "MARK_MISSING":
            final[v][n] = pre[v][n]
            continue
        b = final[v][n]
        if r.type == "ACCEPT":  # accepted reasons were recorded on the resolution
            price, known = candidate_value(pre[v][n]), set(filter(None, (r.choice or "").split(",")))
        else:  # CORRECT / OVERRIDE: Phase A reasons were cleared; anything Phase B adds is new
            price, known = pre[v][n].unit_price_inr_ex_gst, set(pre[v][n].reasons)
        new = sorted(set(b.reasons) - known - ASSUMPTION_REASONS)
        if r.type == "ACCEPT" and r.value and price is not None and Decimal(r.value) != price:
            new = sorted(set(new) | {"VALUE_CHANGED_AFTER_REVIEW"})  # FX or constants moved an accepted number
        keep = sorted({x for x in b.reasons if x in ASSUMPTION_REASONS})
        flags = set(b.flags) | ({"OVERRIDE"} if r.type == "OVERRIDE" else set())
        if new:
            flags.add("NEW_WARNING_AFTER_REVIEW")
        trace = b.trace + [{"step": "sticky_resolution", "resolution_id": r.id, "type": r.type,
                            "new_warnings": new, "label": "recompute never undoes a buyer resolution (§6.5)"}]
        status = S.ASSUMED if keep else S.VERIFIED
        final[v][n] = _with_landed(replace(b, reasons=sorted(set(keep) | set(new)), flags=sorted(flags), trace=trace),
                                   price, status)
    return final


def _apply_freight_estimates(final, res: list[Resolution]) -> dict:
    """Buyer-entered, disclosed freight estimate (PRD §5.4 ESTIMATED): landed = unit + estimate, ASSUMED."""
    for r in res:
        if r.type != "FREIGHT_ESTIMATE":
            continue
        v, est = str(r.target["vendor_id"]), Decimal(r.value)
        for n, c in final.get(v, {}).items():
            if c.freight_basis != "UNKNOWN" or c.unit_price_inr_ex_gst is None:
                continue
            st = c.unit_status if c.unit_status in (S.NEEDS_REVIEW,) else S.ASSUMED
            final[v][n] = replace(c, freight_basis="ESTIMATED", freight_inr_per_box=q4(est),
                                  landed_inr_ex_gst=q4(c.unit_price_inr_ex_gst + est), landed_status=st,
                                  trace=c.trace + [{"step": "freight_estimate", "value": str(est), "resolution_id": r.id,
                                                    "label": "buyer-entered disclosed estimate (FREIGHT_ESTIMATE)", "note": r.reason}])
    return final


# --- the recompute ----------------------------------------------------------------------------
def recompute(sf, rfx_id: int, line_ids: dict[int, int], baseline: dict[int, Decimal], actor: str = "system",
              cause: str = "recompute", cs=None) -> str | None:
    cells = load_phase_a(sf, rfx_id)
    with sf.begin() as s:
        res = _resolutions(s, rfx_id)
        for r in res:  # stale check: source changed since the resolution was made
            if r.type in ("REFERENCE_CONFIRMATION", "FREIGHT_ESTIMATE"):
                continue
            c = cells.get(str(r.target["vendor_id"]), {}).get(int(r.target["line_no"]))
            if c is None or (r.raw_fingerprint and raw_fingerprint(c) != r.raw_fingerprint):
                r.state = "stale"
                s.add(AuditEvent(actor="system", action="RESOLUTION_STALE", target=r.target,
                                 before={"state": "active"}, after={"state": "stale"}, reason="STALE_SOURCE_CHANGED"))
        res = [r for r in res if r.state == "active"]
        for r in res:
            s.expunge(r)
    pre, sticky = _pre_b(cells, res)
    from app.normalize.constants import CONSTANT_SET_V1
    final = _apply_freight_estimates(_post_b(phase_b(pre, baseline, cs or CONSTANT_SET_V1), pre, sticky), res)
    snap = persist(sf, rfx_id, {k: int(k) for k in final}, line_ids, final)
    with sf.begin() as s:  # AWD-7: a scenario is stale when any cells_used fingerprint changes
        from app.analysis.scenario import cell_fingerprint
        from app.db.models import AwardDecision, NormalizedQuote, RfxLine
        lid = {l.line_no: l.id for l in s.scalars(select(RfxLine).where(RfxLine.rfx_id == rfx_id))}
        now = {(q.rfx_line_id, q.vendor_id): cell_fingerprint(q)
               for q in s.scalars(select(NormalizedQuote).where(NormalizedQuote.rfx_line_id.in_(list(lid.values()))))}
        for sc in s.scalars(select(Scenario).where(Scenario.rfx_id == rfx_id, Scenario.stale.is_(False))):
            used = (sc.cells_used_fingerprints or {}).get("cells", {})
            if any(now.get((lid.get(int(k.split(":")[1])), int(k.split(":")[0]))) != fp for k, fp in used.items()):
                sc.stale = True
                for ad in s.scalars(select(AwardDecision).where(AwardDecision.scenario_id == sc.id,
                                                                AwardDecision.acknowledged_at.is_not(None))):
                    ad.superseded = True  # acknowledged awards are never mutated (AWD-7)
        s.add(AuditEvent(actor=actor, action="RECOMPUTE", target={"rfx_id": rfx_id}, after={"snapshot_hash": snap},
                         reason=cause))
    return snap


# --- recording a resolution -------------------------------------------------------------------
def record_resolution(sf, rfx_id: int, *, vendor_id: int, type: str, actor: str, line_no: int | None = None,
                      value: str | None = None, reason: str | None = None, choice: str | None = None) -> Resolution:
    """Validate and store one buyer resolution with its AuditEvent (before/after/actor/time/reason)."""
    type = type.upper()
    cells = load_phase_a(sf, rfx_id)
    with sf.begin() as s:
        if type == "FREIGHT_ESTIMATE":
            try:
                if value is None or Decimal(value) < 0:
                    raise ResolutionError("a non-negative ₹/box freight estimate is required")
            except InvalidOperation:
                raise ResolutionError("value must be a number")
            if not reason:
                raise ResolutionError("a freight estimate must state its source (disclosed assumption)")
            target = {"rfx_id": rfx_id, "vendor_id": vendor_id, "kind": "freight"}
            before, fp = None, None
            for old in _resolutions(s, rfx_id):
                if old.target == target:
                    old.state = "superseded"
        elif type == "REFERENCE_CONFIRMATION":
            if choice not in REFERENCE_CHOICES:
                raise ResolutionError(f"choice must be one of {REFERENCE_CHOICES}")
            if not reason:
                raise ResolutionError("a source note is required for a reference confirmation")
            target = {"rfx_id": rfx_id, "vendor_id": vendor_id, "kind": "reference"}
            before, fp = None, None
            for old in _resolutions(s, rfx_id):  # the latest confirmation is the one in force
                if old.target == target:
                    old.state = "superseded"
        else:
            if type not in CELL_TYPES:
                raise ResolutionError(f"unknown resolution type {type}")
            c = cells.get(str(vendor_id), {}).get(line_no)
            if c is None:
                raise ResolutionError("no such cell")
            if type == "OVERRIDE" and not reason:
                raise ResolutionError("an override requires a reason (§6.5)")
            if type in ("CORRECT", "OVERRIDE"):
                try:
                    if value is None or Decimal(value) <= 0:
                        raise ResolutionError("a positive ₹/box value (ex-GST) is required")
                except InvalidOperation:
                    raise ResolutionError("value must be a number")
            from app.db.models import NormalizedQuote, RfxLine
            line = s.scalar(select(RfxLine).where(RfxLine.rfx_id == rfx_id, RfxLine.line_no == line_no))
            nq = s.scalar(select(NormalizedQuote).where(NormalizedQuote.rfx_line_id == line.id,
                                                        NormalizedQuote.vendor_id == vendor_id))
            if type == "ACCEPT":
                if candidate_value(c) is None:
                    raise ResolutionError("nothing to accept: no candidate value; use Correct")
                choice = ",".join(sorted(set((nq.unit_reasons if nq else c.reasons) or [])))
                value = value or str(candidate_value(c))  # the value the buyer saw and accepted
            before = {"status": nq.unit_status if nq else str(c.unit_status),
                      "value": nq.unit_price_inr_ex_gst if nq else None, "reasons": nq.unit_reasons if nq else c.reasons}
            target = {"rfx_id": rfx_id, "vendor_id": vendor_id, "line_no": line_no, "field": "unit_price"}
            fp = raw_fingerprint(c)
            for old in _resolutions(s, rfx_id):  # a newer resolution supersedes an older one on the same target
                if old.target == target:
                    old.state = "superseded"
        r = Resolution(target=target, type=type, value=value, choice=choice, reason=reason, raw_fingerprint=fp,
                       state="active", actor=actor, at=datetime.now(timezone.utc))
        s.add(r)
        s.flush()
        if type == "REFERENCE_CONFIRMATION":  # DL-20: record the reading on the Reference; terms become ASSUMED
            from app.db.models import Reference
            for ref in s.scalars(select(Reference).where(Reference.rfx_id == rfx_id, Reference.vendor_id == vendor_id)):
                ref.interpretation = {"prices": "CONFIRMED_PRICES", "terms": "CONFIRMED_TERMS", "both": "CONFIRMED_BOTH",
                                      "neither": "CONFIRMED_NEITHER"}[choice]
                ref.confirmation_resolution_id = r.id
                terms_ok = choice in ("terms", "both")
                ref.candidates = [{**c, "status": "ASSUMED", "applied": True, "source": "CONFIRMED_HISTORICAL"}
                                  if c.get("reading") == "B_terms" and terms_ok else
                                  {**c, "applied": False, "status": "UNRESOLVED"} if c.get("reading") == "B_terms" else c
                                  for c in ref.candidates]
        s.add(AuditEvent(actor=actor, action=f"RESOLUTION_{type}", target=target, before=before,
                         after={"resolution_id": r.id, "value": value, "choice": choice}, reason=reason))
        s.flush()
        s.expunge(r)
    return r
