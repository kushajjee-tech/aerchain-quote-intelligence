"""Answer-format guardrails for the analyst (readability, not facts — facts are checked by grounding.py).

Contract: a direct answer first (1–2 sentences), at most 4 short bullets that change what the buyer would do,
an optional "Next:" follow-up, and a final "SHOW: <result index | none>" line choosing the ONE data table the
app displays under the answer. No markdown tables, headings or internal status codes in the prose; the app
shows the data. A violation triggers the analyst's single regeneration; anything still wrong is tidied
deterministically (never by inventing or rewording facts).
"""
from __future__ import annotations

import re

DETAIL_WORDS = re.compile(r"\b(detail|detailed|breakdown|explain|walk me through|list (all|every)|in depth|full)\b", re.I)
SHOW_RE = re.compile(r"^\s*SHOW:\s*(none|\d+)\s*$", re.I | re.M)
TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s+")
CODE = re.compile(r"\b[A-Z]{3,}(?:_[A-Z]{2,})+\b")          # e.g. UNIT_INHERITED, NEEDS_REVIEW
BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
CONTEXT_SUFFIX = re.compile(r"\n*\[Screen context, for reference only:.*\]\s*$", re.S)

FORMAT_RULES = """Answer format (strict; the buyer reads this in a narrow side panel):
- Start with the direct answer to the question in one or two sentences (max 40 words). No preamble, no restating the question.
- Then at most 4 bullet points ("- "), each one short sentence (max 25 words), only for facts that change what the buyer
  would do: exclusions, risks, assumptions that matter, what is missing. Skip bullets for simple factual questions.
- Optionally one final line starting "Next:" with ONE useful follow-up question the buyer could ask you.
- Keep the whole answer under 120 words unless the buyer explicitly asks for detail, a breakdown or a full list (then 250).
- Never write markdown tables, headings or long lists of rows: the app shows the data table you choose below the answer.
- Plain language only: never write internal codes such as UNIT_INHERITED or NEEDS_REVIEW; say "needs review",
  "unit taken from the line's context", "price not usable yet".
- Bold at most 3 short phrases (a vendor name or the key number) with **double asterisks**.
- The very last line must be "SHOW: <n>" where n is the index (0 = first) of the ONE query/run_scenario result whose table
  best supports the answer, or "SHOW: none" when a table adds nothing (yes/no or single-fact answers).
- Call make_chart only if the buyer asks for a chart, or the answer compares 3+ items where a chart is clearly clearer.
- If the screen context is irrelevant to the question, ignore it."""


def wants_detail(question: str) -> bool:
    return bool(DETAIL_WORDS.search(CONTEXT_SUFFIX.sub("", question)))


def split_show(text: str, n_tables: int) -> tuple[str, int | None]:
    """Remove the SHOW marker; return (text, chosen table index or None)."""
    m = None
    for m in SHOW_RE.finditer(text):
        pass
    body = SHOW_RE.sub("", text).strip()
    if not m or m.group(1).lower() == "none":
        return body, None
    i = int(m.group(1))
    return body, i if 0 <= i < n_tables else None


def format_problems(text: str, question: str) -> list[str]:
    """Readability violations, phrased as instructions for the regeneration turn."""
    body = SHOW_RE.sub("", text).strip()
    detail = wants_detail(question)
    lines = [l for l in body.splitlines() if l.strip()]
    bullets = [l for l in lines if BULLET.match(l)]
    words = len(body.split())
    out = []
    if any(TABLE_LINE.match(l) for l in lines):
        out.append("do not write markdown tables; the app shows the data table you choose with SHOW")
    if any(HEADING.match(l) for l in lines):
        out.append("do not use headings")
    if words > (260 if detail else 140):
        out.append(f"the answer has {words} words; keep it under {250 if detail else 120} — direct answer first, then at most 4 short bullets")
    if len(bullets) > (8 if detail else 4):
        out.append(f"use at most {8 if detail else 4} bullets")
    codes = sorted(set(CODE.findall(body)))
    if codes:
        out.append(f"replace internal codes with plain words: {', '.join(codes[:6])}")
    return out


def tidy(text: str, question: str) -> str:
    """Deterministic last resort after regeneration: drop table lines and heading marks, cap bullets.
    Removes structure only; never edits the wording of a sentence."""
    detail = wants_detail(question)
    out, bullets = [], 0
    for line in text.splitlines():
        if TABLE_LINE.match(line):
            continue
        line = HEADING.sub("", line)
        if BULLET.match(line):
            bullets += 1
            if bullets > (8 if detail else 4):
                continue
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
