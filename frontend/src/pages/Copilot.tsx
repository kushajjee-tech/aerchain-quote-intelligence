// Co-pilot: (1) the RFx assistant, full-size (the same conversation as the "Ask AI" panel on every screen);
// (2) the RFx drafting workflow, in order: add RFx → confirm columns → fill open fields → questionnaire → check → approve → send → read replies.
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

const Hint = ({ children }: { children: React.ReactNode }) => <div className="subtle" style={{ marginBottom: 10 }}>{children}</div>;

function Drafting() {
  const { rfxId, setRfxId, refresh, reloadList } = useRfx();
  const [h, setH] = useState<any>(null);
  const [mapping, setMapping] = useState<any[] | null>(null);
  const [gapText, setGapText] = useState("");
  const [gapPatch, setGapPatch] = useState<any>(null);
  const [qdraft, setQdraft] = useState<any>(null);
  const [adding, setAdding] = useState(false);
  const [log, setLog] = useState<{ ok: boolean; text: string }[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const note = (ok: boolean, text: string) => setLog((l) => [{ ok, text }, ...l].slice(0, 6));
  const load = (id = rfxId) => api(`/rfx/${id}`).then(setH).catch(() => setH(null));
  useEffect(() => { load(); setAdding(false); }, [rfxId]);
  const run = async (label: string, fn: () => Promise<any>) => {
    setBusy(label);
    try { const r = await fn(); note(true, `${label}: done`); await load(); await refresh(); return r; }
    catch (e) { note(false, `${label}: ${String(e).replace(/^Error: /, "")}`); } finally { setBusy(null); }
  };
  const start = (sandbox: boolean) => run(sandbox ? "New sandbox RFx" : "Draft from brief pack", async () => {
    const r = await api("/rfx/primary", { body: { title: sandbox ? "Sandbox RFx" : "Annual corrugated packaging RFx", sandbox } });
    await reloadList(); setRfxId(r.rfx_id); setMapping(r.mapping_proposal.mappings); setAdding(false); await load(r.rfx_id);
  });
  const open: string[] = h?.open_fields ?? [];
  const questionnaireDone = !!h?.patches.some((p: any) => p.action === "QUESTIONNAIRE_APPLIED" || p.action === "SEEDED_FALLBACK_LOADED");
  const checked = !!h?.conformance?.conforms;
  const approved = ["approved", "sent"].includes(h?.status);
  const sent = h?.status === "sent";
  // The one step to do next. Everything else is hidden until it is needed.
  const current = !h || adding ? "add" : mapping ? "columns" : open.length > 0 ? "fields" : !questionnaireDone ? "questionnaire"
    : !approved ? "check" : !sent ? "send" : "replies";
  const steps = [["Add", "add"], ["Fill in", "fields"], ["Questions", "questionnaire"], ["Check", "check"], ["Send", "send"], ["Replies", "replies"]] as const;
  const stepIndex = { add: 0, columns: 0, fields: 1, questionnaire: 2, check: 3, send: 4, replies: 5 } as Record<string, number>;
  return (
    <div className="stack" style={{ gap: 16 }}>
      {h && !adding && <Card title={`RFx #${h.rfx_id} · ${h.title}`} actions={<Badge tone="outline">{h.status}</Badge>}>
        <div className="row wrap" style={{ gap: 6 }}>{steps.map(([label], i) => (
          <Badge key={label} tone={i < stepIndex[current] ? "success" : i === stepIndex[current] ? "info" : "outline"}>{i + 1}. {label}</Badge>))}</div>
        <dl className="kv" style={{ marginTop: 14 }}>
          <dt>Scope</dt><dd>{h.scope ?? <span className="subtle">Not filled in yet</span>}</dd>
          <dt>Delivery</dt><dd>{h.delivery_location ?? "—"}</dd>
        </dl>
        <Button variant="ghost" style={{ marginTop: 10 }} onClick={() => setAdding(true)}>+ Start another RFx</Button>
      </Card>}

      {current === "add" && <Card title="Add an RFx">
        <Hint>Creates a new RFx from the brief files. The AI only suggests; nothing changes until you confirm.</Hint>
        <div className="row wrap">
          <Button variant="primary" loading={busy === "Draft from brief pack"} onClick={() => start(false)}>Draft from brief pack (AI)</Button>
          <Button loading={busy === "New sandbox RFx"} onClick={() => start(true)}>New sandbox RFx (AI)</Button>
          <Button loading={busy === "Load seeded fallback"} onClick={() => run("Load seeded fallback", async () => { const r = await api("/rfx/seeded-fallback", { body: {} }); await reloadList(); setRfxId(r.rfx_id); setAdding(false); })}>Ready-made RFx (no AI)</Button>
        </div>
        <Hint>Sandbox: for trying things out, never sent to vendors. Ready-made: a fixed reference copy, no AI.</Hint>
      </Card>}

      {current === "columns" && mapping && <Card title="Confirm columns">
        <Hint>The AI matched each spreadsheet column to a field. Fix any that are wrong, then import.</Hint>
        <table className="t dense"><tbody>{mapping.map((m, i) => (
          <tr key={i}><td>{m.column}</td><td>→</td><td><input className="input" value={m.field ?? ""} onChange={(e) => setMapping(mapping.map((x, k) => k === i ? { ...x, field: e.target.value } : x))} /></td>
            <td>{m.confidence !== "HIGH" && <Badge tone="warning">{m.confidence} confidence</Badge>}</td></tr>))}</tbody></table>
        <Button variant="primary" style={{ marginTop: 10 }} loading={busy === "Confirm mapping"} onClick={() => run("Confirm mapping", async () => {
          const r = await api(`/rfx/${rfxId}/mapping/confirm`, { body: { mapping: Object.fromEntries(mapping.filter((m) => m.field).map((m) => [m.column, m.field])) } });
          note(true, `Imported ${r.lines} lines`); setMapping(null); })}>Import rows</Button>
      </Card>}

      {current === "fields" && <Card title="Fill in what is missing">
        <Hint>Still missing: {open.map((f) => f.replace(/_/g, " ")).join(", ")}. Describe them in your own words; the AI fills them in and quotes your words.</Hint>
        <textarea className="textarea" value={gapText} onChange={(e) => setGapText(e.target.value)} style={{ height: 70 }}
          placeholder="e.g. We buy 30 box types for one year, delivered to our Chakan plant, prices exclusive of GST." />
        <div className="row" style={{ marginTop: 8 }}><Button disabled={!gapText} loading={busy === "Propose answers"} onClick={() => run("Propose answers", async () => setGapPatch(await api(`/rfx/${rfxId}/gaps/propose`, { body: { text: gapText } })))}>Fill in with AI</Button></div>
        {gapPatch && <div style={{ marginTop: 10 }}>{Object.entries(gapPatch).filter(([, v]) => v).map(([k, v]: any) => <div key={k} style={{ fontSize: 13 }}><b>{k.replace(/_/g, " ")}</b>: {v.value} <span className="subtle">— “{v.quote}”</span></div>)}
          <Button variant="primary" style={{ marginTop: 8 }} onClick={() => run("Apply answers", async () => { const r = await api(`/rfx/${rfxId}/gaps/apply`, { body: { patch: gapPatch, source_text: gapText } });
            note(true, `Rejected (quote not in your text): ${r.rejected.join(", ") || "none"}`); setGapPatch(null); })}>Apply</Button></div>}
      </Card>}

      {current === "questionnaire" && <Card title="Vendor questions">
        <Hint>The AI drafts the questions. Each must point to a checklist item, or it is rejected.</Hint>
        <Button loading={busy === "Draft questionnaire"} onClick={() => run("Draft questionnaire", async () => setQdraft(await api(`/rfx/${rfxId}/questionnaire/propose`, { body: {} })))}>Draft questions (AI)</Button>
        {qdraft && <div style={{ marginTop: 10 }}>
          <table className="t dense"><tbody>{qdraft.draft.questions.map((q: any, i: number) => { const v = qdraft.validation.find((x: any) => x.key === q.requirement_key); return (
            <tr key={i}><td className="mono">{q.no}</td><td>{q.text}</td><td>{v?.ok ? <Badge tone="success">OK</Badge> : <Badge tone="critical">Rejected: {v?.problems.join(", ")}</Badge>}</td></tr>); })}</tbody></table>
          <Button variant="primary" style={{ marginTop: 8 }} disabled={!qdraft.validation.every((v: any) => v.ok)} onClick={() => run("Apply questionnaire", async () => { await api(`/rfx/${rfxId}/questionnaire/apply`, { body: { draft: qdraft.draft } }); setQdraft(null); })}>Use these questions</Button></div>}
      </Card>}

      {current === "check" && <Card title="Check and approve">
        <Hint>The check compares this RFx with the approved reference. Approve is possible only after it passes.</Hint>
        {!checked && <Button loading={busy === "Conformance check"} onClick={() => run("Conformance check", () => api(`/rfx/${rfxId}/conformance`, { body: {} }))}>Run check</Button>}
        {h?.conformance && !checked && <>
          <Notice tone="warning">{h.conformance.differences.length} differences to fix before approval.</Notice>
          <ul className="subtle">{h.conformance.differences.slice(0, 10).map((d: any, i: number) => <li key={i}>{JSON.stringify(d)}</li>)}</ul></>}
        {checked && <Button variant="primary" loading={busy === "Approve"} onClick={() => run("Approve", () => api(`/rfx/${rfxId}/approve`, { body: {} }))}>Approve</Button>}
      </Card>}

      {current === "send" && <Card title="Send to vendors">
        <Hint>This sends the RFx to every invited vendor.</Hint>
        <Button variant="primary" loading={busy === "Send to vendors"} onClick={() => run("Send to vendors", () => api(`/rfx/${rfxId}/send`, { body: {} }))}>Send to vendors</Button>
      </Card>}

      {current === "replies" && <Card title="Vendor replies">
        <Hint>Get a reply from the inbox, then read it. Repeat for each vendor.</Hint>
        <div className="row wrap">
          <Button loading={busy === "Deliver next response"} onClick={() => run("Deliver next response", async () => { const r = await api(`/rfx/${rfxId}/deliver-next`, { body: {} }); note(true, r.delivered ? `Received a reply from ${r.delivered.vendor}` : "No new replies"); })}>Get next reply</Button>
          <Button variant="primary" loading={busy === "Read responses"} onClick={() => run("Read responses", async () => { const r = await api(`/rfx/${rfxId}/process`, { body: {} });
            note(true, `Read: ${r.processed_vendors.join(", ") || "nothing new"}${Object.keys(r.failed).length ? "; failed: " + Object.keys(r.failed).join(", ") : ""}`); })}>Read replies (AI)</Button>
        </div>
      </Card>}

      {log.length > 0 && <div className="stack" style={{ gap: 6 }}>{log.map((l, i) => <Notice key={i} tone={l.ok ? "success" : "critical"}>{l.text}</Notice>)}</div>}
    </div>
  );
}

export default function Copilot() {
  const [sp, setSp] = useSearchParams();
  const tab = sp.get("tab") === "draft" ? "draft" : "ask";
  return (
    <div className="stack" style={{ gap: 18 }}>
      <PageHeader title="Co-pilot" sub="Ask questions about this RFx, or add and send a new one." />
      <Tabs value={tab} onChange={(t) => setSp(t === "ask" ? {} : { tab: t })} tabs={[{ key: "ask", label: <><MessageSquareText size={14} /> Ask</> }, { key: "draft", label: <><ClipboardList size={14} /> RFx drafting</> }]} />
      {tab === "ask" ? <Assistant /> : <Drafting />}
    </div>
  );
}
