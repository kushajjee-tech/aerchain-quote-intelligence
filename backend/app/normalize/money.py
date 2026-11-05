"""Decimal money policy (PRD §5.10): unit prices 4 dp; annual line totals rounded once to whole
rupees; totals are sums of rounded line totals; ROUND_HALF_UP; never floats."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, getcontext

getcontext().prec = 28
Q4 = Decimal("0.0001")


def D(x) -> Decimal:
    if isinstance(x, float):
        return Decimal(repr(x))
    return Decimal(str(x))


def q4(x: Decimal) -> Decimal:
    return x.quantize(Q4, rounding=ROUND_HALF_UP)


def line_total(unit_price: Decimal, qty: int) -> Decimal:
    return (unit_price * qty).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def pct(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
