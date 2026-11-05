"""Printable memo (EXP-2): a minimal, dependency-free Markdown → HTML rendering of the template memo."""
from __future__ import annotations

import html
import re

CSS = ("body{font-family:Helvetica,Arial,sans-serif;max-width:900px;margin:24px auto;font-size:13px;color:#111}"
       "table{border-collapse:collapse;width:100%}td,th{border:1px solid #999;padding:3px 6px;text-align:left}"
       "h1{font-size:20px}h2{font-size:15px;margin-top:18px}@media print{body{margin:0}}")


def _inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", t)


def memo_html(md: str, title: str) -> str:
    out, in_list, table = [], False, []

    def flush_table():
        if table:
            rows = [r for r in table if not re.fullmatch(r"\|[-| ]+\|", r)]
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            out.append("<table><thead><tr>" + "".join(f"<th>{_inline(c)}</th>" for c in cells[0]) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in cells[1:])
                       + "</tbody></table>")
            table.clear()

    for line in md.splitlines():
        if line.startswith("|"):
            table.append(line)
            continue
        flush_table()
        if line.startswith("- ") or line.startswith("  - "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_inline(line.strip()[2:])}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if line.startswith("## "):
            out.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{_inline(line[2:])}</h1>")
        elif line.strip():
            out.append(f"<p>{_inline(line)}</p>")
    flush_table()
    if in_list:
        out.append("</ul>")
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title>"
            f"<style>{CSS}</style></head><body>{''.join(out)}</body></html>")
