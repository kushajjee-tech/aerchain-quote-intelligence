import { useEffect, useState } from "react";
import { api } from "../api";
import { Chip } from "../components/StatusBadge";
import { useRfx } from "../rfx";

// J1–J3 (DL-19, DL-27, RFX-9…11): brief pack → AI mapping → buyer confirms → deterministic import → gaps →
// questionnaire + terms (cited) → conformance → approve → send → deliver → process. Every AI step is a proposal.
export default function Copilot() {
  const { rfxId, setRfxId } = useRfx();
  const [h, setH] = useState<any>(null);
  const [mapping, setMapping] = useState<any[] | null>(null);
  const [gapText, setGapText] = useState("");
  const [gapPatch, setGapPatch] = useState<any>(null);
  const [qdraft, setQdraft] = useState<any>(null);
  const [log, setLog] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const note = (m: string) => setLog((l) => [m, ...l].slice(0, 8));
  const refresh = (id = rfxId) => api(`/rfx/${id}`).then(setH).catch(() => setH(null));
  useEffect(() => { refresh(); }, [rfxId]);

  const run = async (label: string, fn: () => Promise<any>) => {
    setBusy(true);
    try { const r = await fn(); note(`${label}: ok`); await refresh(); return r; }
    catch (e) { note(`${label}: ${e}`); } finally { setBusy(false); }
  };
  const start = (sandbox: boolean) => run(sandbox ? "Start sandbox" : "Start live draft", async () => {
    const r = await api("/rfx/primary", { body: { title: sandbox ? "Sandbox RFx" : "Annual corrugated packaging RFx", sandbox } });
    setRfxId(r.rfx_id); setMapping(r.mapping_proposal.mappings); await refresh(r.rfx_id);
  });
  const fallback = () => run("Load seeded fallback", async () => { const r = await api("/rfx/seeded-fallback", { body: {} }); setRfxId(r.rfx_id); });

  return (
    <section>
      <h2>Co-pilot</h2>
      <div style={{ display: "flex", gap: 8 }}>
        <button disabled={busy} onClick={() => start(false)}>Draft primary RFx live from the brief pack</button>
        <button disabled={busy} onClick={() => start(true)}>New sandbox RFx</button>
        <button disabled={busy} onClick={fallback}>Load seeded fallback</button>
      </div>
      {h && (<div style={{ border: "1px solid #e5e7eb", padding: 8, marginTop: 8 }}>
        <b>RFx #{h.rfx_id} — {h.title}</b> <Chip text={h.label} /> <Chip text={`status: ${h.status}`} />
        {h.conformance && <Chip text={h.conformance.conforms ? "Conforms to canonical spec" : `${h.conformance.differences.length} differences`} />}
        <p style={{ fontSize: 12 }}>Scope: {h.scope ?? <i>not yet drafted — answer the open fields below</i>}</p>
        {h.terms?.length > 0 && <p style={{ fontSize: 12 }}>Terms: {h.terms.map((t: any) => `${t.type}: ${t.text}`).join(" · ")}</p>}
        <p style={{ fontSize: 12, color: "#6b7280" }}>Accepted steps: {h.patches.map((p: any) => p.action).join(" → ") || "none yet"}</p>
      </div>)}

      {mapping && (<div><h3>1. Column mapping (AI proposal — confirm or edit)</h3>
        <table style={{ fontSize: 12 }}><tbody>{mapping.map((m, i) => (
          <tr key={i}><td>{m.column}</td><td>→</td>
            <td><input value={m.field ?? ""} onChange={(e) => setMapping(mapping.map((x, k) => k === i ? { ...x, field: e.target.value } : x))} /></td>
            <td>{m.confidence !== "HIGH" && <Chip text={`${m.confidence} confidence`} />}</td></tr>))}</tbody></table>
        <button disabled={busy} onClick={() => run("Confirm mapping + import", async () => {
          const r = await api(`/rfx/${rfxId}/mapping/confirm`, { body: { mapping: Object.fromEntries(mapping.filter((m) => m.field).map((m) => [m.column, m.field])) } });
          note(`imported ${r.lines} lines; open fields: ${r.rfx_gaps.join(", ")}`); setMapping(null);
        })}>Confirm and import rows</button></div>)}

      <h3>2. Open fields</h3>
      <textarea value={gapText} onChange={(e) => setGapText(e.target.value)} placeholder="Answer the co-pilot: what you're buying and for how long, delivery location, dimension convention, validity, GST basis…"
                style={{ width: "100%", height: 50 }} />
      <button disabled={busy || !gapText} onClick={() => run("Propose answers", async () => setGapPatch(await api(`/rfx/${rfxId}/gaps/propose`, { body: { text: gapText } })))}>Propose</button>
      {gapPatch && (<div style={{ fontSize: 12 }}>
        {Object.entries(gapPatch).filter(([, v]) => v).map(([k, v]: any) => <div key={k}>{k}: <b>{v.value}</b> — “{v.quote}”</div>)}
        <button disabled={busy} onClick={() => run("Apply answers", async () => {
          const r = await api(`/rfx/${rfxId}/gaps/apply`, { body: { patch: gapPatch, source_text: gapText } });
          note(`rejected (quote not in your text): ${r.rejected.join(", ") || "none"}`); setGapPatch(null);
        })}>Apply</button></div>)}

      <h3>3. Questionnaire and terms (cited to the checklist and policy)</h3>
      <button disabled={busy} onClick={() => run("Draft questionnaire", async () => setQdraft(await api(`/rfx/${rfxId}/questionnaire/propose`, { body: {} })))}>Draft</button>
      {qdraft && (<div style={{ fontSize: 12 }}>
        <ul>{qdraft.draft.questions.map((q: any, i: number) => {
          const v = qdraft.validation.find((x: any) => x.key === q.requirement_key);
          return <li key={i}>{q.no} [{q.section}] {q.requirement_key}: {q.text} <i>({q.applicability}; {q.pass_op} {q.pass_value ?? ""})</i>{" "}
            {v?.ok ? <Chip text="citation verified" /> : <Chip text={`rejected: ${v?.problems.join(", ")}`} />}</li>;
        })}</ul>
        <button disabled={busy || !qdraft.validation.every((v: any) => v.ok)} onClick={() => run("Apply questionnaire", async () => {
          await api(`/rfx/${rfxId}/questionnaire/apply`, { body: { draft: qdraft.draft } }); setQdraft(null);
        })}>Apply all</button></div>)}

      <h3>4. Check, approve, send</h3>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button disabled={busy} onClick={() => run("Conformance", () => api(`/rfx/${rfxId}/conformance`, { body: {} }))}>Conformance check</button>
        <button disabled={busy} onClick={() => run("Approve", () => api(`/rfx/${rfxId}/approve`, { body: {} }))}>Approve</button>
        <button disabled={busy} onClick={() => run("Send", () => api(`/rfx/${rfxId}/send`, { body: {} }))}>Send to vendors</button>
        <button disabled={busy} onClick={() => run("Deliver next response", async () => {
          const r = await api(`/rfx/${rfxId}/deliver-next`, { body: {} }); note(r.delivered ? `delivered ${r.delivered.path}` : "inbox empty");
        })}>Deliver next response</button>
        <button disabled={busy} onClick={() => run("Process responses", async () => {
          const r = await api(`/rfx/${rfxId}/process`, { body: {} });
          note(`processed: ${r.processed_vendors.join(", ")}${Object.keys(r.failed).length ? "; failed: " + Object.keys(r.failed).join(", ") : ""}`);
        })}>Read responses</button>
      </div>
      {h?.conformance && !h.conformance.conforms && (
        <ul style={{ fontSize: 12, color: "#991b1b" }}>{h.conformance.differences.slice(0, 12).map((d: any, i: number) => <li key={i}>{JSON.stringify(d)}</li>)}</ul>)}
      <ul style={{ fontSize: 12, color: "#374151" }}>{log.map((l, i) => <li key={i}>{l}</li>)}</ul>
    </section>
  );
}
