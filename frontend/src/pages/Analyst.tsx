import { useState } from "react";
import { api } from "../api";
import Chart from "../components/Chart";

function ResultTable({ t, answerId, index }: { t: any; answerId: number; index: number }) {
  const shown = t.rows.slice(0, 50);
  return (
    <div style={{ margin: "6px 0", overflowX: "auto" }}>
      <table style={{ borderCollapse: "collapse", fontSize: 12 }}>
        <thead><tr>{t.columns.map((c: string) => <th key={c} style={{ borderBottom: "1px solid #d1d5db", padding: "2px 6px", textAlign: "left" }}>{c}</th>)}</tr></thead>
        <tbody>{shown.map((r: any, i: number) => <tr key={i}>{t.columns.map((c: string) =>
          <td key={c} style={{ padding: "2px 6px", borderBottom: "1px solid #f3f4f6" }}>{r[c] === null ? "—" : String(r[c])}</td>)}</tr>)}</tbody>
      </table>
      <small>{t.rows.length} rows{t.rows.length > 50 && " (first 50 shown)"} · from {t.source} ·{" "}
        <a href={`/api/analyst/answers/${answerId}/export?index=${index}&fmt=xlsx`}>xlsx</a> ·{" "}
        <a href={`/api/analyst/answers/${answerId}/export?index=${index}&fmt=csv`}>csv</a></small>
    </div>
  );
}
import { useRfx } from "../rfx";

// NLA-3/4/9: narrative + code-generated caveats + the exact tool calls and raw results.
export default function Analyst() {
  const { rfxId } = useRfx();
  const [q, setQ] = useState("");
  const [session, setSession] = useState<string | null>(null);
  const [turns, setTurns] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const ask = async () => {
    setBusy(true);
    try {
      const a = await api("/analyst/ask", { body: { rfx_id: rfxId, question: q, session_id: session } });
      setSession(a.session_id); setTurns([...turns, { q, a }]); setQ(""); setErr(null);
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  };
  return (
    <section>
      <h2>Analyst</h2>
      {turns.map(({ q, a }, i) => (
        <div key={i} style={{ borderBottom: "1px solid #e5e7eb", padding: "8px 0" }}>
          <p><b>Q:</b> {q}</p>
          {a.banner && <p role="alert" style={{ background: "#fee2e2", padding: 6 }}>{a.banner}</p>}
          <p style={{ whiteSpace: "pre-wrap" }}>{a.narrative}</p>
          <p style={{ fontSize: 12, color: "#4b5563" }}>Method: {a.interpretation_note}</p>
          {a.caveats && Object.keys(a.caveats).length > 0 && (
            <details open><summary>Caveats (code-generated)</summary>
              <ul style={{ fontSize: 12 }}>{Object.entries(a.caveats).filter(([k, v]) => k !== "method" && v !== null &&
                !(Array.isArray(v) && v.length === 0) && !(typeof v === "object" && !Array.isArray(v) && Object.keys(v as object).length === 0))
                .map(([k, v]) => <li key={k}><b>{k.replace(/_/g, " ")}:</b> {Array.isArray(v) ? v.join("; ") : typeof v === "object" ? JSON.stringify(v) : String(v)}</li>)}</ul>
            </details>)}
          {a.exclusions?.length > 0 && <details><summary>Exclusions ({a.exclusions.length})</summary>
            <ul style={{ fontSize: 12 }}>{a.exclusions.map((e: any, k: number) => <li key={k}>Line {e.line_no}, {e.vendor}: {e.reason} {e.detail ?? ""}</li>)}</ul></details>}
          {a.charts?.map((ch: any, k: number) => <Chart key={k} c={ch} />)}
          {a.tables?.map((t: any, k: number) => <ResultTable key={k} t={t} answerId={a.answer_id} index={k} />)}
          <details><summary>Show work ({a.tool_calls.length} tool calls)</summary>
            <pre style={{ fontSize: 11, maxHeight: 300, overflow: "auto", background: "#f9fafb" }}>{JSON.stringify(a.tool_calls, null, 1)}{"\n"}{JSON.stringify(a.results, null, 1)}</pre></details>
        </div>))}
      <textarea value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask about the comparison…" style={{ width: "100%", height: 60 }} />
      <button onClick={ask} disabled={busy || !q.trim()}>{busy ? "Thinking…" : "Ask"}</button>
      {err && <p role="alert">{err}</p>}
    </section>
  );
}
