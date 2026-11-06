import { ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { Award, BarChart3, Bell, Boxes, Check, ChevronDown, ClipboardCheck, FileText, Home, Inbox, MessageSquareText,
  Package, Search, Settings, ShieldAlert, Table2, User } from "lucide-react";
import { api } from "./api";
import { OPEN, useRfx } from "./rfx";
import { Badge } from "./ui";
import { AssistantPanel, useAssistant } from "./assistant";
import { useTour } from "./tour";

const NAV = [
  { to: "/", label: "Home", icon: Home, end: true },
  { to: "/copilot", label: "Co-pilot", icon: MessageSquareText },
  { to: "/vendors", label: "Vendors & Inbox", icon: Inbox },
  { to: "/review", label: "Review", icon: ClipboardCheck, badge: true },
  { to: "/comparison", label: "Comparison", icon: Table2 },
  { to: "/analyst", label: "Analyst", icon: BarChart3 },
  { to: "/award", label: "Award", icon: Award },
];

function usePopover() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    const k = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", h); window.addEventListener("keydown", k);
    return () => { document.removeEventListener("mousedown", h); window.removeEventListener("keydown", k); };
  }, [open]);
  return { open, setOpen, ref };
}

function RfxSelector() {
  const { list, rfxId, setRfxId } = useRfx();
  const { open, setOpen, ref } = usePopover();
  const [q, setQ] = useState("");
  const cur = list.find((r) => r.rfx_id === rfxId);
  const shown = list.filter((r) => `${r.title} ${r.meta.code ?? ""} ${r.meta.buyer ?? ""} ${r.rfx_id}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button className="btn" style={{ minWidth: 300, justifyContent: "space-between", height: 40 }} onClick={() => setOpen(!open)} aria-haspopup="listbox" aria-expanded={open}>
        <span style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", lineHeight: 1.2, textAlign: "left" }}>
          <span style={{ fontWeight: 600, fontSize: 13 }}>{cur ? cur.meta.code ?? `RFx #${cur.rfx_id}` : "Select an RFx"}</span>
          <span className="subtle" style={{ fontSize: 11 }}>{cur ? `${cur.meta.buyer ?? ""} · ${cur.meta.category ?? cur.title}` : "No RFx loaded"}</span>
        </span>
        <ChevronDown size={16} />
      </button>
      {open && (
        <div className="pop" style={{ width: 380, left: 0 }} role="listbox">
          <div style={{ padding: 8 }}><div className="search"><Search size={15} /><input autoFocus className="input" placeholder="Search RFx by code, buyer or title"
            value={q} onChange={(e) => setQ(e.target.value)} /></div></div>
          {shown.length === 0 && <div className="subtle" style={{ padding: 12 }}>No RFx matches “{q}”.</div>}
          {shown.map((r) => (
            <button key={r.rfx_id} className={`item ${r.rfx_id === rfxId ? "on" : ""}`} role="option" aria-selected={r.rfx_id === rfxId}
              onClick={() => { setRfxId(r.rfx_id); setOpen(false); }}>
              <div style={{ flex: 1, textAlign: "left" }}>
                <div style={{ fontWeight: 600 }}>{r.meta.code ?? `RFx #${r.rfx_id}`} <span className="subtle">#{r.rfx_id}</span></div>
                <div className="subtle">{r.title}</div>
                <div className="row" style={{ gap: 6, marginTop: 4 }}>
                  <Badge tone="outline">{r.status}</Badge>{r.demo && <Badge tone="violet">Demo / evaluation</Badge>}{r.kind !== "primary" && <Badge tone="neutral">{r.kind}</Badge>}
                </div>
              </div>
              {r.rfx_id === rfxId && <Check size={16} />}
            </button>))}
        </div>)}
    </div>
  );
}

type Hit = { group: string; label: string; sub: string; to: string; icon: ReactNode };
function GlobalSearch() {
  const { overview, rfxId } = useRfx();
  const nav = useNavigate();
  const { open, setOpen, ref } = usePopover();
  const [q, setQ] = useState("");
  const [cmp, setCmp] = useState<any>(null);
  const [docs, setDocs] = useState<any[]>([]);
  useEffect(() => {
    if (!open || !rfxId || cmp?.rfx_id === rfxId) return;
    api(`/rfx/${rfxId}/comparison?basis=unit`).then((d) => {
      setCmp(d);
      setDocs(d.vendors.flatMap((v: any) => (v.documents ?? []).map((x: any) => ({ ...x, vendor_id: v.vendor_id, vendor: v.name }))));
    }).catch(() => setCmp(null));
  }, [open, rfxId, cmp]);
  const hits = useMemo<Hit[]>(() => {
    const s = q.trim().toLowerCase();
    if (!s) return [];
    const m = (t: string) => t.toLowerCase().includes(s);
    const out: Hit[] = [];
    overview?.vendors.filter((v) => m(`${v.name} ${v.key} ${v.email ?? ""}`)).slice(0, 5)
      .forEach((v) => out.push({ group: "Vendors", label: v.name, sub: `${v.key} · ${v.state}`, to: `/vendors/${v.vendor_id}`, icon: <Boxes size={15} /> }));
    cmp?.rows.filter((r: any) => m(`${r.sku_code} ${r.description} line ${r.line_no}`)).slice(0, 6)
      .forEach((r: any) => out.push({ group: "SKUs", label: `${r.sku_code} · ${r.description}`, sub: `Line ${r.line_no} · ${r.annual_qty.toLocaleString("en-IN")}/yr`,
        to: `/comparison?line=${r.line_no}`, icon: <Package size={15} /> }));
    docs.filter((d) => m(`${d.filename} ${d.doc_type} ${d.vendor}`)).slice(0, 5)
      .forEach((d) => out.push({ group: "Documents", label: d.filename, sub: `${d.vendor} · ${d.doc_type.replace(/_/g, " ").toLowerCase()}`,
        to: `/vendors/${d.vendor_id}?tab=documents`, icon: <FileText size={15} /> }));
    overview?.findings.filter((f) => m(`${f.title} ${f.vendor ?? ""} ${f.category} ${f.concern}`)).slice(0, 6)
      .forEach((f) => out.push({ group: "Findings", label: f.title, sub: `${f.vendor ?? "All vendors"} · ${f.category}`, to: `/review?finding=${f.id}`, icon: <ShieldAlert size={15} /> }));
    return out;
  }, [q, overview, cmp, docs]);
  const go = (h: Hit) => { nav(h.to); setOpen(false); setQ(""); };
  let last = "";
  return (
    <div ref={ref} style={{ position: "relative", flex: 1, maxWidth: 520 }}>
      <div className="search"><Search size={15} />
        <input className="input" placeholder="Search vendors, SKUs, documents, findings" value={q} aria-label="Global search"
          onFocus={() => setOpen(true)} onChange={(e) => { setQ(e.target.value); setOpen(true); }}
          onKeyDown={(e) => e.key === "Enter" && hits[0] && go(hits[0])} /></div>
      {open && q.trim() && (
        <div className="pop" style={{ width: "100%", maxHeight: 440, overflow: "auto" }}>
          {hits.length === 0 && <div className="subtle" style={{ padding: 12 }}>{cmp ? `No results for “${q}”.` : "Loading search index…"}</div>}
          {hits.map((h, i) => {
            const head = h.group !== last; last = h.group;
            return (<div key={i}>{head && <div className="group">{h.group}</div>}
              <button className="item" onClick={() => go(h)}>{h.icon}<div style={{ flex: 1, textAlign: "left", minWidth: 0 }}>
                <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{h.label}</div><div className="subtle">{h.sub}</div></div></button></div>);
          })}
        </div>)}
    </div>
  );
}

function Notifications() {
  const { overview } = useRfx();
  const nav = useNavigate();
  const { open, setOpen, ref } = usePopover();
  const blockers = (overview?.findings ?? []).filter((f) => f.severity === "blocker" && OPEN.includes(f.review.state));
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button className="icon-btn" aria-label={`Notifications: ${blockers.length} open blockers`} onClick={() => setOpen(!open)} style={{ position: "relative" }}>
        <Bell size={18} />{blockers.length > 0 && <span className="dot" />}
      </button>
      {open && (
        <div className="pop" style={{ width: 380, right: 0, maxHeight: 460, overflow: "auto" }}>
          <div className="group">Open blockers ({blockers.length})</div>
          {blockers.length === 0 && <div className="subtle" style={{ padding: 12 }}>No open blockers for this RFx.</div>}
          {blockers.slice(0, 8).map((f) => (
            <button key={f.id} className="item" onClick={() => { nav(`/review?finding=${f.id}`); setOpen(false); }}>
              <ShieldAlert size={15} color="var(--critical)" /><div style={{ flex: 1, textAlign: "left" }}><div>{f.title}</div>
                <div className="subtle">{f.vendor ?? "All vendors"} · {f.category}</div></div></button>))}
          {blockers.length > 0 && <button className="item" style={{ justifyContent: "center", color: "var(--primary)", fontWeight: 600 }}
            onClick={() => { nav("/review?severity=blocker"); setOpen(false); }}>View all in Review</button>}
        </div>)}
    </div>
  );
}

export default function Shell({ children }: { children: ReactNode }) {
  const { overview } = useRfx();
  const blockers = (overview?.findings ?? []).filter((f) => f.severity === "blocker" && OPEN.includes(f.review.state)).length;
  const buyer = overview?.rfx.meta.buyer_name;
  const { open: assistantOpen } = useAssistant();
  const { start: startTour } = useTour();
  return (
    <div className={`shell ${assistantOpen ? "assistant-open" : ""}`}>
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><Package size={16} /></span>Quote Intelligence</div>
        <nav className="nav" aria-label="Primary">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}><n.icon size={17} />{n.label}
              {n.badge && blockers > 0 && <span className="count" aria-label={`${blockers} open blockers`}>{blockers}</span>}</NavLink>))}
        </nav>
        <div className="spacer" />
        <div className="sep" />
        <nav className="nav"><NavLink to="/settings"><Settings size={17} />Settings</NavLink></nav>
        <div className="foot subtle">Demo / evaluation build · data from the seeded RFx fixture</div>
      </aside>
      <div className="main">
        <header className="topbar">
          <RfxSelector />
          {overview?.rfx.demo && <Badge tone="violet" title="This RFx runs on the evaluation fixture (synthetic vendors and documents).">Demo / evaluation RFx</Badge>}
          <div className="grow" style={{ display: "flex", justifyContent: "center" }}><GlobalSearch /></div>
          <button className="btn sm" onClick={startTour} title="A short guided walkthrough of the product">Take the tour</button>
          <Notifications />
          <div className="row" style={{ gap: 8 }} title="Signed-in buyer (from the RFx fixture)">
            <span className="brand-mark" style={{ background: "var(--surface-3)", color: "var(--text-2)", borderRadius: "50%" }}><User size={15} /></span>
            <div style={{ lineHeight: 1.2 }}><div style={{ fontSize: 13, fontWeight: 600 }}>{buyer ?? "Buyer"}</div><div className="subtle" style={{ fontSize: 11 }}>Buyer</div></div>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
      <AssistantPanel />
    </div>
  );
}
