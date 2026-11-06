"""Grounding check (architecture §11.5): every numeral in the narrative must match a value in the
turn's tool results (at displayed precision, incl. lakh/crore forms), a number in the question, or a
small count/line number."""
from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.(\d+))?(\s*(?:lakh|lakhs|crore|crores|cr|%))?", re.I)


def _dec(x) -> Decimal | None:
    try:
        return Decimal(str(x).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _collect(obj, out: set[Decimal]):
    if isinstance(obj, dict):
        for v in obj.values():
            _collect(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _collect(v, out)
    elif isinstance(obj, bool) or obj is None:
        return
    else:
        d = _dec(obj)
        if d is not None:
            out.add(d)
        elif isinstance(obj, str):
            for m in NUM.finditer(obj):
                d = _dec(m.group(1) + (("." + m.group(2)) if m.group(2) else ""))
                if d is not None:
                    out.add(d)


def _variants(values: set[Decimal]) -> set[Decimal]:
    out = set(values)  # the exact stored value (e.g. 4-dp unit prices) is always allowed
    for v in values:
        for scale in (Decimal(1), Decimal(100000), Decimal(10000000)):
            x = v / scale
            for q in ("1", "0.1", "0.01"):
                out.add(x.quantize(Decimal(q), rounding=ROUND_HALF_UP))
    return out


def narrative_numbers(text: str) -> list[tuple[str, Decimal]]:
    found = []
    for m in NUM.finditer(text):
        raw = m.group(0).strip()
        d = _dec(m.group(1) + (("." + m.group(2)) if m.group(2) else ""))
        if d is not None:
            found.append((raw, d))
    return found


def _is_pair_difference_or_sum(d: Decimal, values: set[Decimal]) -> bool:
    """A savings-style figure: the difference or sum of two values that both appear in the tool results.
    Only two operands, both taken from this turn's results, so nothing new is invented."""
    for a in values:
        if (a + d) in values or (a - d) in values:
            return True
    return False


def check_grounding(narrative: str, tool_results: list, question: str, max_small_int: int = 50) -> list[str]:
    values: set[Decimal] = set()
    _collect(tool_results, values)
    allowed = _variants(values)
    allowed_norm = {a.normalize() for a in allowed}
    q_nums = {d for _, d in narrative_numbers(question)}
    bad = []
    for raw, d in narrative_numbers(narrative):
        if d in q_nums or (d == d.to_integral_value() and d <= max_small_int):
            continue
        if d in allowed or d.normalize() in allowed_norm:
            continue
        if _is_pair_difference_or_sum(d, values):
            continue
        bad.append(raw)
    return bad


# NLA-12: dates, certificate/report numbers and similar identifiers must also come from a tool result row.
DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})\b", re.I)
IDENT = re.compile(r"\b[A-Z]{2,}(?:/[A-Z0-9-]+){2,}\b|\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z0-9]{2}\b")
_MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def _iso(token: str) -> str:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
        return token
    d, mon, y = token.replace(".", "").split()
    return f"{y}-{_MONTHS.index(mon[:3].lower()) + 1:02d}-{int(d):02d}"


def check_identifiers(narrative: str, tool_results: list, question: str) -> list[str]:
    import json as _json
    blob = _json.dumps(tool_results, default=str) + " " + question
    known_dates = {_iso(m.group(1)) for m in DATE.finditer(blob)}
    bad = [m.group(1) for m in DATE.finditer(narrative) if _iso(m.group(1)) not in known_dates]
    bad += [m.group(0) for m in IDENT.finditer(narrative) if m.group(0) not in blob]
    return bad


NEGATION = re.compile(r"\b(no|not|none|never|nobody|neither|nor|without)\b|n't\b", re.I)
FAIL_WORDS = re.compile(r"\b(fail(?:ed|s|ing)?|disqualified)\b", re.I)


def label_lint(narrative: str, tool_results: list) -> list[str]:
    """ELG-6/DL-3: 'failed' only when a result row says FAIL; Unverified is never described as failed."""
    import json as _json
    blob = _json.dumps(tool_results, default=str)
    if '"FAIL"' in blob or "Failed" in blob:
        return []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", narrative):
        if FAIL_WORDS.search(sentence) and not NEGATION.search(sentence):
            return ["'failed' used but no tool result reports FAIL"]
    return []
