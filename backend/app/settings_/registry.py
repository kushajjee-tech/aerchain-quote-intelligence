"""Buyer-managed settings that feed normalisation: FX rates (DL-15/30) and the active constant-set version
(DL-18, PRD §5.11). Changing either is audited and re-normalises stored Phase A inputs, then runs a
global recompute (VAL-5). No document is re-read and no model is called."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.db.models import AuditEvent, ConstantSet as ConstantSetRow, FxRate
from app.normalize.constants import CONSTANT_SET_V1, UNVALIDATED, ConstantSet


def fx_rates(sf) -> dict:
    with sf() as s:
        return {r.currency: {"rate": Decimal(r.rate_to_inr), "as_of": r.as_of, "source": r.source}
                for r in s.scalars(select(FxRate))}


def _row_to_set(r: ConstantSetRow) -> ConstantSet:
    return ConstantSet(r.version, tuple(r.constants))


def active_constant_set(sf) -> ConstantSet:
    with sf() as s:
        r = s.scalar(select(ConstantSetRow).where(ConstantSetRow.active.is_(True)))
        return _row_to_set(r) if r else CONSTANT_SET_V1


def all_constant_sets(sf) -> list[dict]:
    active = active_constant_set(sf).version
    sets = {CONSTANT_SET_V1.version: CONSTANT_SET_V1}
    with sf() as s:
        for r in s.scalars(select(ConstantSetRow)):
            sets[r.version] = _row_to_set(r)
    return [{"version": v, "hash": cs.content_hash, "active": v == active,
             "constants": [{**c, "label": cs.label(c["key"])} for c in cs.constants]} for v, cs in sorted(sets.items())]


def set_fx(sf, currency: str, rate: str, as_of: str, source: str, actor: str) -> None:
    if Decimal(rate) <= 0:
        raise ValueError("rate must be positive")
    with sf.begin() as s:
        row = s.get(FxRate, currency.upper())
        before = None if row is None else {"rate": row.rate_to_inr, "as_of": row.as_of, "source": row.source}
        if row is None:
            row = FxRate(currency=currency.upper(), rate_to_inr=rate, as_of=as_of, source=source, set_by=actor)
            s.add(row)
        else:
            row.rate_to_inr, row.as_of, row.source, row.set_by = rate, as_of, source, actor
        s.add(AuditEvent(actor=actor, action="FX_RATE_SET", target={"currency": currency.upper()}, before=before,
                         after={"rate": rate, "as_of": as_of, "source": source}))


def create_constant_set(sf, base_version: str, changes: dict[str, str], new_version: str, actor: str, reason: str) -> ConstantSet:
    base = next((c for c in all_constant_sets(sf) if c["version"] == base_version), None)
    if base is None:
        raise ValueError("unknown base version")
    if any(c["version"] == new_version for c in all_constant_sets(sf)):
        raise ValueError("versions are immutable: choose a new version name")
    keys = {c["key"] for c in base["constants"]}
    unknown = set(changes) - keys
    if unknown:
        raise ValueError(f"unknown constants: {sorted(unknown)}")
    consts = tuple({**{k: v for k, v in c.items() if k != "label"},
                    **({"value": str(Decimal(changes[c["key"]])), "validation_status": UNVALIDATED, "source": reason}
                       if c["key"] in changes else {})} for c in base["constants"])
    cs = ConstantSet(new_version, consts)
    with sf.begin() as s:
        s.add(ConstantSetRow(version=new_version, content_hash=cs.content_hash, active=False, constants=list(consts)))
        s.add(AuditEvent(actor=actor, action="CONSTANT_SET_CREATED", target={"version": new_version},
                         after={"base": base_version, "changes": changes, "hash": cs.content_hash}, reason=reason))
    return cs


def activate_constant_set(sf, version: str, actor: str, reason: str) -> None:
    with sf.begin() as s:
        rows = list(s.scalars(select(ConstantSetRow)))
        if version != CONSTANT_SET_V1.version and not any(r.version == version for r in rows):
            raise ValueError("unknown version")
        before = next((r.version for r in rows if r.active), CONSTANT_SET_V1.version)
        for r in rows:
            r.active = r.version == version
            if r.active:
                r.activated_by, r.activated_at = actor, datetime.now(timezone.utc)
        s.add(AuditEvent(actor=actor, action="CONSTANT_SET_ACTIVATED", target={"version": version},
                         before={"version": before}, after={"version": version}, reason=reason))
