// Home: the RFx command centre. Every figure comes from GET /rfx/{id}/overview (no hard-coded counts).
import { Activity, AlertTriangle, ArrowRight, Boxes, Check, ClipboardCheck, FileText, Package, ShieldAlert, Table2, Users } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Finding, OPEN, useRfx } from "../rfx";
import { Badge, Button, Card, DataTable, EmptyState, MetricCard, PageHeader, StatusBadge } from "../ui";

export const fmtTime = (s: string | null | undefined) => s ? new Date(s).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "—";
const compact = (n: number) => n >= 1e6 ? `~${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `~${Math.round(n / 1e3)}k` : String(n);

function sourceName(f: Finding) {
  return f.source?.filename ?? f.source?.document ?? (f.source?.documents?.[0]) ?? null;
}

function FindingRow({ f, onOpen }: { f: Finding; onOpen: () => void }) {
  const src = sourceName(f);
  return (
    <div className="list-row" style={{ alignItems: "flex-start" }}>
      <span className={`sev ${f.severity}`} aria-hidden />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
          <StatusBadge status={f.severity} />
          <b>{f.vendor_key ? `${f.vendor_key} · ${f.vendor}` : "All vendors"}</b>
          <span className="subtle">{f.category}</span>
          {f.review.state !== "open" && <StatusBadge status={f.review.state} />}
        </div>
        <div style={{ marginTop: 4 }}>{f.title}</div>
        {!f.title.toLowerCase().includes(f.concern.toLowerCase().slice(0, 40)) && <div className="muted" style={{ fontSize: 13 }}>{f.concern}</div>}
        {src && <div className="subtle row" style={{ gap: 4, marginTop: 2 }}><FileText size={12} />{src}</div>}
      </div>
      <Button size="sm" onClick={onOpen} icon={<ArrowRight size={14} />}>{ctaLabel(f)}</Button>
    </div>
  );
}

function ctaLabel(f: Finding) {
  if (f.category === "Document validity" || f.category === "Quality & compliance") return "Review documents";
  if (f.kind === "cells") return "Inspect quotation";
  if (f.category === "Commercial terms") return "Review terms";
  return "Open";
}

export default function Home() {
  const { overview } = useRfx();
  const nav = useNavigate();
  if (!overview) return null;
  const { rfx, metrics, findings, vendors, stages, activity } = overview;
  const open = findings.filter((f) => OPEN.includes(f.review.state));
  const blockers = open.filter((f) => f.severity === "blocker");
  const others = open.filter((f) => f.severity !== "blocker");
  const status = blockers.length ? "Evaluation in progress · blockers open" : stages.find((s) => s.state === "current")?.label ?? "Evaluation in progress";
  return (
    <div className="stack" style={{ gap: 20 }}>
      <PageHeader
        title={rfx.meta.code === "PUNE-PKG-2026" ? "Pune Packaging RFx" : rfx.title}
        sub={`${rfx.meta.buyer ?? ""} · ${rfx.meta.code ?? `RFx #${rfx.rfx_id}`} · ${rfx.meta.category ?? ""}`}
        badge={<Badge tone={blockers.length ? "warning" : "info"} icon={<Activity size={12} />}>{status}</Badge>}
        actions={<>
          <Button onClick={() => nav("/review?severity=blocker")} icon={<ShieldAlert size={15} />}>Review blockers</Button>
          <Button variant="primary" onClick={() => nav("/comparison")} icon={<Table2 size={15} />}>Open comparison</Button>
        </>} />

      <div className="grid g4">
        <MetricCard icon={<Users size={14} />} label="Supplier responses" value={`${metrics.vendors_responded} of ${metrics.vendors_invited}`}
          hint="received and read" onClick={() => nav("/vendors")} />
        <MetricCard icon={<Package size={14} />} label="Items in scope" value={`${metrics.skus} SKUs`} hint="lines on the RFx" onClick={() => nav("/comparison")} />
        <MetricCard icon={<Boxes size={14} />} label="Annual demand" value={`${compact(metrics.annual_demand)} pcs`}
          hint={`${metrics.annual_demand.toLocaleString("en-IN")} boxes / year`} onClick={() => nav("/analyst")} />
        <MetricCard icon={<ShieldAlert size={14} />} label="Blocking issues" value={`${blockers.length} open`} alert={blockers.length > 0}
          hint={`${others.length} other exceptions`} onClick={() => nav("/review?severity=blocker")} />
      </div>

      <div className="split" style={{ alignItems: "stretch" }}>
        <div className="stack" style={{ gap: 20 }}>
          <Card className="fill" title="Needs your attention" icon={<ShieldAlert size={16} color="var(--critical)" />}
            actions={<Badge tone="critical">{blockers.length} blocker{blockers.length === 1 ? "" : "s"}</Badge>} pad={false}>
            {blockers.length === 0 ? <EmptyState icon={<Check size={22} />} title="No open blockers">Every blocking finding has been reviewed.</EmptyState>
              : <div className="fill-scroll">{blockers.map((f) => <FindingRow key={f.id} f={f} onOpen={() => nav(`/review?finding=${f.id}`)} />)}</div>}
          </Card>

        </div>

        <div className="stack" style={{ gap: 20 }}>
          <Card title="Evaluation progress" icon={<ClipboardCheck size={16} />}>
            <div className="steps vertical">
              {stages.map((s, i) => (
                <button key={s.key} className={`step ${s.state}`} onClick={() => nav(s.route)}>
                  <span className="ix">{s.state === "done" ? <Check size={13} /> : i + 1}</span>
                  <span className="lb"><b>{s.label}</b><span className="subtle">{s.state === "done" ? "Complete" : s.state === "current" ? "In progress" : "Not started"} · {s.detail}</span></span>
                </button>))}
            </div>
          </Card>

          <Card title="Other exceptions" icon={<AlertTriangle size={16} color="var(--warning)" />} actions={<Badge tone="warning">{others.length}</Badge>} pad={false}>
            {others.length === 0 ? <EmptyState title="No other open exceptions" /> :
              <div style={{ maxHeight: 300, overflow: "auto" }}>{others.map((f) => (
                <button key={f.id} className="list-row" style={{ width: "100%", background: "none", border: 0, textAlign: "left", cursor: "pointer" }}
                  onClick={() => nav(`/review?finding=${f.id}`)}>
                  <StatusBadge status={f.severity} /><div style={{ flex: 1, minWidth: 0 }}><div style={{ fontSize: 13 }}>{f.title}</div>
                    <div className="subtle">{f.vendor_key ? `${f.vendor_key} · ${f.vendor}` : "All vendors"}</div></div><ArrowRight size={14} color="var(--text-3)" /></button>))}</div>}
          </Card>

          <Card title="Recent activity" icon={<Activity size={16} />} pad={false}>
            {activity.length === 0 ? <EmptyState title="No activity yet">Activity will appear here as your team works on this RFx.</EmptyState> :
              <div style={{ maxHeight: 280, overflow: "auto" }}>{activity.map((a) => (
                <div key={a.id} className="list-row"><div style={{ flex: 1 }}><div style={{ fontSize: 13 }}>{a.text}</div>
                  <div className="subtle">{a.actor} · {fmtTime(a.at)}</div></div></div>))}</div>}
          </Card>
        </div>
      </div>

      <Card title="Supplier response tracker" icon={<Users size={16} />} pad={false} actions={<Button size="sm" variant="ghost" onClick={() => nav("/vendors")}>All suppliers</Button>}>
            <DataTable rows={vendors} rowKey={(v) => v.vendor_id} onRowClick={(v) => nav(`/vendors/${v.vendor_id}`)} columns={[
              { key: "s", label: "Supplier", render: (v) => <div><div style={{ fontWeight: 600 }}>{v.name}</div><div className="subtle">{v.key}</div></div> },
              { key: "r", label: "Response", render: (v) => <StatusBadge status={v.state} /> },
              { key: "f", label: "Messages received", right: true, render: (v) => <span className="num">{v.messages}</span> },
              { key: "c", label: "Coverage", right: true, render: (v) => <span className="num">{v.quoted_lines}/{v.lines}</span> },
              { key: "q", label: "Quality", render: (v) => v.quality ? <StatusBadge status={v.quality} /> : <span className="subtle">—</span> },
              { key: "m", label: "Commercial", render: (v) => v.commercial ? <StatusBadge status={v.commercial} /> : <span className="subtle">—</span> },
              { key: "a", label: "Last activity", render: (v) => <span className="subtle" style={{ whiteSpace: "nowrap" }}>{fmtTime(v.last_activity)}</span> },
              { key: "x", label: "", render: (v) => <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); nav(`/vendors/${v.vendor_id}`); }}>Open supplier</Button> },
            ]} />
          </Card>
    </div>
  );
}
