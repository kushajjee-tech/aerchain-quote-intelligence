// Co-pilot: (1) the RFx assistant, full-size (the same conversation as the "Ask AI" panel on every screen);
// (2) the RFx drafting workflow (brief → mapping → open fields → questionnaire → conformance → approve → send → read).
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ClipboardList, MessageSquareText, RotateCcw } from "lucide-react";
import { api } from "../api";
import { ChatThread, useAssistant } from "../assistant";
import { useRfx } from "../rfx";
import { Badge, Button, Card, Notice, PageHeader, Tabs } from "../ui";

function Assistant() {
  const { overview } = useRfx();
  const { turns, reset } = useAssistant();
  return (
    <div className="split" style={{ gridTemplateColumns: "1fr 300px", alignItems: "start" }}>
      <Card pad={false}><div style={{ height: "calc(100vh - 290px)", minHeight: 460 }}><ChatThread /></div></Card>
      <div className="stack" style={{ gap: 16 }}>
        <Card title="Context">
          <dl className="kv" style={{ gridTemplateColumns: "80px 1fr" }}>
            <dt>RFx</dt><dd>{overview?.rfx.meta.code}<div className="subtle">{overview?.rfx.title}</div></dd>
            <dt>Scope</dt><dd>{overview?.metrics.skus} SKUs · {overview?.metrics.vendors_responded} responses</dd>
            <dt>Sources</dt><dd className="subtle">Normalised comparison, eligibility results, document facts, award engine</dd>
          </dl>
        </Card>
        <Notice tone="info">This is the same conversation as the <b>Ask AI</b> button on every screen. There, questions also carry what you are looking at (supplier, line or finding).</Notice>
        <Notice tone="info">Answers are analysis, not an award decision. Clarification drafts are never sent automatically.</Notice>
        {turns.length > 0 && <Button variant="ghost" onClick={reset} icon={<RotateCcw size={14} />}>New conversation</Button>}
      </div>
    </div>
  );
}

function Drafting() {
  const { rfxId, setRfxId, refresh, reloadList } = useRfx();
  const [h, setH] = useState<any>(null);
  const [mapping, setMapping] = useState<any[] | null>(null);
  const [gapText, setGapText] = useState("");
  const [gapPatch, setGapPatch] = useState<any>(null);
  const [qdraft, setQdraft] = useState<any>(null);
  const [log, setLog] = useState<{ ok: boolean; text: string }[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const note = (ok: boolean, text: string) => setLog((l) => [{ ok, text }, ...l].slice(0, 8));
  const load = (id = rfxId) => api(`/rfx/${id}`).then(setH).catch(() => setH(null));
  useEffect(() => { load(); }, [rfxId]);
  const run = async (label: string, fn: () => Promise<any>) => {
    setBusy(label);
    try { const r = await fn(); note(true, `${label}: done`); await load(); await refresh(); return r; }
    catch (e) { note(false, `${label}: ${String(e).replace(/^Error: /, "")}`); } finally { setBusy(null); }
  };
  const start = (sandbox: boolean) => run(sandbox ? "New sandbox RFx" : "Draft from brief pack", async () => {
    const r = await api("/rfx/primary", { body: { title: sandbox ? "Sandbox RFx" : "Annual corrugated packaging RFx", sandbox } });
    await reloadList(); setRfxId(r.rfx_id); setMapping(r.mapping_proposal.mappings); await load(r.rfx_id);
  });
  const steps = [
    { label: "Draft", done: !!h?.patches.some((p: any) => p.action.startsWith("MAPPING_CONFIRMED") || p.action === "SEEDED_FALLBACK_LOADED") },
    { label: "Questionnaire", done: !!h?.patches.some((p: any) => p.action === "QUESTIONNAIRE_APPLIED" || p.action === "SEEDED_FALLBACK_LOADED") },
    { label: "Conformance", done: !!h?.conformance },
    { label: "Approved", done: ["approved", "sent"].includes(h?.status) },
    { label: "Sent", done: h?.status === "sent" },
  ];
  return (
    <div className="stack" style={{ gap: 16 }}>
      {h && <Card title={<span className="row" style={{ gap: 8 }}>RFx #{h.rfx_id} · {h.title}</span>} actions={<><Badge tone="info">{h.label}</Badge><Badge tone="outline">{h.status}</Badge></>}>
        <div className="steps" style={{ flexDirection: "row", gap: 8, flexWrap: "wrap" }}>{steps.map((s, i) => (
          <div key={s.label} className={`step ${s.done ? "done" : ""}`} style={{ flex: 1, minWidth: 120 }}><span className="ix">{i + 1}</span><span className="lb"><b>{s.label}</b><span className="subtle">{s.done ? "Complete" : "Pending"}</span></span></div>))}</div>
        <dl className="kv" style={{ marginTop: 14 }}>
          <dt>Scope</dt><dd>{h.scope ?? <span className="subtle">Not yet drafted — answer the open fields below</span>}</dd>
          <dt>Delivery</dt><dd>{h.delivery_location ?? "—"}</dd>
          <dt>Terms</dt><dd>{h.terms?.length ? <ul style={{ margin: 0, paddingLeft: 18 }}>{h.terms.map((t: any) => <li key={t.type}>{t.text}{t.source && <span className="subtle"> · cited {t.source.unit_ids.join(", ")}</span>}</li>)}</ul> : "—"}</dd>
          <dt>Conformance</dt><dd>{h.conformance ? (h.conformance.conforms ? <Badge tone="success">Conforms to the canonical spec</Badge> : <Badge tone="warning">{h.conformance.differences.length} differences</Badge>) : "Not checked"}</dd>
        </dl>
      </Card>}
      <Card title="Start or load an RFx">
        <div className="row wrap"><Button variant="primary" loading={busy === "Draft from brief pack"} onClick={() => start(false)}>Draft from the brief pack (AI)</Button>
          <Button loading={busy === "New sandbox RFx"} onClick={() => start(true)}>New sandbox RFx (AI)</Button>
          <Button loading={busy === "Load seeded fallback"} onClick={() => run("Load seeded fallback", async () => { const r = await api("/rfx/seeded-fallback", { body: {} }); await reloadList(); setRfxId(r.rfx_id); })}>Load seeded fallback (no AI)</Button></div>
        <div className="subtle" style={{ marginTop: 8 }}>AI steps are proposals: nothing changes the RFx until you confirm it. AI steps need the API key.</div>
      </Card>
      {mapping && <Card title="1 · Column mapping (AI proposal — confirm or edit)">
        <table className="t dense"><tbody>{mapping.map((m, i) => (
          <tr key={i}><td>{m.column}</td><td>→</td><td><input className="input" value={m.field ?? ""} onChange={(e) => setMapping(mapping.map((x, k) => k === i ? { ...x, field: e.target.value } : x))} /></td>
            <td>{m.confidence !== "HIGH" && <Badge tone="warning">{m.confidence} confidence</Badge>}</td></tr>))}</tbody></table>
        <Button variant="primary" style={{ marginTop: 10 }} loading={busy === "Confirm mapping"} onClick={() => run("Confirm mapping", async () => {
          const r = await api(`/rfx/${rfxId}/mapping/confirm`, { body: { mapping: Object.fromEntries(mapping.filter((m) => m.field).map((m) => [m.column, m.field])) } });
          note(true, `Imported ${r.lines} lines; open fields: ${r.rfx_gaps.join(", ")}`); setMapping(null); })}>Confirm and import rows</Button>
      </Card>}
      <Card title="2 · Open fields">
        <textarea className="textarea" value={gapText} onChange={(e) => setGapText(e.target.value)} style={{ height: 70 }}
          placeholder="Answer the co-pilot: what you’re buying and for how long, delivery location, dimension convention, validity, GST basis…" />
        <div className="row" style={{ marginTop: 8 }}><Button disabled={!gapText} loading={busy === "Propose answers"} onClick={() => run("Propose answers", async () => setGapPatch(await api(`/rfx/${rfxId}/gaps/propose`, { body: { text: gapText } })))}>Propose (AI)</Button></div>
        {gapPatch && <div style={{ marginTop: 10 }}>{Object.entries(gapPatch).filter(([, v]) => v).map(([k, v]: any) => <div key={k} style={{ fontSize: 13 }}><b>{k}</b>: {v.value} <span className="subtle">— “{v.quote}”</span></div>)}
          <Button variant="primary" style={{ marginTop: 8 }} onClick={() => run("Apply answers", async () => { const r = await api(`/rfx/${rfxId}/gaps/apply`, { body: { patch: gapPatch, source_text: gapText } });
            note(true, `Rejected (quote not in your text): ${r.rejected.join(", ") || "none"}`); setGapPatch(null); })}>Apply</Button></div>}
      </Card>
      <Card title="3 · Questionnaire and terms (cited to the checklist and policy)">
        <Button loading={busy === "Draft questionnaire"} onClick={() => run("Draft questionnaire", async () => setQdraft(await api(`/rfx/${rfxId}/questionnaire/propose`, { body: {} })))}>Draft questionnaire (AI)</Button>
        {qdraft && <div style={{ marginTop: 10 }}>
          <table className="t dense"><tbody>{qdraft.draft.questions.map((q: any, i: number) => { const v = qdraft.validation.find((x: any) => x.key === q.requirement_key); return (
            <tr key={i}><td className="mono">{q.no}</td><td>{q.section}</td><td>{q.text}</td><td>{v?.ok ? <Badge tone="success">Citation verified</Badge> : <Badge tone="critical">Rejected: {v?.problems.join(", ")}</Badge>}</td></tr>); })}</tbody></table>
          <Button variant="primary" style={{ marginTop: 8 }} disabled={!qdraft.validation.every((v: any) => v.ok)} onClick={() => run("Apply questionnaire", async () => { await api(`/rfx/${rfxId}/questionnaire/apply`, { body: { draft: qdraft.draft } }); setQdraft(null); })}>Apply all</Button></div>}
      </Card>
      <Card title="4 · Check, approve, send, read">
        <div className="row wrap">
          <Button loading={busy === "Conformance check"} onClick={() => run("Conformance check", () => api(`/rfx/${rfxId}/conformance`, { body: {} }))}>Conformance check</Button>
          <Button loading={busy === "Approve"} onClick={() => run("Approve", () => api(`/rfx/${rfxId}/approve`, { body: {} }))}>Approve</Button>
          <Button loading={busy === "Send to vendors"} onClick={() => run("Send to vendors", () => api(`/rfx/${rfxId}/send`, { body: {} }))}>Send to vendors</Button>
          <Button loading={busy === "Deliver next response"} onClick={() => run("Deliver next response", async () => { const r = await api(`/rfx/${rfxId}/deliver-next`, { body: {} }); note(true, r.delivered ? `Delivered ${r.delivered.path}` : "Inbox empty"); })}>Deliver next response</Button>
          <Button variant="primary" loading={busy === "Read responses"} onClick={() => run("Read responses", async () => { const r = await api(`/rfx/${rfxId}/process`, { body: {} });
            note(true, `Read: ${r.processed_vendors.join(", ") || "nothing new"}${Object.keys(r.failed).length ? "; failed: " + Object.keys(r.failed).join(", ") : ""}`); })}>Read responses (AI)</Button>
        </div>
        {h?.conformance && !h.conformance.conforms && <ul className="subtle">{h.conformance.differences.slice(0, 10).map((d: any, i: number) => <li key={i}>{JSON.stringify(d)}</li>)}</ul>}
        {log.length > 0 && <div className="stack" style={{ gap: 6, marginTop: 12 }}>{log.map((l, i) => <Notice key={i} tone={l.ok ? "success" : "critical"}>{l.text}</Notice>)}</div>}
      </Card>
    </div>
  );
}

export default function Copilot() {
  const [sp, setSp] = useSearchParams();
  const tab = sp.get("tab") === "draft" ? "draft" : "ask";
  return (
    <div className="stack" style={{ gap: 18 }}>
      <PageHeader title="Co-pilot" sub="Interrogate this RFx with sources, or run the RFx drafting workflow." />
      <Tabs value={tab} onChange={(t) => setSp(t === "ask" ? {} : { tab: t })} tabs={[{ key: "ask", label: <><MessageSquareText size={14} /> Ask</> }, { key: "draft", label: <><ClipboardList size={14} /> RFx drafting</> }]} />
      {tab === "ask" ? <Assistant /> : <Drafting />}
    </div>
  );
}
