"""Deterministic unit-string dictionary (PRD §5.1) and unit-token detection."""
from __future__ import annotations

import re

UNIT_DICTIONARY: dict[str, str] = {
    "per pc": "PER_BOX", "per piece": "PER_BOX", "/pc": "PER_BOX", "each": "PER_BOX", "per nos": "PER_BOX",
    "per box": "PER_BOX", "₹ per pc": "PER_BOX", "rate (₹ per pc)": "PER_BOX", "per set": "PER_SET",
    "per 100": "PER_100", "per 100 pcs": "PER_100", "per 100 nos": "PER_100", "rate per 100 pcs": "PER_100",
    "per 1000": "PER_1000", "per 1000 pcs": "PER_1000", "/1000 pcs": "PER_1000",
    "per dozen": "PER_DOZEN", "/kg": "PER_KG", "per kg": "PER_KG", "₹/kg": "PER_KG", "rs/kg": "PER_KG",
}
UNIT_TOKEN = re.compile(r"(/\s*kg\b|per\s+kg\b|/\s*pc\b|per\s+(pc|piece|box|set|dozen|nos)\b|per\s+100\b|per\s+1000\b|\beach\b|\bkg\b)", re.I)


def dictionary_class(unit_as_stated: str | None) -> str | None:
    """Known string → class; unknown string → None ("no opinion", PRD §5.1)."""
    if not unit_as_stated:
        return None
    return UNIT_DICTIONARY.get(" ".join(unit_as_stated.lower().split()))


def cross_check(ai_class: str, unit_as_stated: str | None) -> tuple[str, list[str]]:
    d = dictionary_class(unit_as_stated)
    if d is None:
        return ai_class, (["UNIT_DICT_UNSEEN"] if unit_as_stated else [])
    return (ai_class, []) if d == ai_class else ("UNKNOWN", ["UNIT_DICT_DISAGREES"])


def has_unit_token(text: str) -> bool:
    return bool(UNIT_TOKEN.search(text))
