// Settings: only settings that work or are explained. Every change is audited; FX and constants recompute the comparison.
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Download } from "lucide-react";
import { api } from "../api";
import { useRfx } from "../rfx";
import { Badge, Button, Card, DataTable, Notice, PageHeader, SearchInput, Skeleton } from "../ui";
import { fmtTime } from "./Home";

const SECTIONS = [
  { key: "rfx", label: "RFx metadata" }, { key: "criteria", label: "Evaluation criteria" }, { key: "commercial", label: "Commercial policy" },
  { key: "normalisation", label: "Units & currency" }, { key: "audit", label: "Audit log & export" },
];

function Metadata() {
  const { rfxId, overview, refresh, reloadList } = useRfx();
  const m = overview?.rfx.meta ?? {};
  const [form, setForm] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<{ ok: boolean; t: string } | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { setForm({ code: m.code ?? "", buyer: m.buyer ?? "", buyer_name: m.buyer_name ?? "", category: m.category ?? "", plant: m.plant ?? "", currency: m.currency ?? "" }); }, [overview?.rfx.rfx_id]);
  const save = async () => {
    setBusy(true);
    try { await api(`/rfx/${rfxId}/meta`, { method: "PUT", body: form }); await refresh(); await reloadList(); setMsg({ ok: true, t: "Saved. The change is recorded in the audit log." }); }
    catch (e) { setMsg({ ok: false, t: String(e) }); } finally { setBusy(false); }
  };
  const F = (k: string, label: string) => <label className="field">{label}<input className="input" value={form[k] ?? ""} onChange={(e) => setForm({ ...form, [k]: e.target.value })} /></label>;
  return (
    <Card title="RFx metadata" actions={<Badge tone="violet">Demo / evaluation RFx</Badge>}>
      <div className="grid g2" style={{ gap: 14 }}>
        <label className="field">Title<input className="input" value={overview?.rfx.title ?? ""} disabled /></label>
        <label className="field">RFx ID<input className="input" value={`#${rfxId}`} disabled /></label>
        {F("code", "RFx code")}{F("buyer", "Buying organisation")}{F("buyer_name", "Buyer")}{F("category", "Category")}{F("plant", "Plant / delivery location")}{F("currency", "Comparison currency")}
      </div>
      <div className="subtle" style={{ marginTop: 10 }}>The comparison currency is a label: prices are always normalised to INR ex-GST. Title and line items are set by the drafting workflow.</div>
      <div className="row" style={{ marginTop: 14 }}><Button variant="primary" loading={busy} onClick={save}>Save metadata</Button>{msg && <Notice tone={msg.ok ? "success" : "critical"}>{msg.t}</Notice>}</div>
    </Card>
  );
}

function Criteria({ rfx }: { rfx: any }) {
  if (!rfx) return <Skeleton />;
  return (
    <Card pad={false} title="Evaluation criteria" actions={<Badge tone="outline">{rfx.questions?.length ?? 0} questions</Badge>}>
      <div style={{ padding: "12px 16px" }} className="muted">Qualification is pass/fail per question; there are no weightings. Price is compared only among suppliers that pass the quality gate (strict mode). Questions are set when the RFx is drafted and cannot be edited after it is sent.</div>
      <DataTable dense rows={rfx.questions ?? []} rowKey={(q: any) => q.key} columns={[
        { key: "k", label: "Key", render: (q: any) => <span className="mono">{q.no} {q.key}</span> },
        { key: "s", label: "Section", render: (q: any) => <Badge tone={q.section === "QUALITY" ? "info" : "neutral"}>{q.section.toLowerCase()}</Badge> },
        { key: "t", label: "Requirement", render: (q: any) => <div style={{ maxWidth: 520 }}>{q.text}</div> },
        { key: "r", label: "Pass rule", render: (q: any) => q.pass_rule ? <span className="mono">{q.pass_rule.op} {q.pass_rule.value ?? ""}</span> : <span className="subtle">—</span> },
        { key: "e", label: "Evidence", render: (q: any) => q.evidence_required ? <span>{(q.evidence_doc_type ?? "document").replace(/_/g, " ").toLowerCase()}</span> : <span className="subtle">Not required</span> },
        { key: "a", label: "Applies to", render: (q: any) => <span className="subtle">{q.applicability.replace(/_/g, " ").toLowerCase()}</span> },
      ]} />
    </Card>
  );
}

function Commercial({ rfx }: { rfx: any }) {
  if (!rfx) return <Skeleton />;
  return (
    <Card title="Commercial policy" actions={<Badge tone="outline">From the buyer policy</Badge>}>
      <div className="muted" style={{ marginBottom: 12 }}>Terms were drafted by the co-pilot from the buyer policy document, each with its citation. They are part of the issued RFx and cannot be changed here.</div>
      <div className="stack" style={{ gap: 10 }}>{(rfx.terms ?? []).map((t: any) => (
        <div key={t.type} className="row" style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "10px 14px", alignItems: "flex-start" }}>
          <Badge tone="neutral">{t.type.replace(/_/g, " ").toLowerCase()}</Badge><div style={{ flex: 1 }}><div>{t.text}</div>
            {t.source && <div className="subtle">Source {t.source.unit_ids.join(", ")}: “{t.source.quote}”</div>}</div></div>))}</div>
      <dl className="kv" style={{ marginTop: 14 }}><dt>Response basis</dt><dd>{rfx.response_basis ? JSON.stringify(rfx.response_basis) : "—"}</dd><dt>Delivery</dt><dd>{rfx.delivery_location ?? "—"}</dd></dl>
    </Card>
  );
}

function Normalisation() {
  const [fx, setFx] = useState<any>(null);
  const [sets, setSets] = useState<any[]>([]);
  const [rate, setRate] = useState(""); const [asOf, setAsOf] = useState(""); const [src, setSrc] = useState("");
  const [changes, setChanges] = useState<Record<string, string>>({}); const [ver, setVer] = useState(""); const [why, setWhy] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; t: string } | null>(null);
  const { refresh } = useRfx();
  const load = () => { api("/settings/fx").then(setFx).catch(() => setFx({})); api("/settings/constants").then(setSets).catch(() => setSets([])); };
  useEffect(load, []);
  const act = async (fn: () => Promise<any>, ok: string) => { try { await fn(); setMsg({ ok: true, t: ok }); load(); refresh(); } catch (e) { setMsg({ ok: false, t: String(e) }); } };
  const active = sets.find((s) => s.active);
  return (
    <div className="stack" style={{ gap: 16 }}>
      {msg && <Notice tone={msg.ok ? "success" : "critical"}>{msg.t}</Notice>}
      <Card title="FX rate (USD → INR)">
        <div className="muted" style={{ marginBottom: 10 }}>Policy: one dated rate with a named source per currency. USD prices stay Unresolved until a rate is set. Changing it recomputes the comparison and is audited.</div>
        {fx === null ? <Skeleton rows={1} /> : <dl className="kv"><dt>Current</dt><dd>{fx.USD ? <><b className="num">{fx.USD.rate}</b> as of {fx.USD.as_of} · {fx.USD.source}</> : <span className="subtle">Not set</span>}</dd></dl>}
        <div className="row wrap" style={{ marginTop: 12, alignItems: "flex-end" }}>
          <label className="field">Rate<input className="input" value={rate} onChange={(e) => setRate(e.target.value)} style={{ width: 100 }} /></label>
          <label className="field">As of<input className="input" type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} /></label>
          <label className="field">Source<input className="input" value={src} onChange={(e) => setSrc(e.target.value)} placeholder="e.g. RBI reference rate" style={{ width: 220 }} /></label>
          <Button variant="primary" disabled={!rate || !asOf || !src} onClick={() => act(() => api("/settings/fx/USD", { method: "PUT", body: { rate_to_inr: rate, as_of: asOf, source: src } }), "FX rate saved; comparison recomputed.")}>Save and recompute</Button>
        </div>
      </Card>
      <Card pad={false} title="Unit conversion constants" actions={active && <Badge tone="info">Active: {active.version}</Badge>}>
        <div style={{ padding: "12px 16px" }} className="muted">Used to convert ₹/kg quotes to ₹/box (board weight). Edit values to create a new version; activate it to recompute. Every version is kept.</div>
        {active && <DataTable dense rows={active.constants} rowKey={(c: any) => c.key} columns={[
          { key: "k", label: "Constant", render: (c: any) => <span className="mono">{c.key}</span> }, { key: "v", label: "Value", right: true, render: (c: any) => <span className="num">{c.value}</span> },
          { key: "u", label: "Unit", render: (c: any) => <span className="subtle">{c.unit}</span> }, { key: "l", label: "Validation", render: (c: any) => <Badge tone="outline">{c.label}</Badge> },
          { key: "n", label: "New value", render: (c: any) => <input className="input" style={{ width: 90, height: 30 }} value={changes[c.key] ?? ""} onChange={(e) => setChanges({ ...changes, [c.key]: e.target.value })} aria-label={`New value for ${c.key}`} /> },
        ]} />}
        <div className="row wrap" style={{ padding: 16, alignItems: "flex-end" }}>
          <label className="field">New version<input className="input" value={ver} onChange={(e) => setVer(e.target.value)} /></label>
          <label className="field">Reason / source<input className="input" value={why} onChange={(e) => setWhy(e.target.value)} style={{ width: 260 }} /></label>
          <Button disabled={!ver || !why || !active} onClick={() => act(() => api("/settings/constants", { body: { base_version: active.version, new_version: ver, reason: why, changes: Object.fromEntries(Object.entries(changes).filter(([, v]) => v)) } }), `Version ${ver} created (not active).`)}>Create version</Button>
        </div>
        <div style={{ padding: "0 16px 16px" }} className="row wrap">{sets.map((s) => s.active ? <Badge key={s.version} tone="success">{s.version} · active</Badge> :
          <Button key={s.version} size="sm" onClick={() => act(() => api(`/settings/constants/${s.version}/activate`, { body: { reason: why || "activated in settings" } }), `${s.version} activated; comparison recomputed.`)}>Activate {s.version}</Button>)}</div>
      </Card>
    </div>
  );
}

function Audit() {
  const { rfxId } = useRfx();
  const [rows, setRows] = useState<any[] | null>(null);
  const [q, setQ] = useState("");
  useEffect(() => { api(`/rfx/${rfxId}/audit`).then(setRows).catch(() => setRows([])); }, [rfxId]);
  const shown = (rows ?? []).filter((r) => `${r.action} ${r.actor} ${r.reason ?? ""}`.toLowerCase().includes(q.toLowerCase())).slice().reverse();
  return (
    <div className="stack" style={{ gap: 16 }}>
      <Card title="Data export">
        <div className="row wrap"><a className="btn" href={`/api/rfx/${rfxId}/export.xlsx?basis=unit`}><Download size={15} />Comparison (XLSX, unit)</a>
          <a className="btn" href={`/api/rfx/${rfxId}/export.xlsx?basis=landed`}><Download size={15} />Comparison (XLSX, landed)</a>
          <a className="btn" href={`/api/rfx/${rfxId}/audit.csv`}><Download size={15} />Audit log (CSV)</a></div>
        <div className="subtle" style={{ marginTop: 8 }}>Supplier responses are imported through Vendors & Inbox (upload) or the Co-pilot drafting workflow.</div>
      </Card>
      <Card pad={false} title={<span>Audit log <Badge tone="neutral">{rows?.length ?? "…"}</Badge></span>} actions={<SearchInput value={q} onChange={setQ} placeholder="Filter events" width={220} />}>
        {rows === null ? <div style={{ padding: 16 }}><Skeleton /></div> : <DataTable dense rows={shown} rowKey={(r: any) => r.id} maxHeight={560} columns={[
          { key: "t", label: "When", render: (r: any) => <span className="subtle" style={{ whiteSpace: "nowrap" }}>{fmtTime(r.at)}</span> },
          { key: "a", label: "Actor", render: (r: any) => r.actor }, { key: "e", label: "Event", render: (r: any) => <span className="mono">{r.action}</span> },
          { key: "r", label: "Reason", render: (r: any) => <span className="muted">{r.reason ?? ""}</span> },
          { key: "c", label: "Change", render: (r: any) => <span className="subtle mono" style={{ display: "block", maxWidth: 420, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={JSON.stringify(r.after)}>{r.after ? JSON.stringify(r.after) : ""}</span> },
        ]} />}
      </Card>
    </div>
  );
}

export default function Settings() {
  const { rfxId } = useRfx();
  const [sp, setSp] = useSearchParams();
  const sec = sp.get("section") ?? "rfx";
  const [rfx, setRfx] = useState<any>(null);
  useEffect(() => { if (rfxId) api(`/rfx/${rfxId}`).then(setRfx).catch(() => setRfx(null)); }, [rfxId]);
  return (
    <div className="stack" style={{ gap: 18 }}>
      <PageHeader title="Settings" sub="RFx configuration, normalisation preferences and audit. Settings that cannot be changed are explained, not shown as dead controls." />
      <div className="split" style={{ gridTemplateColumns: "220px 1fr", alignItems: "start" }}>
        <nav className="nav card" style={{ padding: 8 }}>{SECTIONS.map((s) => (
          <a key={s.key} href={`?section=${s.key}`} className={sec === s.key ? "active" : ""} onClick={(e) => { e.preventDefault(); setSp({ section: s.key }); }}>{s.label}</a>))}</nav>
        <div>
          {sec === "rfx" && <Metadata />}{sec === "criteria" && <Criteria rfx={rfx} />}{sec === "commercial" && <Commercial rfx={rfx} />}
          {sec === "normalisation" && <Normalisation />}{sec === "audit" && <Audit />}
        </div>
      </div>
    </div>
  );
}
