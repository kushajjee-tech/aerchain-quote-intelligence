// Award: a buyer's recommendation, not a purchase. Allocation comes from the award engine; saving requires
// confirmation with a reason, is audited (who/when/why), and is blocked while an open blocker affects the allocation.
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, Download, FileText, Info, Lock, Play, Save, ShieldAlert } from "lucide-react";
import { api, inr } from "../api";
import { OPEN, useRfx } from "../rfx";
import { useAssistantScope } from "../assistant";
import { Badge, Button, Card, DataTable, EmptyState, ErrorState, MetricCard, Notice, PageHeader, Select, Skeleton, StatusBadge, useEscape } from "../ui";

function SaveDialog({ onClose, onSave, busy, err }: { onClose: () => void; onSave: (reason: string) => void; busy: boolean; err: string | null }) {
  const [reason, setReason] = useState("");
  useEscape(onClose);
  return (<>
    <div className="scrim" onClick={onClose} />
    <div className="dialog" role="alertdialog" aria-modal="true" style={{ width: 500 }}>
      <h3 style={{ fontSize: 16, marginBottom: 6 }}>Save award recommendation?</h3>
      <div className="muted" style={{ marginBottom: 12 }}>This records your acknowledgement of the readiness items and drafts the recommendation memo. It does not place a purchase order. Your name, the time and the reason are kept in the audit log.</div>
      <label className="field">Reason for this allocation<textarea className="textarea" autoFocus value={reason} onChange={(e) => setReason(e.target.value)} style={{ height: 80 }} placeholder="e.g. Cheapest eligible per line; freight-dependent lines to be confirmed before PO" /></label>
      {err && <div style={{ marginTop: 10 }}><Notice tone="critical">{err}</Notice></div>}
      <div className="row" style={{ justifyContent: "flex-end", marginTop: 14 }}><Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button variant="primary" disabled={!reason.trim()} loading={busy} onClick={() => onSave(reason)} icon={<Save size={14} />}>Save recommendation</Button></div>
    </div></>);
}

export default function Award() {
  const { rfxId, overview, refresh } = useRfx();
  const nav = useNavigate();
  const [strategy, setStrategy] = useState("cheapest_per_line");
  const [single, setSingle] = useState("");
  const [basis, setBasis] = useState("freight_aware");
  const [mode, setMode] = useState("strict");
  const [sc, setSc] = useState<any>(null);
  const [ready, setReady] = useState<any>(null);
  const [memo, setMemo] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveErr, setSaveErr] = useState<string | null>(null);
  const [dialog, setDialog] = useState(false);
  const run = async () => {
    setBusy(true); setErr(null);
    try {
      const r = await api(`/rfx/${rfxId}/scenarios`, { body: { name: "Award recommendation", strategy, vendor_id: strategy === "single_vendor" ? Number(single) : undefined, basis, eligibility_mode: mode } });
      setSc(r); setReady(await api(`/scenarios/${r.scenario_id}/readiness`)); setMemo(null);
    } catch (e) { setErr(String(e).replace(/^Error: /, "")); } finally { setBusy(false); }
  };
  useEffect(() => { if (strategy === "cheapest_per_line") run(); }, [rfxId]);

  const blockers = (overview?.findings ?? []).filter((f) => f.severity === "blocker" && OPEN.includes(f.review.state));
  const blockingFor = (vid: number, line: number) => blockers.filter((f) => f.vendor_id === vid && (f.lines.length === 0 || f.lines.includes(line)));
  const affecting = useMemo(() => {
    if (!sc) return [];
    const ids = new Set<string>();
    sc.awards.forEach((a: any) => blockingFor(a.vendor_id, a.line_no).forEach((f) => ids.add(f.id)));
    return blockers.filter((f) => ids.has(f.id));
  }, [sc, blockers]);
  const save = async (reason: string) => {
    setSaving(true); setSaveErr(null);
    try {
      await api(`/scenarios/${sc.scenario_id}/acknowledge`, { body: { actor: "buyer", reason } });
      setMemo((await api(`/scenarios/${sc.scenario_id}/memo`, { body: {} })).memo_markdown); setDialog(false); await refresh();
    } catch (e) { setSaveErr(String(e).replace(/^Error: /, "")); } finally { setSaving(false); }
  };
  const sv = sc?.savings;
  useAssistantScope(sc ? { label: "Award · current allocation", context: `The buyer is on the award page: ${strategy === "single_vendor" ? "single-source" : "cheapest eligible per line"}, ${basis} basis, eligibility ${mode}; ${sc.awards.length} lines awarded, ${sc.uncovered_lines.length} not covered; shares ${Object.entries(sc.per_vendor_share_pct).map(([k, v]) => `${k} ${v}%`).join(", ")}.`,
    prompts: ["Why is each supplier getting the lines it gets?", "What would make this recommendation unsafe to sign?"] } : null);
  const vendors = overview?.vendors ?? [];
  const locked = affecting.length > 0;
  return (
    <div className="stack" style={{ gap: 18 }}>
      <PageHeader title="Award recommendation" sub="Prepare and record a recommendation. No purchase order is created; approval integration is not configured in this demo."
        actions={<>
          {memo && sc && <><a className="btn" href={`/api/scenarios/${sc.scenario_id}/memo.md`}><Download size={15} />Export (.md)</a>
            <a className="btn" href={`/api/scenarios/${sc.scenario_id}/memo.html`} target="_blank" rel="noreferrer"><FileText size={15} />Printable memo</a></>}
          <Button variant="primary" icon={locked ? <Lock size={15} /> : <Save size={15} />} disabled={!sc || locked || !ready?.can_acknowledge || !!memo}
            title={locked ? "Resolve or review the open blockers that affect this allocation first" : undefined} onClick={() => setDialog(true)}>{memo ? "Recommendation saved" : "Save recommendation"}</Button>
        </>} />

      <Card title="Allocation" actions={<Badge tone="outline">Formal scenario</Badge>}>
        <div className="row wrap" style={{ alignItems: "flex-end", gap: 12 }}>
          <Select label="Allocation" value={strategy} onChange={setStrategy} options={[{ value: "cheapest_per_line", label: "Split by SKU: cheapest eligible" }, { value: "single_vendor", label: "Single source" }]} />
          {strategy === "single_vendor" && <Select label="Supplier" value={single} onChange={setSingle} options={[{ value: "", label: "Choose…" }, ...vendors.map((v) => ({ value: String(v.vendor_id), label: `${v.key} · ${v.name}` }))]} />}
          <Select label="Price basis" value={basis} onChange={setBasis} options={[{ value: "freight_aware", label: "Freight-aware (default)" }, { value: "unit", label: "Unit" }, { value: "landed", label: "Landed" }]} />
          <Select label="Eligibility" value={mode} onChange={setMode} options={[{ value: "strict", label: "Quality-eligible only" }, { value: "inclusive", label: "Include Unverified" }, { value: "none", label: "Ignore eligibility" }]} />
          <Button icon={<Play size={14} />} loading={busy} disabled={strategy === "single_vendor" && !single} onClick={run}>Recalculate</Button>
        </div>
      </Card>
      {err && <ErrorState error={err} onRetry={run} />}
      {!sc && !err && <Skeleton rows={8} />}
      {sc && (<>
        {locked && <div className="notice critical"><ShieldAlert size={16} /><div style={{ flex: 1 }}>
          <b>{affecting.length} open blocker{affecting.length === 1 ? "" : "s"} affect this allocation.</b> The recommendation cannot be saved until each is resolved, dismissed with a reason, or marked not applicable.
          <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>{affecting.map((f) => <li key={f.id}><button className="btn link" style={{ padding: 0 }} onClick={() => nav(`/review?finding=${f.id}`)}>{f.vendor_key} · {f.title}</button></li>)}</ul></div></div>}
        <div className="grid g4">
          <MetricCard label="Estimated annual spend" value={inr(sc.total_annual_spend_inr, 0)} hint={`${sc.awards.length} of ${sc.awards.length + sc.uncovered_lines.length} SKUs awarded`} />
          <MetricCard label="vs last year" value={sv?.vs_last_year?.savings_inr != null ? inr(sv.vs_last_year.savings_inr, 0) : "Not comparable"} hint={sv?.vs_last_year ? `${sv.vs_last_year.savings_pct ?? "—"}% on ${sv.vs_last_year.lines} lines with a baseline` : undefined} />
          <MetricCard label="Freight-dependent lines" value={sc.freight_dependent_lines?.length ?? 0} alert={(sc.freight_dependent_lines?.length ?? 0) > 0} hint="priced without freight: spend is a lower bound" />
          <MetricCard label="Not awarded" value={sc.uncovered_lines.length} hint={sc.uncovered_lines.length ? `lines ${sc.uncovered_lines.map((u: any) => u.line_no).join(", ")}: no includable quote` : "every SKU covered"} />
        </div>
        {sv?.vs_last_year?.bound_note && <Notice tone="warning">Assumption: {sv.vs_last_year.bound_note}.</Notice>}
        <div className="split" style={{ gridTemplateColumns: "1fr 340px" }}>
          <Card pad={false} title="Allocation by SKU" actions={<span className="subtle row" style={{ gap: 4 }} title={`Tie-break: ${sc.tie_break}`}><Info size={13} />Tie-break rules</span>}>
            <DataTable dense rows={sc.awards} rowKey={(a: any) => a.line_no} maxHeight={560} onRowClick={(a: any) => nav(`/comparison?line=${a.line_no}`)} columns={[
              { key: "l", label: "SKU", sort: (a: any) => a.line_no, render: (a: any) => <span className="nowrap"><span className="subtle num">{a.line_no}</span> <span className="mono">{a.sku}</span></span> },
              { key: "q", label: "Annual qty", right: true, sort: (a: any) => a.annual_qty, render: (a: any) => <span className="num">{a.annual_qty.toLocaleString("en-IN")}</span> },
              { key: "v", label: "Proposed supplier", sort: (a: any) => a.vendor, render: (a: any) => <div><div>{a.vendor}</div><StatusBadge status={a.eligibility ?? "Passed"} label={`Quality: ${a.eligibility ?? "—"}`} /></div> },
              { key: "b", label: "Quote basis", render: (a: any) => <span className="subtle" style={{ display: "inline-block", maxWidth: 140 }}>{a.price_kind}</span> },
              { key: "p", label: "₹/box", right: true, sort: (a: any) => Number(a.price_on_basis_inr), render: (a: any) => <span className="num">{inr(a.price_on_basis_inr, 2)}</span> },
              { key: "s", label: "Expected spend", right: true, sort: (a: any) => Number(a.annual_spend_inr), render: (a: any) => <span className="num">{inr(a.annual_spend_inr, 0)}</span> },
              { key: "d", label: "Key deviations", render: (a: any) => { const bl = blockingFor(a.vendor_id, a.line_no); return (
                <div className="row wrap" style={{ gap: 4 }}><StatusBadge status={a.status} />
                  {a.freight_status === "FREIGHT_DEPENDENT" && <Badge tone="warning" icon={<AlertTriangle size={11} />} title={`Wins unless freight exceeds ₹${a.break_even_inr_per_box}/box`}>Freight ≤ ₹{a.break_even_inr_per_box}</Badge>}
                  {a.spec_differences && <Badge tone="warning">Spec deviation</Badge>}
                  {bl.length > 0 && <Badge tone="critical" icon={<ShieldAlert size={11} />}>Open blocker</Badge>}</div>); } },
            ]} />
          </Card>
          <div className="stack" style={{ gap: 16 }}>
            <Card title="Supplier share">{Object.entries(sc.per_vendor_spend_inr).map(([k, v]) => (
              <div key={k} style={{ marginBottom: 10 }}><div className="row" style={{ fontSize: 13 }}><span>{k}</span><span className="ml-auto num">{sc.per_vendor_share_pct[k]}%</span></div>
                <div className="bar-track"><div className="bar-fill" style={{ width: `${sc.per_vendor_share_pct[k]}%` }} /></div><div className="subtle num">{inr(v as string, 0)}</div></div>))}</Card>
            <Card title="Excluded suppliers">
              {sc.ineligible_vendors.failed.length + sc.ineligible_vendors.unverified.length === 0 ? <div className="subtle">None excluded.</div> : <div className="stack" style={{ gap: 8 }}>
                {[...sc.ineligible_vendors.failed, ...sc.ineligible_vendors.unverified].map((x: any) => (
                  <div key={x.vendor_id}><div className="row"><b style={{ fontSize: 13 }}>{x.vendor}</b><span className="ml-auto"><StatusBadge status={x.state} /></span></div>
                    <div className="subtle">{x.reasons.join("; ")}</div></div>))}
                <div className="subtle">Unverified is not the same as failed: the supplier may qualify once the evidence is corrected.</div></div>}
            </Card>
            {ready && <Card title="Readiness check">
              {ready.items.length === 0 ? <div className="subtle">No readiness items.</div> : <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }} className="stack">{ready.items.map((i: any, k: number) => (
                <li key={k}><b>{i.kind.replace(/_/g, " ").toLowerCase()}</b>{" "}<span className="muted">
                  {i.kind === "FREIGHT_DEPENDENT" && `${i.lines.length} lines (break-even per line in the table)`}
                  {i.kind === "DECISION_SENSITIVE" && `lines ${i.lines.map((l: any) => l.line_no).join(", ")}`}
                  {i.kind === "AWAITING_RESPONSE" && i.vendors.join(", ")}
                  {i.kind === "FX_EXPOSURE" && i.exposures.map((x: any) => x.statement).join("; ")}
                  {i.kind === "BILLED_WEIGHT_EXPOSURE" && i.statement}
                  {i.kind === "REFERENCE_AMBIGUOUS" && `${i.cells.length} cells`}</span></li>))}</ul>}
              {!ready.can_acknowledge && <div style={{ marginTop: 8 }}><Notice tone="warning">This scenario is stale or exploratory; recalculate before saving.</Notice></div>}
            </Card>}
          </div>
        </div>
        {memo && <Card title="Recommendation memo" actions={<Badge tone="success">Saved</Badge>}><pre className="quote" style={{ whiteSpace: "pre-wrap", fontSize: 12, maxHeight: 420, overflow: "auto" }}>{memo}</pre></Card>}
        {sc.awards.length === 0 && <EmptyState title="No line can be awarded under these settings">Try including Unverified suppliers or another basis.</EmptyState>}
      </>)}
      {dialog && <SaveDialog onClose={() => setDialog(false)} onSave={save} busy={saving} err={saveErr} />}
    </div>
  );
}
