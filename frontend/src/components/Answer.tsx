// One analyst answer: narrative (model), calculated tables/charts (tool results), interpretation, code-generated caveats,
// and links back into the app for the suppliers and lines it mentions.
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ExternalLink, FileText, Send, Table2 } from "lucide-react";
import Chart from "./Chart";
import { useRfx } from "../rfx";
import { Notice } from "../ui";

export function ResultTable({ t, answerId, index, maxHeight = 320 }: { t: any; answerId: number; index: number; maxHeight?: number }) {
  const shown = t.rows.slice(0, 50);
  return (
    <div style={{ margin: "8px 0" }}>
      <div className="table-wrap" style={{ maxHeight }}>
        <table className="t dense"><thead><tr>{t.columns.map((c: string) => <th key={c}>{c.replace(/_/g, " ")}</th>)}</tr></thead>
          <tbody>{shown.map((r: any, i: number) => <tr key={i}>{t.columns.map((c: string) =>
            <td key={c} className="num">{r[c] === null ? <span className="subtle">—</span> : String(r[c])}</td>)}</tr>)}</tbody></table>
      </div>
      <div className="subtle row wrap" style={{ gap: 8, marginTop: 4 }}>{t.rows.length} rows{t.rows.length > 50 && " (first 50 shown)"} · from {t.source}
        <a href={`/api/analyst/answers/${answerId}/export?index=${index}&fmt=xlsx`}>XLSX</a><a href={`/api/analyst/answers/${answerId}/export?index=${index}&fmt=csv`}>CSV</a></div>
    </div>
  );
}

/** Suppliers and lines an answer refers to, so the buyer can jump straight to them. */
export function answerLinks(text: string, vendors: { vendor_id: number; key: string; name: string }[]) {
  const links: { label: string; to: string }[] = [];
  for (const v of vendors) {
    const first = v.name.split(/\s+/)[0];
    if (new RegExp(`\\b${v.key}\\b`).test(text) || (first.length > 3 && text.includes(first))) links.push({ label: `Open ${v.key} · ${first}`, to: `/vendors/${v.vendor_id}` });
  }
  const lines = [...new Set([...text.matchAll(/\b[Ll]ines? (\d{1,2})\b/g)].map((m) => Number(m[1])))].filter((n) => n >= 1 && n <= 99).slice(0, 3);
  lines.forEach((n) => links.push({ label: `Open line ${n}`, to: `/comparison?line=${n}` }));
  return links.slice(0, 6);
}

export function Answer({ a, compact }: { a: any; compact?: boolean }) {
  const nav = useNavigate();
  const { overview } = useRfx();
  const [work, setWork] = useState(false);
  const cav = Object.entries(a.caveats ?? {}).filter(([k, v]) => k !== "method" && v !== null && !(Array.isArray(v) && v.length === 0) &&
    !(typeof v === "object" && !Array.isArray(v) && Object.keys(v as object).length === 0));
  const links = answerLinks(a.narrative ?? "", overview?.vendors ?? []);
  const firstVendor = links.find((l) => l.to.startsWith("/vendors/"));
  return (
    <div className="stack" style={{ gap: 12 }}>
      {a.banner && <Notice tone="critical">{a.banner}</Notice>}
      <div>{!compact && <div className="section-title">Answer</div>}<div style={{ whiteSpace: "pre-wrap" }}>{a.narrative}</div></div>
      {(a.tables?.length > 0 || a.charts?.length > 0) && <div><div className="section-title">What the system calculated</div>
        {a.charts?.map((ch: any, k: number) => <div key={k} style={{ overflowX: "auto" }}><Chart c={ch} /></div>)}
        {a.tables?.map((t: any, k: number) => <ResultTable key={k} t={t} answerId={a.answer_id} index={k} maxHeight={compact ? 220 : 320} />)}</div>}
      {a.interpretation_note && <div><div className="section-title">How the question was interpreted</div><div className="muted" style={{ fontSize: 13 }}>{a.interpretation_note}</div></div>}
      {cav.length > 0 && <details open={!compact}><summary className="section-title" style={{ cursor: "pointer" }}>Caveats and assumptions (code-generated)</summary>
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }} className="muted">{cav.map(([k, v]) => <li key={k}><b>{k.replace(/_/g, " ")}:</b> {Array.isArray(v) ? v.join("; ") : typeof v === "object" ? JSON.stringify(v) : String(v)}</li>)}</ul></details>}
      {a.exclusions?.length > 0 && <details><summary className="subtle" style={{ cursor: "pointer" }}>Exclusions ({a.exclusions.length})</summary>
        <ul style={{ fontSize: 12 }}>{a.exclusions.map((e: any, k: number) => <li key={k}>Line {e.line_no}, {e.vendor}: {e.reason} {e.detail ?? ""}</li>)}</ul></details>}
      <div className="row wrap" style={{ gap: 6 }}>
        {links.map((l) => <button key={l.to} className="prompt-chip" onClick={() => nav(l.to)}><ExternalLink size={12} /> {l.label}</button>)}
        {links.length === 0 && <button className="prompt-chip" onClick={() => nav("/comparison")}><Table2 size={12} /> Open comparison</button>}
        {firstVendor && <button className="prompt-chip" onClick={() => nav(firstVendor.to)}><Send size={12} /> Draft clarification</button>}
        <button className="prompt-chip" onClick={() => setWork(!work)}><FileText size={12} /> {work ? "Hide" : "Show"} work ({a.tool_calls?.length ?? 0})</button>
      </div>
      {work && <pre className="quote mono" style={{ maxHeight: 320, overflow: "auto", whiteSpace: "pre-wrap" }}>{JSON.stringify(a.tool_calls, null, 1)}{"\n"}{JSON.stringify(a.results, null, 1)}</pre>}
    </div>
  );
}
