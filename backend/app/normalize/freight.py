"""Freight basis from THIS year's response only (PRD §5.4; DL-2, DL-8)."""
from __future__ import annotations

from decimal import Decimal

INCLUDED_HINTS = ("freight included", "delivered", "for destination", "inclusive of freight", "free delivery")
UNKNOWN_HINTS = ("freight extra", "ex-works", "ex works", "freight ex")


PER_BOX_UNITS = ("per box", "per pc", "per piece", "/box", "/pc")
CHARGED_HINTS = ("charged separately", "over and above", "extra", "additional", "charged at")


def freight_currency(t: dict) -> str:
    blob = f"{t.get('unit') or ''} {t.get('value') or ''} {t.get('text') or ''}".lower()
    return "USD" if any(h in blob for h in ("usd", "us$", "$")) else "INR"


def _amount(value) -> Decimal | None:
    try:
        return Decimal(str(value).replace(",", "").replace("₹", "").replace("$", "").replace("USD", "").replace("usd", "").strip())
    except Exception:
        return None


def freight_basis(terms: list[dict]) -> tuple[str, Decimal | None, dict | None]:
    """terms: extracted FREIGHT DocumentTerms → (basis, amount per box in the term's currency or None, cited term).
    A stated per-box amount wins over hint words ("…per box, delivered to your plant (charged separately)" is
    STATED, not INCLUDED). The currency is read by `freight_currency`; conversion happens in the engine."""
    for t in terms:
        if t.get("type") != "FREIGHT":
            continue
        text = (t.get("text") or "").lower()
        value, unit = t.get("value"), (t.get("unit") or "").lower()
        amount = _amount(value) if value not in (None, "") else None
        per_box = any(u in unit for u in PER_BOX_UNITS) or any(u in text for u in PER_BOX_UNITS)
        if amount is not None and amount > 0 and per_box:
            return "STATED", amount, t
        if any(h in text for h in INCLUDED_HINTS) and not any(h in text for h in CHARGED_HINTS + UNKNOWN_HINTS):
            return "INCLUDED", Decimal(0), t
        if any(h in text for h in UNKNOWN_HINTS):
            return "UNKNOWN", None, t
    return "UNKNOWN", None, None  # silent → unknown; never filled from history
