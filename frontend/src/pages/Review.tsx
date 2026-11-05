// Review: finding-level qualification and evidence review. Findings are derived by the backend from eligibility,
// cell statuses and coverage; the buyer's review state is recorded and audited (previous state kept in history).
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2, ClipboardCheck, ExternalLink, FileText, HelpCircle, MinusCircle, ShieldAlert, XCircle } from "lucide-react";
import { api } from "../api";
import ProvenanceDrawer from "../components/ProvenanceDrawer";
import { Finding, OPEN, useRfx } from "../rfx";
import { Badge, Button, Card, DataTable, Drawer, EmptyState, MetricCard, Notice, PageHeader, SearchInput, Select, Skeleton, StatusBadge } from "../ui";
import { fmtTime } from "./Home";
import { useAssistantScope } from "../assistant";

const CATEGORIES = ["Quality & compliance", "Commercial terms", "Quote completeness", "Specification deviations", "Document validity"];
const NOT_PROVIDED = /not provided|no .*attached|not attached|claimed, but|could not be read|not stated|not quoted/i;
export type Outcome = "fail" | "needs_review" | "not_provided";
export const outcome = (f: Finding): Outcome => f.severity === "blocker" ? "fail"
  : f.kind === "missing" || NOT_PROVIDED.test(f.concern) || NOT_PROVIDED.test(f.title) ? "not_provided" : "needs_review";
const OUT_LABEL: Record<Outcome, string> = { fail: "Fail / blocker", needs_review: "Needs review", not_provided: "Not provided" };

const ACTIONS = [
  { state: "confirmed", label: "Confirm", hint: "The finding is correct; it stays open until the supplier resolves it.", needs: false },
  { state: "clarification_requested", label: "Request clarification", hint: "Ask the supplier; the finding stays open.", needs: false },
  { state: "rejected", label: "Reject", hint: "The finding is wrong. A reason is required and kept in the audit trail.", needs: true },
  { state: "not_applicable", label: "Mark not applicable", hint: "Does not apply to this award. A reason is required.", needs: true },
];

function FindingDrawer({ f, onClose, onChanged }: { f: Finding; onClose: () => void; onChanged: () => void }) {
  const { rfxId } = useRfx();
  const nav = useNavigate();
  const [hist, setHist] = useState<any[] | null>(null);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [cell, setCell] = useState<number | null>(null);
  const loadHist = () => api(`/rfx/${rfxId}/findings/${f.id}/history`).then(setHist).catch(() => setHist([]));
  useEffect(() => { loadHist(); setErr(null); setComment(""); }, [f.id]);
  const act = async (state: string) => {
    setBusy(state); setErr(null);
    try { await api(`/rfx/${rfxId}/findings/${f.id}/review`, { body: { state, comment: comment || undefined, actor: "buyer" } }); setComment(""); await onChanged(); await loadHist(); }
    catch (e) { setErr(String(e).replace(/^Error: /, "")); } finally { setBusy(null); }
  };
  const fileUrl = f.source?.filename && f.vendor_id ? `/api/rfx/${rfxId}/vendors/${f.vendor_id}/file?name=${encodeURIComponent(f.source.filename)}` : null;
  return (
    <Drawer title={f.title} sub={`${f.vendor_key ? `${f.vendor_key} · ${f.vendor}` : "All vendors"} · ${f.category}`} onClose={onClose}>
      <div className="stack" style={{ gap: 16 }}>
        <div className="row wrap" style={{ gap: 6 }}><StatusBadge status={f.severity} /><Badge tone="outline">{OUT_LABEL[outcome(f)]}</Badge><StatusBadge status={f.review.state} /></div>
        <dl className="kv">
          <dt>Supplier statement</dt><dd>{f.statement ? <span className="quote" style={{ display: "block" }}>{f.statement}</span> : <span className="subtle">Nothing stated</span>}</dd>
          <dt>Requirement</dt><dd>{f.requirement ?? <span className="subtle">—</span>}</dd>
          <dt>Concern</dt><dd>{f.concern}</dd>
          {f.lines.length > 0 && <><dt>Affected SKUs</dt><dd>Lines {f.lines.join(", ")}</dd></>}
          <dt>Evidence</dt><dd>{fileUrl ? <a href={fileUrl} target="_blank" rel="noreferrer" className="row" style={{ gap: 4 }}><FileText size={13} />{f.source.filename}<ExternalLink size={11} /></a>
            : f.source?.evidence?.length ? <span className="mono">{f.source.evidence.join(", ")}</span> : <span className="subtle">See the affected lines</span>}</dd>
          <dt>System confidence</dt><dd>{f.confidence ?? <span className="subtle">—</span>} <div className="subtle">Extraction confidence is separate from the compliance outcome.</div></dd>
        </dl>
        <div className="row wrap"><Button size="sm" icon={<ExternalLink size={13} />} onClick={() => nav(f.target)}>Open source view</Button></div>

        {f.kind === "cells" && f.vendor_id && <div><div className="section-title">Inspect affected cells</div>
          <div className="row wrap" style={{ gap: 6 }}>{f.lines.map((l) => <Button key={l} size="sm" variant="ghost" onClick={() => setCell(l)}>Line {l}</Button>)}</div>
          <div className="subtle" style={{ marginTop: 4 }}>Resolving a cell (accept, correct, mark not quoted) clears it from this finding.</div></div>}

        <div><div className="section-title">Human review</div>
          <textarea className="textarea" placeholder="Comment (required to reject or mark not applicable)" value={comment} onChange={(e) => setComment(e.target.value)} style={{ height: 70 }} />
          <div className="row wrap" style={{ marginTop: 8 }}>{ACTIONS.map((a) => (
            <Button key={a.state} size="sm" variant={a.state === "confirmed" ? "primary" : a.state === "rejected" ? "danger" : "secondary"} title={a.hint}
              disabled={(a.needs && !comment.trim()) || f.review.state === a.state} loading={busy === a.state} onClick={() => act(a.state)}>{a.label}</Button>))}
            {f.review.state !== "open" && <Button size="sm" variant="ghost" loading={busy === "open"} onClick={() => act("open")}>Reopen</Button>}</div>
          {err && <div style={{ marginTop: 8 }}><Notice tone="critical">{err}</Notice></div>}
        </div>

        <div><div className="section-title">Audit trail</div>
          {hist === null ? <Skeleton rows={2} /> : hist.length === 0 ? <div className="subtle">No review actions yet. Current state: open.</div> : (
            <table className="t dense"><tbody>{hist.slice().reverse().map((h, i) => (
              <tr key={i}><td className="subtle" style={{ whiteSpace: "nowrap" }}>{fmtTime(h.at)}</td><td>{h.actor}</td>
                <td><StatusBadge status={h.before?.state ?? "open"} /> → <StatusBadge status={h.after?.state} /></td><td className="muted">{h.reason ?? ""}</td></tr>))}</tbody></table>)}
        </div>
      </div>
      {cell !== null && f.vendor_id && <ProvenanceDrawer rfxId={rfxId} vendorId={f.vendor_id} lineNo={cell} onClose={() => setCell(null)} onChanged={onChanged} />}
    </Drawer>
  );
}

export default function Review() {
  const { overview, rfxId, refresh } = useRfx();
  const [sp, setSp] = useSearchParams();
  const [q, setQ] = useState("");
  const [passed, setPassed] = useState<{ vendor: string; key: string; reason: string }[] | null>(null);
  const vendor = sp.get("vendor") ?? "all", cat = sp.get("category") ?? "all", sev = sp.get("severity") ?? "all",
    state = sp.get("state") ?? "open", out = sp.get("outcome") ?? "all", fid = sp.get("finding");
  const set = (k: string, v: string) => { const n = new URLSearchParams(sp); v === "all" || (k === "state" && v === "open") ? n.delete(k) : n.set(k, v); if (k !== "finding") n.delete("finding"); setSp(n); };
  const findings = overview?.findings ?? [];
  const vendors = overview?.vendors ?? [];
  useEffect(() => {
    Promise.all(vendors.map((v) => api(`/rfx/${rfxId}/vendors/${v.vendor_id}/eligibility`).then((e) => ({ v, e })).catch(() => null))).then((all) =>
      setPassed(all.flatMap((x) => !x || !x.e.configured ? [] : ["quality", "commercial"].flatMap((s) => x.e[s].questions.filter((qq: any) => qq.state === "PASS")
        .map((qq: any) => ({ vendor: `${x.v.key} · ${x.v.name}`, key: qq.key, reason: qq.reason }))))));
  }, [rfxId, vendors.length]);
  const openF = findings.filter((f) => OPEN.includes(f.review.state));
  const count = (o: Outcome) => openF.filter((f) => outcome(f) === o).length;
  const rows = useMemo(() => findings.filter((f) =>
    (vendor === "all" || String(f.vendor_id) === vendor) && (cat === "all" || f.category === cat) && (sev === "all" || f.severity === sev) &&
    (state === "all" ? true : state === "open" ? OPEN.includes(f.review.state) : f.review.state === state) &&
    (out === "all" || outcome(f) === out) &&
    `${f.title} ${f.vendor ?? ""} ${f.concern}`.toLowerCase().includes(q.toLowerCase())), [findings, vendor, cat, sev, state, out, q]);
  const current = fid ? findings.find((f) => f.id === fid) : null;
  useAssistantScope(current ? { label: `Finding · ${current.vendor_key ?? "all"}`, context: `The buyer is reviewing the finding "${current.title}" for ${current.vendor ?? "all suppliers"} (${current.category}; concern: ${current.concern}${current.lines.length ? `; lines ${current.lines.join(", ")}` : ""}).`,
    prompts: ["Explain this finding and what evidence would resolve it.", "Does this finding change which supplier wins any line?"] } : null);
  const showPassed = out === "pass";
  return (
    <div className="stack" style={{ gap: 20 }}>
      <PageHeader title="Review" sub="Qualification, document validity and quote-level findings. Nothing passes because a document merely exists." />
      <div className="grid g4">
        <MetricCard icon={<CheckCircle2 size={14} color="var(--success)" />} label="Pass" value={passed === null ? "…" : passed.length} hint="qualification checks passed with valid evidence" onClick={() => set("outcome", "pass")} />
        <MetricCard icon={<HelpCircle size={14} color="var(--warning)" />} label="Needs review" value={count("needs_review")} hint="open warnings and information" onClick={() => set("outcome", "needs_review")} />
        <MetricCard icon={<XCircle size={14} color="var(--critical)" />} label="Fail / blocker" value={count("fail")} alert={count("fail") > 0} hint="open blockers — must be resolved before award" onClick={() => set("outcome", "fail")} />
        <MetricCard icon={<MinusCircle size={14} />} label="Not provided" value={count("not_provided")} hint="non-blocking: lines not quoted, terms not stated" onClick={() => set("outcome", "not_provided")} />
      </div>
      <Card pad={false} title={<span className="row" style={{ gap: 8 }}><ClipboardCheck size={16} />{showPassed ? "Passed checks" : "Findings"} <Badge tone="neutral">{showPassed ? passed?.length ?? 0 : rows.length}</Badge></span>}
        actions={<>
          <SearchInput value={q} onChange={setQ} placeholder="Search findings" width={200} />
          <Select value={vendor} onChange={(v) => set("vendor", v)} options={[{ value: "all", label: "Vendor: all" }, ...vendors.map((v) => ({ value: String(v.vendor_id), label: `${v.key} · ${v.name}` }))]} />
          <Select value={cat} onChange={(v) => set("category", v)} options={[{ value: "all", label: "Category: all" }, ...CATEGORIES.map((c) => ({ value: c, label: c }))]} />
          <Select value={sev} onChange={(v) => set("severity", v)} options={[{ value: "all", label: "Severity: all" }, { value: "blocker", label: "Blocker" }, { value: "warning", label: "Warning" }, { value: "info", label: "Info" }]} />
          <Select value={state} onChange={(v) => set("state", v)} options={[{ value: "open", label: "State: open" }, { value: "all", label: "State: all" }, { value: "confirmed", label: "Confirmed" },
            { value: "clarification_requested", label: "Clarification requested" }, { value: "rejected", label: "Dismissed" }, { value: "not_applicable", label: "Not applicable" }]} />
          {out !== "all" && <Button size="sm" variant="ghost" onClick={() => set("outcome", "all")}>Clear outcome filter</Button>}
        </>}>
        {showPassed ? (passed === null ? <div style={{ padding: 16 }}><Skeleton /></div> :
          <DataTable rows={passed} rowKey={(p) => p.vendor + p.key} columns={[
            { key: "v", label: "Supplier", render: (p) => p.vendor }, { key: "k", label: "Check", render: (p) => <span className="mono">{p.key}</span> },
            { key: "s", label: "Outcome", render: () => <StatusBadge status="Passed" /> }, { key: "r", label: "Basis", render: (p) => <span className="muted">{p.reason}</span> }]} />) :
        <DataTable rows={rows} rowKey={(f) => f.id} onRowClick={(f) => { const n = new URLSearchParams(sp); n.set("finding", f.id); setSp(n); }}
          empty={<EmptyState icon={<ShieldAlert size={22} />} title="No findings match these filters" />}
          initialSort={{ key: "sev", dir: 1 }}
          columns={[
            { key: "sev", label: "Severity", sort: (f) => ({ blocker: 0, warning: 1, info: 2 }[f.severity]), render: (f) => <StatusBadge status={f.severity} /> },
            { key: "t", label: "Finding", sort: (f) => f.title, render: (f) => <div style={{ maxWidth: 460 }}><div style={{ fontWeight: 500 }}>{f.title}</div>{!f.title.toLowerCase().includes(f.concern.toLowerCase().slice(0, 40)) && <div className="subtle">{f.concern}</div>}</div> },
            { key: "v", label: "Supplier", sort: (f) => f.vendor_key ?? "", render: (f) => f.vendor_key ? <span><span className="mono">{f.vendor_key}</span> <span className="subtle">{f.vendor}</span></span> : <span className="subtle">All</span> },
            { key: "c", label: "Category", sort: (f) => f.category, render: (f) => <span className="subtle">{f.category}</span> },
            { key: "l", label: "SKUs", render: (f) => f.lines.length ? <span className="num">{f.lines.length}</span> : <span className="subtle">—</span> },
            { key: "o", label: "Outcome", render: (f) => <Badge tone="outline">{OUT_LABEL[outcome(f)]}</Badge> },
            { key: "s", label: "Review state", sort: (f) => f.review.state, render: (f) => <StatusBadge status={f.review.state} /> },
          ]} />}
      </Card>
      {current && <FindingDrawer f={current} onClose={() => set("finding", "all")} onChanged={refresh} />}
    </div>
  );
}
