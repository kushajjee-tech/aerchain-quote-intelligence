"""Quantity-unit conversion to per box (PRD §5.1/NRM-2). Exact arithmetic; flag CONVERTED."""
from __future__ import annotations

from decimal import Decimal

DIVISOR = {"PER_BOX": Decimal(1), "PER_SET": Decimal(1), "PER_100": Decimal(100),
           "PER_1000": Decimal(1000), "PER_DOZEN": Decimal(12)}


def to_per_box(value: Decimal, unit_class: str) -> Decimal | None:
    d = DIVISOR.get(unit_class)
    return None if d is None else value / d
