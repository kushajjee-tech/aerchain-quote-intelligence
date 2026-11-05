// One analyst answer, built to be read in a narrow panel: the direct answer first, a few short points with visual
// cues, ONE data table the analyst chose (tidied, first rows only), an optional chart, a follow-up the buyer can click,
// and everything else (method, caveats, raw results, tool calls) folded under "Sources & details".
import { Fragment, ReactNode, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowRight, CheckCircle2, ChevronDown, ChevronRight, CircleDot, ExternalLink, ShieldCheck, Table2, XCircle } from "lucide-react";
import Chart from "./Chart";
import { inr } from "../api";
import { useRfx } from "../rfx";
import { Notice } from "../ui";

// ---------- light formatting ----------
function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((p, i) => p.startsWith("**") && p.endsWith("**") ? <b key={i}>{p.slice(2, -2)}</b> : <Fragment key={i}>{p}</Fragment>);
}
const RISK = /\b(not|no|missing|excluded|exclude|unverified|fail|failed|risk|unknown|unresolved|withheld|depends|caveat|review|expired|below|lower bound|assum)/i;
const NEG = /\b(fail|failed|expired|excluded|not usable|withheld|no eligible)\b/i;

type Block = { kind: "p" | "bullet" | "table" | "next" | "h"; text?: string; rows?: string[][] };
export function parseNarrative(n: string): Block[] {
  const out: Block[] = [];
  const lines = n.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i].trim();
    if (!l) continue;
    if (/^\|.*\|$/.test(l)) {                       // legacy markdown table → real table
      const rows: string[][] = [];
      while (i < lines.length && /^\|.*\|$/.test(lines[i].trim())) {
        const cells = lines[i].trim().slice(1, -1).split("|").map((c) => c.trim());
        if (!cells.every((c) => /^:?-{2,}:?$/.test(c))) rows.push(cells);
        i++;
      }
      i--; out.push({ kind: "table", rows }); continue;
    }
    if (/^#{1,6}\s/.test(l)) { out.push({ kind: "h", text: l.replace(/^#+\s*/, "") }); continue; }
    if (/^next:/i.test(l)) { out.push({ kind: "next", text: l.replace(/^next:\s*/i, "") }); continue; }
    if (/^\s*(?:[-*•]|\d+[.)])\s+/.test(l)) { out.push({ kind: "bullet", text: l.replace(/^\s*(?:[-*•]|\d+[.)])\s+/, "") }); continue; }
    if (/^\*\*[^*]+\*\*:?$/.test(l)) { out.push({ kind: "h", text: l.replace(/\*\*/g, "").replace(/:$/, "") }); continue; }
    out.push({ kind: "p", text: l });
  }
  return out;
}

// ---------- data table: readable headers, hidden ids, formatted values ----------
const HIDE = /^(rfx_id|vendor_id|evidence_ref|evidence_snippet|reasons|flags|fact_status|expiry_kind|includable_formal)$/;
const LABEL: Record<string, string> = { sku: "SKU", line_no: "Line", unit_price_inr: "₹/box", price_on_basis_inr: "₹/box", annual_spend_inr: "Annual spend",
  landed_inr: "Landed ₹/box", annual_qty: "Annual qty", break_even_inr_per_box: "Break-even freight", n: "Count", valid_today: "Valid today" };
const head = (c: string) => LABEL[c] ?? c.replace(/_inr$/, " (₹)").replace(/_/g, " ").replace(/^./, (x) => x.toUpperCase());
function cell(c: string, v: any): ReactNode {
  if (v === null || v === undefined || v === "") return <span className="subtle">—</span>;
  if (typeof v === "boolean" || v === "true" || v === "false" || ((c === "valid_today" || c === "needs_review") && (v === 1 || v === 0)))
    return String(v) === "true" || v === 1 ? "Yes" : "No";
  if (/_inr$|_inr_per_box$/.test(c) && !isNaN(Number(v))) return inr(v, /spend|total|savings/.test(c) ? 0 : 2);
  if (typeof v === "string" && /^[A-Z_]{4,}$/.test(v)) return v.replace(/_/g, " ").toLowerCase();
  return String(v);
}
export function ResultTable({ t, answerId, index, initial = 6 }: { t: any; answerId?: number; index: number; initial?: number }) {
  const [all, setAll] = useState(false);
  const cols: string[] = t.columns.filter((c: string) => !HIDE.test(c));
  const rows = all ? t.rows.slice(0, 200) : t.rows.slice(0, initial);
  return (
    <div>
      <div className="table-wrap" style={{ maxHeight: all ? 360 : undefined, border: "1px solid var(--border)", borderRadius: 8 }}>
        <table className="t dense"><thead><tr>{cols.map((c) => <th key={c}>{head(c)}</th>)}</tr></thead>
          <tbody>{rows.map((r: any, i: number) => <tr key={i}>{cols.map((c) => <td key={c} className="num">{cell(c, r[c])}</td>)}</tr>)}</tbody></table>
      </div>
      <div className="subtle row wrap" style={{ gap: 10, marginTop: 4 }}>
        {t.rows.length > initial && <button className="btn link" style={{ padding: 0, fontSize: 12 }} onClick={() => setAll(!all)}>{all ? "Show fewer" : `Show all ${t.rows.length} rows`}</button>}
        {answerId !== undefined && <><a href={`/api/analyst/answers/${answerId}/export?index=${index}&fmt=xlsx`}>XLSX</a><a href={`/api/analyst/answers/${answerId}/export?index=${index}&fmt=csv`}>CSV</a></>}
      </div>
    </div>
  );
}

/** Suppliers and lines an answer refers to, so the buyer can jump straight to them. */
export function answerLinks(text: string, vendors: { vendor_id: number; key: string; name: string }[]) {
  const links: { label: string; to: string }[] = [];
  for (const v of vendors) {
    const first = v.name.split(/\s+/)[0];
    if (new RegExp(`\\b${v.key}\\b`).test(text) || (first.length > 3 && text.includes(first))) links.push({ label: `${v.key} · ${first}`, to: `/vendors/${v.vendor_id}` });
  }
  const lines = [...new Set([...text.matchAll(/\b[Ll]ines? (\d{1,2})\b/g)].map((m) => Number(m[1])))].filter((n) => n >= 1 && n <= 99).slice(0, 3);
  lines.forEach((n) => links.push({ label: `Line ${n}`, to: `/comparison?line=${n}` }));
  return links.slice(0, 5);
}

function Point({ text }: { text: string }) {
  const icon = NEG.test(text) ? <XCircle size={14} color="var(--critical)" /> : RISK.test(text) ? <AlertTriangle size={14} color="var(--warning)" /> : <CheckCircle2 size={14} color="var(--success)" />;
  return <li className="answer-point"><span className="answer-icon">{icon}</span><span>{inline(text)}</span></li>;
}

export function Answer({ a, compact, onAsk }: { a: any; compact?: boolean; onAsk?: (q: string) => void }) {
  const nav = useNavigate();
  const overview = useRfx()?.overview;
  const [details, setDetails] = useState(false);
  const blocks = parseNarrative(a.narrative ?? "");
  const lead = blocks.filter((b) => b.kind === "p").slice(0, 2);
  const rest = blocks.filter((b) => !lead.includes(b));
  const links = answerLinks(a.narrative ?? "", overview?.vendors ?? []);
  const shown = typeof a.display_table === "number" ? a.tables?.[a.display_table] : null;
  const cav = Object.entries(a.caveats ?? {}).filter(([k, v]) => k !== "method" && v !== null && !(Array.isArray(v) && v.length === 0) &&
    !(typeof v === "object" && !Array.isArray(v) && Object.keys(v as object).length === 0));
  return (
    <div className="answer">
      {a.banner && <Notice tone="critical">{a.banner}</Notice>}
      <div className="answer-lead">{lead.map((b, i) => <p key={i}>{inline(b.text!)}</p>)}</div>
      {rest.length > 0 && (() => {
        const groups: ReactNode[] = []; let bullets: string[] = [];
        const flush = () => { if (bullets.length) groups.push(<ul key={groups.length} className="answer-points">{bullets.map((t, i) => <Point key={i} text={t} />)}</ul>); bullets = []; };
        rest.forEach((b) => {
          if (b.kind === "bullet") { bullets.push(b.text!); return; }
          flush();
          if (b.kind === "h") groups.push(<div key={groups.length} className="answer-h">{b.text}</div>);
          else if (b.kind === "p") groups.push(<p key={groups.length} className="answer-p">{inline(b.text!)}</p>);
          else if (b.kind === "table" && b.rows?.length) groups.push(<ResultTable key={groups.length} index={-1} t={{ columns: b.rows[0], rows: b.rows.slice(1).map((r) => Object.fromEntries(b.rows![0].map((c, k) => [c, r[k]]))) }} />);
        });
        flush();
        return <div className="stack" style={{ gap: 8 }}>{groups}</div>;
      })()}
      {a.charts?.map((ch: any, k: number) => <div key={k} className="answer-figure"><Chart c={ch} /></div>)}
      {shown && <div className="answer-figure"><div className="answer-h"><Table2 size={13} /> Supporting data</div><ResultTable t={shown} answerId={a.answer_id} index={a.display_table} initial={compact ? 5 : 8} /></div>}
      {blocks.filter((b) => b.kind === "next").map((b, i) => (
        <button key={i} className="answer-next" onClick={() => onAsk?.(b.text!)} disabled={!onAsk}><ArrowRight size={13} />{b.text}</button>))}
      <div className="row wrap" style={{ gap: 6 }}>
        {links.map((l) => <button key={l.to} className="prompt-chip" onClick={() => nav(l.to)}><ExternalLink size={11} /> {l.label}</button>)}
        <span className="answer-check" title="Every number in the answer was checked against the calculation results">
          {a.grounded !== false && !a.banner ? <><ShieldCheck size={12} /> Numbers checked</> : <><CircleDot size={12} /> Not fully verified</>}</span>
      </div>
      <button className="answer-more" onClick={() => setDetails(!details)}>{details ? <ChevronDown size={13} /> : <ChevronRight size={13} />} Sources & details</button>
      {details && (
        <div className="stack answer-details">
          {a.interpretation_note && <div><div className="answer-h">Method</div><div className="muted">{a.interpretation_note}</div></div>}
          {cav.length > 0 && <div><div className="answer-h">Caveats (generated by code)</div>
            <ul className="muted" style={{ margin: 0, paddingLeft: 18 }}>{cav.map(([k, v]) => <li key={k}><b>{k.replace(/_/g, " ")}:</b> {Array.isArray(v) ? v.join("; ") : typeof v === "object" ? JSON.stringify(v) : String(v)}</li>)}</ul></div>}
          {a.exclusions?.length > 0 && <div><div className="answer-h">Exclusions ({a.exclusions.length})</div>
            <ul className="muted" style={{ margin: 0, paddingLeft: 18 }}>{a.exclusions.slice(0, 30).map((e: any, k: number) => <li key={k}>Line {e.line_no}, {e.vendor}: {e.reason}</li>)}</ul></div>}
          {a.tables?.map((t: any, k: number) => k === a.display_table ? null : (
            <details key={k}><summary className="subtle" style={{ cursor: "pointer" }}>Result {k + 1}: {t.source} · {t.rows.length} rows</summary><ResultTable t={t} answerId={a.answer_id} index={k} initial={5} /></details>))}
          <details><summary className="subtle" style={{ cursor: "pointer" }}>Tool calls ({a.tool_calls?.length ?? 0})</summary>
            <pre className="quote mono" style={{ maxHeight: 260, overflow: "auto", whiteSpace: "pre-wrap" }}>{JSON.stringify(a.tool_calls, null, 1)}</pre></details>
        </div>)}
    </div>
  );
}
