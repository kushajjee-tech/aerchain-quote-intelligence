"""Slab selection (NRM-10): the slab whose quantity range contains the RFx annual quantity."""
from __future__ import annotations

from decimal import Decimal


def select_slab(slabs: list[dict], annual_qty: int) -> tuple[int | None, str | None]:
    """slabs: [{min_qty, max_qty, value}] → (index, None) or (None, 'SLAB_AMBIGUOUS')."""
    hits = [i for i, s in enumerate(slabs)
            if (s.get("min_qty") is None or annual_qty >= s["min_qty"])
            and (s.get("max_qty") is None or annual_qty <= s["max_qty"])]
    return (hits[0], None) if len(hits) == 1 else (None, "SLAB_AMBIGUOUS")


def slab_value(slab: dict) -> Decimal:
    return Decimal(str(slab["value"]))
