// Comparison: spreadsheet-precise, traceable SKU × supplier grid. Values come only from the backend; a cell without a
// comparable number shows its status in words, never a zero. Vendor-stated and normalised amounts sit side by side.
import { Fragment, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ChevronDown, ChevronRight, Download, FileDown, Info, Table2, Trophy } from "lucide-react";
import { api, inr } from "../api";
import ProvenanceDrawer, { reasonText } from "../components/ProvenanceDrawer";
import { OPEN, useRfx } from "../rfx";
import { useAssistantScope } from "../assistant";
import { Badge, Button, Card, DataTable, EmptyState, ErrorState, MetricCard, Notice, PageHeader, SearchInput, Segmented, Select, Skeleton, StatusBadge } from "../ui";

const OK = ["VERIFIED", "EXTRACTED", "ASSUMED"];
type Basis = "unit" | "landed" | "quoted";
type View = "sku" | "supplier" | "exceptions";
const unitLabel = (u?: string) => !u ? "" : ({ PER_BOX: "/box", PER_KG: "/kg", PER_100: "/100 boxes", PER_1000: "/1000 boxes" } as Record<string, string>)[u] ?? `/${u.replace("PER_", "").toLowerCase()}`;
const isException = (c: any) => c?.status && (!OK.includes(c.status) || (c.flags ?? []).includes("ALTERNATE"));
const short = (n: string) => n.replace(/ (Pvt\.|Ltd\.|Private|Limited).*$/, "").replace(/&/g, "&");

function SpecCell({ r }: { r: any }) {
  const d = r.dims_mm;
  return (
    <div style={{ fontSize: 12, lineHeight: 1.45, maxWidth: 140 }}>
      <div>{r.item_type} · {r.ply}-ply{r.flute ? ` · ${r.flute} flute` : ""}</div>
      {d && <div className="subtle num">{d.L}×{d.W}×{d.H} mm</div>}
      {r.gsm?.filter(Boolean).length > 0 && <div className="subtle num">GSM {r.gsm.filter(Boolean).join("/")}</div>}
      <div className="subtle">{r.printing?.colours ? `${r.printing.colours}-col ${r.printing.type ?? ""}` : "Plain"}{r.food_contact ? " · food contact" : ""}</div>
    </div>
  );
}

function PriceCell({ c, best, basis }: { c: any; best: boolean; basis: Basis }) {
  if (!c) return <span className="subtle">—</span>;
  if (c.state === "AWAITING_RESPONSE") return <StatusBadge status="Awaiting" />;
  if (c.state === "PENDING_PROCESSING" || !c.status) return <StatusBadge status="Processing" />;
  const withheld = ["UNRESOLVED", "NOT_CONVERTIBLE", "MISSING"].includes(c.status);
  const shownValue = c.value !== null && c.value !== undefined && !withheld;
  return (
    <div style={{ minWidth: 140 }}>
      {shownValue ? (
        <div className="row" style={{ gap: 6, alignItems: "baseline" }}>
          <span className="price num">{basis === "quoted" ? `${c.quoted?.currency ?? ""} ${c.value}` : inr(c.value, 2)}</span>
          {basis === "quoted" && <span className="subtle">{unitLabel(c.quoted?.unit_class)}</span>}
          {best && <Badge tone="success" icon={<Trophy size={11} />}>Lowest</Badge>}
        </div>) : <div className="subtle" style={{ fontSize: 12 }}>No comparable value</div>}
      {basis !== "quoted" && !withheld && c.quoted?.value && <div className="cell-sub">As quoted: {c.quoted.currency} {c.quoted.value}{unitLabel(c.quoted.unit_class)}</div>}
      <div className="row wrap" style={{ gap: 4, marginTop: 4 }}>
        <StatusBadge status={c.status} />
        {c.fx && <Badge tone="info" title={`FX ${c.fx.rate} (${c.fx.source}, ${c.fx.as_of})`}>FX</Badge>}
        {(c.flags ?? []).includes("ALTERNATE") && <Badge tone="warning">Alternate spec</Badge>}
        {basis === "unit" && c.freight_basis && c.freight_basis !== "INCLUDED" && <Badge tone="outline" title="Freight is not included in this unit price">{({ STATED: "+ freight (stated)", UNKNOWN: "Freight unknown", ESTIMATED: "+ freight (estimated)" } as Record<string, string>)[c.freight_basis] ?? `Freight ${c.freight_basis.replace(/_/g, " ").toLowerCase()}`}</Badge>}
      </div>
    </div>
  );
}

function Breakdown({ r, vendors, onOpen }: { r: any; vendors: any[]; onOpen: (v: number) => void }) {
  return (
    <div style={{ padding: "12px 16px", background: "var(--surface-2)", position: "sticky", left: 0, width: "calc(100vw - var(--sidebar) - 66px)", overflowX: "auto" }}>
      <div className="section-title">Calculation breakdown · line {r.line_no}</div>
      <table className="t dense" style={{ background: "var(--surface)" }}>
        <thead><tr><th>Supplier</th><th>As quoted</th><th>Currency / FX</th><th>Discount</th><th>Slab used</th><th>Unit conversion</th><th>Freight</th><th>Tax</th><th className="r">Unit ₹/box</th><th className="r">Landed ₹/box</th><th /></tr></thead>
        <tbody>{vendors.map((v) => { const c = r.cells[String(v.vendor_id)]; if (!c?.status) return null; return (
          <tr key={v.vendor_id}>
            <td><b>{short(v.name)}</b><div><StatusBadge status={c.status} /></div></td>
            <td className="num">{c.quoted?.value ? `${c.quoted.currency} ${c.quoted.value}${unitLabel(c.quoted.unit_class)}` : <span className="subtle">Not quoted</span>}</td>
            <td>{c.fx ? <span className="num">USD→INR {c.fx.rate}<div className="subtle">{c.fx.source}, {c.fx.as_of}</div></span> : (c.quoted?.currency ?? "INR")}</td>
            <td className="num">{c.discount_pct ? `${c.discount_pct}%` : <span className="subtle">None stated</span>}</td>
            <td className="num">{c.slab ? `Slab ${c.slab.chosen}${c.slab.min_qty ? ` (${Number(c.slab.min_qty).toLocaleString("en-IN")}${c.slab.max_qty ? `–${Number(c.slab.max_qty).toLocaleString("en-IN")}` : "+"})` : ""}` : <span className="subtle">Single price</span>}
              {c.slab && <div className="subtle">matches annual qty {r.annual_qty.toLocaleString("en-IN")}</div>}</td>
            <td>{c.quoted?.unit_class === "PER_KG" ? <span>₹/kg × box weight<div className="subtle">{c.weight_source ? c.weight_source.replace(/_/g, " ").toLowerCase() : "weight required"}</div></span>
              : c.quoted?.unit_class && c.quoted.unit_class !== "PER_BOX" ? `÷ ${c.quoted.unit_class.replace("PER_", "")}` : <span className="subtle">None (per box)</span>}</td>
            <td>{c.freight_basis?.replace(/_/g, " ").toLowerCase()}{c.freight_inr_per_box && c.freight_basis !== "INCLUDED" && <div className="subtle num">₹{c.freight_inr_per_box}/box</div>}</td>
            <td className="subtle">{c.gst}</td>
            <td className="r num">{c.unit_price ? inr(c.unit_price, 4) : <span className="subtle">—</span>}</td>
            <td className="r num">{c.landed && OK.includes(c.landed_status) ? inr(c.landed, 4) : <span className="subtle">{c.landed_status ? c.landed_status.replace(/_/g, " ").toLowerCase() : "—"}</span>}</td>
            <td><Button size="sm" variant="ghost" onClick={() => onOpen(v.vendor_id)}>Evidence</Button></td>
          </tr>); })}</tbody>
      </table>
      {vendors.some((v) => r.cells[String(v.vendor_id)]?.reasons?.length) && <div className="subtle" style={{ marginTop: 8 }}>
        {vendors.filter((v) => r.cells[String(v.vendor_id)]?.reasons?.length).map((v) => `${short(v.name)}: ${r.cells[String(v.vendor_id)].reasons.map(reasonText).join("; ")}`).join(" · ")}</div>}
    </div>
  );
}

export default function Comparison() {
  const { rfxId, overview, refresh } = useRfx();
  const nav = useNavigate();
  const [sp, setSp] = useSearchParams();
  const [basis, setBasis] = useState<Basis>("unit");
  const [view, setView] = useState<View>(sp.get("exceptions") ? "exceptions" : "sku");
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const [open, setOpen] = useState<{ v: number; l: number } | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(() => new Set(sp.get("line") ? [Number(sp.get("line"))] : []));
  const [q, setQ] = useState("");
  const [vendorF, setVendorF] = useState(sp.get("vendor") ?? "all");
  const [quotedF, setQuotedF] = useState("all");
  const [sort, setSort] = useState("line");
  const [dense, setDense] = useState(false);

  useEffect(() => {
    setErr(null);
    api(`/rfx/${rfxId}/comparison?basis=${basis}`).then(setData).catch((e) => setErr(String(e)));
  }, [rfxId, basis, tick]);
  useEffect(() => {
    const l = sp.get("line");
    if (l && data) setTimeout(() => document.getElementById(`line-${l}`)?.scrollIntoView({ block: "center" }), 50);
  }, [data, sp]);

  const vendors = useMemo(() => (data?.vendors ?? []).filter((v: any) => vendorF === "all" || String(v.vendor_id) === vendorF), [data, vendorF]);
  const rows = useMemo(() => {
    if (!data) return [];
    const cellsOf = (r: any) => vendors.map((v: any) => r.cells[String(v.vendor_id)]);
    let rs = data.rows.filter((r: any) => `${r.sku_code} ${r.description} ${r.line_no}`.toLowerCase().includes(q.toLowerCase()));
    if (quotedF === "unquoted") rs = rs.filter((r: any) => cellsOf(r).some((c: any) => c?.status === "MISSING"));
    if (quotedF === "quoted") rs = rs.filter((r: any) => cellsOf(r).every((c: any) => c?.status && c.status !== "MISSING"));
    if (quotedF === "deviations") rs = rs.filter((r: any) => cellsOf(r).some((c: any) => (c?.flags ?? []).includes("ALTERNATE")));
    if (view === "exceptions") rs = rs.filter((r: any) => cellsOf(r).some(isException));
    const bestVal = (r: any) => { const c = r.best_vendor_id ? r.cells[String(r.best_vendor_id)] : null; return c?.value != null ? Number(c.value) : Infinity; };
    const by: Record<string, (r: any) => number | string> = { line: (r) => r.line_no, sku: (r) => r.sku_code, qty: (r) => -r.annual_qty, price: bestVal,
      variance: (r) => r.best_vs_baseline_pct != null ? Number(r.best_vs_baseline_pct) : Infinity };
    return [...rs].sort((a, b) => { const x = by[sort](a), y = by[sort](b); return x < y ? -1 : x > y ? 1 : 0; });
  }, [data, vendors, q, quotedF, view, sort]);

  const openRow = open && data ? data.rows.find((r: any) => r.line_no === open.l) : null;
  const openVendor = open && data ? data.vendors.find((v: any) => v.vendor_id === open.v) : null;
  const focusLine = sp.get("line") && data ? data.rows.find((r: any) => String(r.line_no) === sp.get("line")) : null;
  useAssistantScope(openRow && openVendor
    ? { label: `Line ${openRow.line_no} · ${short(openVendor.name)}`, context: `The buyer is inspecting line ${openRow.line_no} (${openRow.sku_code}, ${openRow.description}) for ${openVendor.name} on the ${basis} basis.`,
        prompts: [`Explain how ${short(openVendor.name)}'s price for line ${openRow.line_no} was derived.`, `Compare all suppliers on line ${openRow.line_no}.`] }
    : focusLine ? { label: `Line ${focusLine.line_no} · ${focusLine.sku_code}`, context: `The buyer is looking at line ${focusLine.line_no} (${focusLine.sku_code}, ${focusLine.description}) in the comparison.`,
        prompts: [`Compare all suppliers on line ${focusLine.line_no}.`] }
    : { label: `Comparison · ${basis} basis`, context: `The buyer is on the comparison grid, ${basis} basis${vendorF !== "all" ? `, filtered to vendor id ${vendorF}` : ""}${view !== "sku" ? `, view ${view}` : ""}.`, prompts: [] });
  if (err) return <ErrorState error={`Could not load the comparison: ${err}`} onRetry={() => setTick(tick + 1)} />;
  if (!data) return <Skeleton rows={10} />;
  const summ = data.vendor_summary ?? [];
  const responded = data.vendors.filter((v: any) => v.state === "RESPONDED").length;
  const complete = summ.filter((s: any) => s.complete_total_inr);
  const lowest = complete.length ? complete.reduce((a: any, b: any) => (Number(a.complete_total_inr) <= Number(b.complete_total_inr) ? a : b)) : null;
  const totalQuoted = summ.reduce((n: number, s: any) => n + s.quoted, 0), totalCells = summ.reduce((n: number, s: any) => n + s.lines, 0);
  const openEx = (overview?.findings ?? []).filter((f) => OPEN.includes(f.review.state) && f.severity !== "info").length;
  const toggle = (l: number) => { const n = new Set(expanded); n.has(l) ? n.delete(l) : n.add(l); setExpanded(n); };
  const fx = data.rows.flatMap((r: any) => Object.values(r.cells)).find((c: any) => c?.fx)?.fx;
  const colSpan = 5 + vendors.length;

  return (
    <div className="stack" style={{ gap: 18 }}>
      <PageHeader title="Comparison" sub={`${data.rows.length} SKUs × ${data.vendors.length} suppliers · prices normalised to ₹ per box, ex-GST`}
        badge={data.provisional ? <Badge tone="warning">Provisional — responses still processing</Badge> : <Badge tone="success">Final read</Badge>}
        actions={<>
          <a className="btn" href={`/api/rfx/${rfxId}/audit.csv`}><FileDown size={15} />Audit log (CSV)</a>
          <a className="btn primary" href={`/api/rfx/${rfxId}/export.xlsx?basis=${basis === "quoted" ? "unit" : basis}`}><Download size={15} />Export XLSX</a>
        </>} />

      <div className="grid g4">
        <MetricCard label="Suppliers compared" value={`${responded} of ${data.vendors.length}`} hint="responses read" onClick={() => setView("supplier")} />
        <MetricCard label="Quoted SKU coverage" value={`${totalQuoted} of ${totalCells}`} hint="supplier × SKU cells with a quote" onClick={() => { setView("sku"); setQuotedF("unquoted"); }} />
        <MetricCard label="Lowest complete supplier total" value={lowest ? inr(lowest.complete_total_inr, 0) : "Not available"}
          hint={lowest ? `${short(lowest.name)} · all ${lowest.lines} SKUs comparable` : "No supplier has a comparable price on all SKUs"} onClick={() => setView("supplier")} />
        <MetricCard label="Open exceptions" value={openEx} alert={openEx > 0} hint="commercial and quality findings" onClick={() => nav("/review")} />
      </div>

      <div className="notice info"><Info size={16} /><div>
        Basis: <b>{basis === "unit" ? "unit price, ₹/box ex-GST, freight shown separately" : basis === "landed" ? "landed (unit + freight), ₹/box ex-GST" : "as quoted by the supplier (currency and unit as stated)"}</b>.
        {fx && <> USD prices converted at <b>{fx.rate}</b> ({fx.source}, as of {fx.as_of}).</>} Tax: prices compared ex-GST. Slabs: the slab matching the annual quantity is used.
        Unquoted lines show <b>Not quoted</b>, never zero; ₹/kg is converted only with a stated box weight.</div></div>

      <Card pad={false} title={<Segmented value={view} onChange={setView} options={[{ key: "sku", label: "By SKU" }, { key: "supplier", label: "By supplier" }, { key: "exceptions", label: "Exceptions only" }]} />}
        actions={view !== "supplier" && <>
          <Segmented value={basis} onChange={setBasis} options={[{ key: "unit", label: "Unit" }, { key: "landed", label: "Landed" }, { key: "quoted", label: "As quoted" }]} />
          <SearchInput value={q} onChange={setQ} placeholder="Search SKU" width={170} />
          <Select value={vendorF} onChange={(v) => { setVendorF(v); const n = new URLSearchParams(sp); v === "all" ? n.delete("vendor") : n.set("vendor", v); setSp(n); }}
            options={[{ value: "all", label: "All suppliers" }, ...data.vendors.map((v: any) => ({ value: String(v.vendor_id), label: short(v.name) }))]} />
          <Select value={quotedF} onChange={setQuotedF} options={[{ value: "all", label: "All lines" }, { value: "quoted", label: "Quoted by all shown" }, { value: "unquoted", label: "Has unquoted" }, { value: "deviations", label: "Has spec deviations" }]} />
          <Select value={sort} onChange={setSort} options={[{ value: "line", label: "Sort: line" }, { value: "sku", label: "Sort: SKU" }, { value: "qty", label: "Sort: annual qty" }, { value: "price", label: "Sort: lowest price" }, { value: "variance", label: "Sort: vs last year" }]} />
          <Button size="sm" variant="ghost" onClick={() => setDense(!dense)}>{dense ? "Comfortable" : "Compact"}</Button>
        </>}>
        {view === "supplier" ? (
          <DataTable rows={summ} rowKey={(s: any) => s.vendor_id} onRowClick={(s: any) => nav(`/vendors/${s.vendor_id}`)} columns={[
            { key: "n", label: "Supplier", sort: (s: any) => s.name, render: (s: any) => { const v = data.vendors.find((x: any) => x.vendor_id === s.vendor_id);
              return <div><div style={{ fontWeight: 600 }}>{s.name}</div><div className="row" style={{ gap: 4, marginTop: 2 }}>{v?.eligibility ? <><StatusBadge status={v.eligibility.quality} label={`Quality: ${v.eligibility.quality}`} /><StatusBadge status={v.eligibility.commercial} label={`Commercial: ${v.eligibility.commercial}`} /></> : <span className="subtle">Not evaluated</span>}</div></div>; } },
            { key: "q", label: "Quoted", right: true, sort: (s: any) => s.quoted, render: (s: any) => <span className="num">{s.quoted} / {s.lines}</span> },
            { key: "m", label: "Not quoted", right: true, sort: (s: any) => s.not_quoted, render: (s: any) => <span className="num">{s.not_quoted}</span> },
            { key: "c", label: "Comparable", right: true, sort: (s: any) => s.comparable, render: (s: any) => <span className="num">{s.comparable}</span> },
            { key: "e", label: "Exceptions", right: true, sort: (s: any) => s.exceptions, render: (s: any) => s.exceptions ? <Badge tone="warning">{s.exceptions}</Badge> : <span className="subtle">0</span> },
            { key: "s", label: "Spend on comparable lines", right: true, sort: (s: any) => Number(s.comparable_spend_inr ?? 0), render: (s: any) => s.comparable_spend_inr ? <span className="num">{inr(s.comparable_spend_inr, 0)}<div className="subtle">{s.comparable} lines only — not a total</div></span> : <span className="subtle">No comparable lines</span> },
            { key: "t", label: "Complete total", right: true, render: (s: any) => s.complete_total_inr ? <span className="price num">{inr(s.complete_total_inr, 0)}</span> : <span className="subtle">Not comparable on all SKUs</span> },
          ]} />
        ) : rows.length === 0 ? <EmptyState icon={<Table2 size={22} />} title="No lines match these filters" /> : (
          <div className="table-wrap" style={{ maxHeight: "calc(100vh - 360px)" }}>
            <table className={`t ${dense ? "dense" : ""}`}>
              <thead><tr>
                <th className="sticky" style={{ minWidth: 210 }}>SKU</th><th>Specification</th><th className="r">Annual qty</th><th className="r">Last year</th>
                {vendors.map((v: any) => <th key={v.vendor_id} style={{ minWidth: 150 }}>
                  <button className="btn link" style={{ fontWeight: 600, padding: 0 }} onClick={() => nav(`/vendors/${v.vendor_id}`)}>{short(v.name)}</button>
                  {v.eligibility && <div className="row" style={{ gap: 4, marginTop: 2, fontWeight: 400 }}><StatusBadge status={v.eligibility.quality} label={`Q: ${v.eligibility.quality}`} /></div>}</th>)}
                <th />
              </tr></thead>
              <tbody>{rows.map((r: any) => (
                <Fragment key={r.line_no}>
                  <tr id={`line-${r.line_no}`} style={sp.get("line") === String(r.line_no) ? { outline: "2px solid var(--primary)", outlineOffset: -2 } : undefined}>
                    <td className="sticky"><div className="row" style={{ gap: 6, alignItems: "flex-start" }}>
                      <button className="icon-btn" style={{ width: 24, height: 24 }} aria-label={expanded.has(r.line_no) ? "Collapse breakdown" : "Expand breakdown"} onClick={() => toggle(r.line_no)}>
                        {expanded.has(r.line_no) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</button>
                      <div><div className="row" style={{ gap: 6 }}><span className="subtle num">{r.line_no}</span><span className="mono" style={{ fontWeight: 600 }}>{r.sku_code}</span></div>
                        <div style={{ fontSize: 12, maxWidth: 170 }} className="muted">{r.description}</div></div></div></td>
                    <td><SpecCell r={r} /></td>
                    <td className="r num">{r.annual_qty.toLocaleString("en-IN")}<div className="subtle">boxes</div></td>
                    <td className="r num">{r.baseline ? <>{inr(r.baseline.unit_price_inr_ex_gst, 2)}{r.best_vs_baseline_pct != null && basis !== "quoted" &&
                      <div style={{ fontSize: 11, color: Number(r.best_vs_baseline_pct) <= 0 ? "var(--success)" : "var(--critical)" }}>best {Number(r.best_vs_baseline_pct) > 0 ? "+" : ""}{r.best_vs_baseline_pct}%</div>}</>
                      : <span className="subtle">No baseline</span>}</td>
                    {vendors.map((v: any) => { const c = r.cells[String(v.vendor_id)]; const best = r.best_vendor_id === v.vendor_id && basis !== "quoted"; return (
                      <td key={v.vendor_id} className={best ? "bestcell" : ""} style={{ cursor: c?.status ? "pointer" : undefined, opacity: view === "exceptions" && !isException(c) ? 0.55 : 1 }}
                        onClick={() => c?.status && setOpen({ v: v.vendor_id, l: r.line_no })} title="Open source evidence and calculation">
                        <PriceCell c={c} best={best} basis={basis} /></td>); })}
                    <td />
                  </tr>
                  {expanded.has(r.line_no) && <tr><td colSpan={colSpan} style={{ padding: 0 }}><Breakdown r={r} vendors={vendors} onOpen={(v) => setOpen({ v, l: r.line_no })} /></td></tr>}
                </Fragment>))}</tbody>
            </table>
          </div>)}
      </Card>
      {basis === "landed" && <Notice tone="warning">Landed values are shown only where freight is included or estimated. Where freight is unknown the cell shows its status instead of a number.</Notice>}
      {open && <ProvenanceDrawer rfxId={rfxId} vendorId={open.v} lineNo={open.l} onClose={() => setOpen(null)} onChanged={() => { setTick(tick + 1); refresh(); }} />}
    </div>
  );
}
