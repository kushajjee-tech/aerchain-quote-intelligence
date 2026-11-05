// Analyst: deterministic analytics over the normalised comparison, findings and the award engine. Charts show only
// values the backend returned; where inputs are missing the panel says exactly which, instead of drawing a zero.
import { ReactNode, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BarChart3, FlaskConical, Info, Play } from "lucide-react";
import { api, inr } from "../api";
import { OPEN, useRfx } from "../rfx";
import { Badge, Button, Card, DataTable, EmptyState, ErrorState, Notice, PageHeader, Select, Skeleton } from "../ui";

const PALETTE = ["#3157c8", "#1f7a4d", "#9a5b00", "#5b3fa8", "#b42318"];

function Method({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <span style={{ position: "relative" }}>
      <button className="icon-btn" style={{ width: 26, height: 26 }} aria-label="Methodology" onClick={() => setOpen(!open)}><Info size={14} /></button>
      {open && <div className="pop" style={{ right: 0, width: 300, padding: 12, fontSize: 12, lineHeight: 1.5 }} onMouseLeave={() => setOpen(false)}>{children}</div>}
    </span>
  );
}

function Insufficient({ missing }: { missing: string[] }) {
  return <EmptyState title="Insufficient comparable data"><div>Missing inputs:</div><ul style={{ textAlign: "left", display: "inline-block", margin: "6px 0 0" }}>{missing.map((m) => <li key={m}>{m}</li>)}</ul></EmptyState>;
}

function HBars({ items, format, onClick, active }: { items: { label: string; value: number; sub?: string; color?: string }[]; format: (n: number) => string; onClick?: (l: string) => void; active?: string | null }) {
  const max = Math.max(...items.map((i) => i.value), 0);
  return (
    <div className="stack" style={{ gap: 10 }}>
      {items.map((i, k) => (
        <button key={i.label} onClick={() => onClick?.(i.label)} style={{ background: "none", border: 0, padding: 0, textAlign: "left", cursor: onClick ? "pointer" : "default", opacity: active && active !== i.label ? 0.45 : 1 }}>
          <div className="row" style={{ fontSize: 13, marginBottom: 4 }}><span style={{ fontWeight: 500 }}>{i.label}</span>{i.sub && <span className="subtle">{i.sub}</span>}<span className="ml-auto num">{format(i.value)}</span></div>
          <div className="bar-track" style={{ height: 10 }}><div className="bar-fill" style={{ width: `${max ? (i.value / max) * 100 : 0}%`, background: i.color ?? PALETTE[k % 5] }} /></div>
        </button>))}
    </div>
  );
}

export default function Analyst() {
  const { rfxId, overview } = useRfx();
  const nav = useNavigate();
  const [cmp, setCmp] = useState<any>(null);
  const [base, setBase] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [family, setFamily] = useState<string | null>(null);
  const [vendorF, setVendorF] = useState("all");
  // what-if controls
  const [strategy, setStrategy] = useState("cheapest_per_line");
  const [single, setSingle] = useState("");
  const [mode, setMode] = useState("strict");
  const [basis, setBasis] = useState("freight_aware");
  const [excluded, setExcluded] = useState<number[]>([]);
  const [what, setWhat] = useState<any>(null);
  const [wErr, setWErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setErr(null); setCmp(null); setBase(null);
    api(`/rfx/${rfxId}/comparison?basis=unit`).then(setCmp).catch((e) => setErr(String(e)));
    api(`/rfx/${rfxId}/scenarios`, { body: { name: "Analyst baseline estimate", basis: "freight_aware", eligibility_mode: "strict" } }).then(setBase).catch(() => setBase({ error: true }));
  }, [rfxId]);

  const families = useMemo(() => {
    const m = new Map<string, { qty: number; skus: number }>();
    (cmp?.rows ?? []).forEach((r: any) => { const f = m.get(r.item_type) ?? { qty: 0, skus: 0 }; f.qty += r.annual_qty; f.skus += 1; m.set(r.item_type, f); });
    return [...m.entries()].map(([label, v]) => ({ label, value: v.qty, sub: `${v.skus} SKUs` })).sort((a, b) => b.value - a.value);
  }, [cmp]);
  const variance = useMemo(() => (cmp?.rows ?? []).filter((r: any) => !family || r.item_type === family), [cmp, family]);
  const runWhat = async () => {
    setBusy(true); setWErr(null);
    try {
      setWhat(await api(`/rfx/${rfxId}/scenarios`, { body: { name: "What-if", strategy, vendor_id: strategy === "single_vendor" ? Number(single) : undefined,
        basis, eligibility_mode: mode, exclude_vendor_ids: excluded, context: "exploratory" } }));
    } catch (e) { setWErr(String(e).replace(/^Error: /, "")); } finally { setBusy(false); }
  };
  if (err) return <ErrorState error={err} />;
  if (!cmp) return <Skeleton rows={10} />;
  const summ = (cmp.vendor_summary ?? []).filter((s: any) => vendorF === "all" || String(s.vendor_id) === vendorF);
  const findings = (overview?.findings ?? []).filter((f) => OPEN.includes(f.review.state) && (vendorF === "all" || String(f.vendor_id) === vendorF));
  const cats = [...new Set(findings.map((f) => f.category))];
  const noBaseline = variance.filter((r: any) => !r.baseline).map((r: any) => r.line_no);
  const noBest = variance.filter((r: any) => r.baseline && r.best_vs_baseline_pct == null).map((r: any) => r.line_no);
  const withVar = variance.filter((r: any) => r.best_vs_baseline_pct != null);
  const spend = base && !base.error ? Object.entries(base.per_vendor_spend_inr as Record<string, string>).map(([k, v], i) => ({ label: k, value: Number(v), sub: `${base.per_vendor_share_pct[k]}%`, color: PALETTE[i % 5] })) : [];

  return (
    <div className="stack" style={{ gap: 18 }}>
      <PageHeader title="Analyst" sub="Traceable analytics for this RFx. Ask free-form questions in the Co-pilot."
        actions={<><Select value={vendorF} onChange={setVendorF} options={[{ value: "all", label: "All suppliers" }, ...cmp.vendors.map((v: any) => ({ value: String(v.vendor_id), label: v.name }))]} />
          <Select value={family ?? "all"} onChange={(v) => setFamily(v === "all" ? null : v)} options={[{ value: "all", label: "All SKU families" }, ...families.map((f) => ({ value: f.label, label: f.label }))]} />
          <Button icon={<BarChart3 size={15} />} onClick={() => nav("/copilot")}>Ask the Co-pilot</Button></>} />

      <div className="grid g2">
        <Card title="Spend estimate by supplier" actions={<><Badge tone="violet">Scenario</Badge><Method>Cheapest eligible quote per line (freight-aware, quality-eligible suppliers only, Needs-review values excluded), × annual quantity. Lines priced without freight are lower bounds. This is an estimate, not committed spend.</Method></>}>
          {!base ? <Skeleton /> : base.error ? <Insufficient missing={["A final, normalised comparison (award engine returned an error)"]} /> : spend.length === 0 ? <Insufficient missing={["At least one eligible supplier with comparable prices"]} /> : <>
            <HBars items={spend} format={(n) => inr(n, 0)} />
            <div className="subtle" style={{ marginTop: 12 }}>Total {inr(base.total_annual_spend_inr, 0)} on {base.awards.length} of {cmp.rows.length} lines.
              {base.uncovered_lines.length > 0 && ` Not covered: lines ${base.uncovered_lines.map((u: any) => u.line_no).join(", ")}.`}
              {base.freight_dependent_lines?.length > 0 && ` ${base.freight_dependent_lines.length} lines depend on unknown freight.`}</div></>}
        </Card>
        <Card title="Annual demand by SKU family" actions={<Method>Sum of RFx annual quantity per item type. Click a family to filter the variance table below.</Method>}>
          <HBars items={families} format={(n) => `${n.toLocaleString("en-IN")} pcs`} onClick={(l) => setFamily(family === l ? null : l)} active={family} />
        </Card>
        <Card title="Quote coverage by supplier" actions={<Method>Per supplier: SKUs quoted, of which comparable (a verified/extracted/assumed price on the requested spec). Not-quoted lines are counted, never priced as zero.</Method>}>
          <div className="stack" style={{ gap: 12 }}>{summ.map((s: any) => (
            <div key={s.vendor_id}><div className="row" style={{ fontSize: 13, marginBottom: 4 }}><b>{s.name}</b><span className="ml-auto subtle num">{s.comparable} comparable · {s.exceptions} exceptions · {s.not_quoted} not quoted</span></div>
              <div className="bar-track" style={{ height: 10, display: "flex" }}>
                <div style={{ width: `${(s.comparable / s.lines) * 100}%`, background: "var(--success)" }} title={`${s.comparable} comparable`} />
                <div style={{ width: `${(s.exceptions / s.lines) * 100}%`, background: "var(--warning)" }} title={`${s.exceptions} quoted but not comparable`} /></div></div>))}
            <div className="row subtle" style={{ gap: 14 }}><span className="row" style={{ gap: 4 }}><span style={{ width: 10, height: 10, background: "var(--success)", borderRadius: 2 }} />Comparable</span>
              <span className="row" style={{ gap: 4 }}><span style={{ width: 10, height: 10, background: "var(--warning)", borderRadius: 2 }} />Quoted, not comparable</span>
              <span className="row" style={{ gap: 4 }}><span style={{ width: 10, height: 10, background: "var(--surface-3)", borderRadius: 2, border: "1px solid var(--border)" }} />Not quoted</span></div>
          </div>
        </Card>
        <Card title="Open exceptions by category" actions={<Method>Open findings (not dismissed or marked not applicable), by review category and severity. Click to open Review filtered.</Method>}>
          {cats.length === 0 ? <EmptyState title="No open exceptions" /> : <div className="stack" style={{ gap: 10 }}>{cats.map((c) => {
            const fs = findings.filter((f) => f.category === c); const b = fs.filter((f) => f.severity === "blocker").length, w = fs.filter((f) => f.severity === "warning").length, i = fs.length - b - w;
            return (<button key={c} onClick={() => nav(`/review?category=${encodeURIComponent(c)}`)} style={{ background: "none", border: 0, padding: 0, textAlign: "left", cursor: "pointer" }}>
              <div className="row" style={{ fontSize: 13, marginBottom: 4 }}><span style={{ fontWeight: 500 }}>{c}</span><span className="ml-auto subtle">{b} blocker · {w} warning · {i} info</span></div>
              <div className="bar-track" style={{ height: 10, display: "flex" }}>{[[b, "var(--critical)"], [w, "var(--warning)"], [i, "var(--info)"]].map(([n, col], k) =>
                <div key={k} style={{ width: `${(Number(n) / Math.max(...cats.map((cc) => findings.filter((f) => f.category === cc).length))) * 100}%`, background: String(col) }} />)}</div></button>); })}</div>}
        </Card>
      </div>

      <Card pad={false} title={<span>Price variance vs last-year baseline{family && <> · <Badge tone="info">{family}</Badge></>}</span>}
        actions={<Method>Best comparable unit price this year vs last year’s awarded price, per line. Lines with no baseline or no comparable quote are listed, not plotted.</Method>}>
        {withVar.length === 0 ? <Insufficient missing={["Last-year awarded prices for these lines", "A comparable quote on the same lines"]} /> :
          <DataTable dense rows={withVar} rowKey={(r: any) => r.line_no} onRowClick={(r: any) => nav(`/comparison?line=${r.line_no}`)} initialSort={{ key: "v", dir: 1 }} maxHeight={380} columns={[
            { key: "l", label: "Line", sort: (r: any) => r.line_no, render: (r: any) => <span className="num">{r.line_no}</span> },
            { key: "s", label: "SKU", render: (r: any) => <span><span className="mono">{r.sku_code}</span> <span className="subtle">{r.item_type}</span></span> },
            { key: "b", label: "Last year ₹/box", right: true, render: (r: any) => <span className="num">{inr(r.baseline.unit_price_inr_ex_gst, 2)}</span> },
            { key: "n", label: "Best now ₹/box", right: true, render: (r: any) => <span className="num">{inr(r.cells[String(r.best_vendor_id)].value, 2)}</span> },
            { key: "w", label: "Supplier", render: (r: any) => <span className="subtle">{cmp.vendors.find((v: any) => v.vendor_id === r.best_vendor_id)?.name}</span> },
            { key: "v", label: "Variance", right: true, sort: (r: any) => Number(r.best_vs_baseline_pct), render: (r: any) => { const v = Number(r.best_vs_baseline_pct); return (
              <div className="row" style={{ justifyContent: "flex-end", gap: 8 }}><div style={{ width: 80, height: 6, background: "var(--surface-3)", borderRadius: 3, position: "relative" }}>
                <div style={{ position: "absolute", left: v < 0 ? `${50 + Math.max(v, -50)}%` : "50%", width: `${Math.min(Math.abs(v), 50)}%`, top: 0, bottom: 0, background: v <= 0 ? "var(--success)" : "var(--critical)", borderRadius: 3 }} /></div>
                <span className="num" style={{ color: v <= 0 ? "var(--success)" : "var(--critical)", width: 54 }}>{v > 0 ? "+" : ""}{r.best_vs_baseline_pct}%</span></div>); } },
          ]} />}
        {(noBaseline.length > 0 || noBest.length > 0) && <div style={{ padding: 12 }}><Notice tone="warning">
          {noBaseline.length > 0 && <>No last-year baseline: lines {noBaseline.join(", ")}. </>}
          {noBest.length > 0 && <>No comparable quote this year: lines {noBest.join(", ")}.</>}</Notice></div>}
      </Card>

      <Card title={<span className="row" style={{ gap: 8 }}><FlaskConical size={16} />What-if allocation</span>} actions={<Badge tone="violet">Scenario — not committed savings</Badge>}>
        <div className="row wrap" style={{ alignItems: "flex-end", gap: 12 }}>
          <Select label="Allocation" value={strategy} onChange={setStrategy} options={[{ value: "cheapest_per_line", label: "Split: cheapest per line" }, { value: "single_vendor", label: "Single source" }]} />
          {strategy === "single_vendor" && <Select label="Supplier" value={single} onChange={setSingle} options={[{ value: "", label: "Choose…" }, ...cmp.vendors.map((v: any) => ({ value: String(v.vendor_id), label: v.name }))]} />}
          <Select label="Price basis" value={basis} onChange={setBasis} options={[{ value: "freight_aware", label: "Freight-aware" }, { value: "unit", label: "Unit" }, { value: "landed", label: "Landed" }]} />
          <Select label="Eligibility" value={mode} onChange={setMode} options={[{ value: "strict", label: "Quality-eligible only" }, { value: "inclusive", label: "Include Unverified" }, { value: "none", label: "Ignore eligibility" }]} />
          <div className="field">Exclude suppliers<div className="row wrap" style={{ gap: 6 }}>{cmp.vendors.map((v: any) => (
            <label key={v.vendor_id} className="chip" style={{ cursor: "pointer" }}><input type="checkbox" checked={excluded.includes(v.vendor_id)}
              onChange={(e) => setExcluded(e.target.checked ? [...excluded, v.vendor_id] : excluded.filter((x) => x !== v.vendor_id))} /> {v.name.split(" ")[0]}</label>))}</div></div>
          <Button variant="primary" icon={<Play size={14} />} loading={busy} disabled={strategy === "single_vendor" && !single} onClick={runWhat}>Run scenario</Button>
        </div>
        {wErr && <div style={{ marginTop: 12 }}><ErrorState error={wErr} /></div>}
        {what && <div className="grid g3" style={{ marginTop: 16 }}>
          <div className="card" style={{ padding: 14 }}><div className="subtle">Scenario annual spend</div><div className="price" style={{ fontSize: 20 }}>{inr(what.total_annual_spend_inr, 0)}</div>
            <div className="subtle">{what.awards.length} lines awarded · {what.uncovered_lines.length} not covered</div></div>
          <div className="card" style={{ padding: 14 }}><div className="subtle">vs last year (scenario)</div>
            {what.savings?.vs_last_year?.savings_inr != null ? <><div className="price" style={{ fontSize: 20 }}>{inr(what.savings.vs_last_year.savings_inr, 0)} {what.savings.vs_last_year.savings_pct && <span className="subtle">({what.savings.vs_last_year.savings_pct}%)</span>}</div>
              <div className="subtle">{what.savings.vs_last_year.statement}</div></> : <div className="muted">Not comparable</div>}</div>
          <div className="card" style={{ padding: 14 }}><div className="subtle">Allocation</div>{Object.entries(what.per_vendor_share_pct).map(([k, v]) => <div key={k} className="row" style={{ fontSize: 13 }}><span>{k}</span><span className="ml-auto num">{String(v)}%</span></div>)}</div>
          {what.savings?.vs_last_year?.bound_note && <div style={{ gridColumn: "1 / -1" }}><Notice tone="warning">{what.savings.vs_last_year.bound_note}.</Notice></div>}
        </div>}
      </Card>
    </div>
  );
}
