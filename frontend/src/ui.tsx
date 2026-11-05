// Shared UI primitives. All styling comes from styles.css tokens; status is never colour alone (icon + word).
import { ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, Circle, Clock, HelpCircle, Info, Loader2,
  MinusCircle, Search, X, XCircle } from "lucide-react";

export function Button({ variant = "secondary", size, loading, icon, children, ...p }:
  { variant?: "primary" | "secondary" | "ghost" | "danger" | "link"; size?: "sm"; loading?: boolean; icon?: ReactNode } &
  React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button {...p} disabled={p.disabled || loading} className={`btn ${variant} ${size ?? ""} ${p.className ?? ""}`}>
      {loading ? <Loader2 size={14} className="spin" /> : icon}{children}
    </button>
  );
}

type Tone = "success" | "warning" | "critical" | "info" | "neutral" | "violet" | "outline";
export function Badge({ tone = "neutral", icon, children, title }: { tone?: Tone; icon?: ReactNode; children: ReactNode; title?: string }) {
  return <span className={`badge b-${tone}`} title={title}>{icon}{children}</span>;
}

// Value statuses (canonical vocabulary) and review/eligibility states, each with an icon and a word.
const STATUS: Record<string, { tone: Tone; label: string; icon: ReactNode }> = {
  VERIFIED: { tone: "success", label: "Verified", icon: <CheckCircle2 size={12} /> },
  EXTRACTED: { tone: "info", label: "Extracted", icon: <Circle size={12} /> },
  ASSUMED: { tone: "violet", label: "Assumed", icon: <Info size={12} /> },
  NEEDS_REVIEW: { tone: "warning", label: "Needs review", icon: <AlertTriangle size={12} /> },
  UNRESOLVED: { tone: "critical", label: "Unresolved", icon: <AlertCircle size={12} /> },
  NOT_CONVERTIBLE: { tone: "neutral", label: "Not comparable", icon: <MinusCircle size={12} /> },
  MISSING: { tone: "outline", label: "Not quoted", icon: <MinusCircle size={12} /> },
  Passed: { tone: "success", label: "Passed", icon: <CheckCircle2 size={12} /> },
  Failed: { tone: "critical", label: "Failed", icon: <XCircle size={12} /> },
  Unverified: { tone: "warning", label: "Unverified", icon: <HelpCircle size={12} /> },
  "Not applicable": { tone: "neutral", label: "Not applicable", icon: <MinusCircle size={12} /> },
  "Not provided": { tone: "outline", label: "Not provided", icon: <MinusCircle size={12} /> },
  Awaiting: { tone: "outline", label: "Awaiting", icon: <Clock size={12} /> },
  Received: { tone: "success", label: "Received", icon: <CheckCircle2 size={12} /> },
  Pending: { tone: "outline", label: "Pending", icon: <Clock size={12} /> },
  Processing: { tone: "info", label: "Processing", icon: <Loader2 size={12} /> },
  "Needs clarification": { tone: "warning", label: "Needs clarification", icon: <AlertTriangle size={12} /> },
  "Failed to read": { tone: "critical", label: "Failed to read", icon: <XCircle size={12} /> },
  blocker: { tone: "critical", label: "Blocker", icon: <AlertCircle size={12} /> },
  warning: { tone: "warning", label: "Warning", icon: <AlertTriangle size={12} /> },
  info: { tone: "info", label: "Info", icon: <Info size={12} /> },
  open: { tone: "neutral", label: "Open", icon: <Circle size={12} /> },
  confirmed: { tone: "critical", label: "Confirmed", icon: <AlertCircle size={12} /> },
  rejected: { tone: "success", label: "Dismissed", icon: <CheckCircle2 size={12} /> },
  clarification_requested: { tone: "info", label: "Clarification requested", icon: <Clock size={12} /> },
  not_applicable: { tone: "neutral", label: "Not applicable", icon: <MinusCircle size={12} /> },
  parsed: { tone: "success", label: "Parsed", icon: <CheckCircle2 size={12} /> },
  failed: { tone: "critical", label: "Failed", icon: <XCircle size={12} /> },
  deferred: { tone: "warning", label: "Not read", icon: <AlertTriangle size={12} /> },
};
export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const s = STATUS[status] ?? { tone: "neutral" as Tone, label: status, icon: <Circle size={12} /> };
  return <Badge tone={s.tone} icon={s.icon}>{label ?? s.label}</Badge>;
}

export function Card({ title, actions, children, pad = true, className, icon }:
  { title?: ReactNode; actions?: ReactNode; children: ReactNode; pad?: boolean; className?: string; icon?: ReactNode }) {
  return (
    <section className={`card ${className ?? ""}`}>
      {title && <div className="card-h">{icon}<h3>{title}</h3><div className="ml-auto row">{actions}</div></div>}
      <div className={pad ? "card-b" : ""}>{children}</div>
    </section>
  );
}

export function MetricCard({ label, value, hint, onClick, alert, icon }:
  { label: string; value: ReactNode; hint?: ReactNode; onClick?: () => void; alert?: boolean; icon?: ReactNode }) {
  return (
    <button className={`metric ${alert ? "alert" : ""}`} onClick={onClick}>
      <span className="k">{icon}{label}</span><span className="v">{value}</span>{hint && <span className="h">{hint}</span>}
    </button>
  );
}

export function PageHeader({ title, sub, actions, crumbs, badge }:
  { title: ReactNode; sub?: ReactNode; actions?: ReactNode; crumbs?: ReactNode; badge?: ReactNode }) {
  return (
    <div>
      {crumbs && <div className="crumbs">{crumbs}</div>}
      <div className="page-h">
        <div><div className="row"><h1>{title}</h1>{badge}</div>{sub && <div className="sub">{sub}</div>}</div>
        {actions && <div className="actions">{actions}</div>}
      </div>
    </div>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { key: T; label: ReactNode }[]; value: T; onChange: (t: T) => void }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => <button key={t.key} role="tab" aria-selected={value === t.key} className={value === t.key ? "on" : ""}
        onClick={() => onChange(t.key)}>{t.label}</button>)}
    </div>
  );
}

export function Segmented<T extends string>({ options, value, onChange }: { options: { key: T; label: string }[]; value: T; onChange: (t: T) => void }) {
  return <div className="seg">{options.map((o) => <button key={o.key} className={value === o.key ? "on" : ""} onClick={() => onChange(o.key)}>{o.label}</button>)}</div>;
}

export function SearchInput({ value, onChange, placeholder, width = 260 }: { value: string; onChange: (v: string) => void; placeholder?: string; width?: number }) {
  return (
    <div className="search" style={{ width }}>
      <Search size={15} />
      <input className="input" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} aria-label={placeholder} />
    </div>
  );
}

export function Select({ value, onChange, options, label, width }:
  { value: string; onChange: (v: string) => void; options: { value: string; label: string }[]; label?: string; width?: number }) {
  const sel = <select className="select" style={{ width }} value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}>
    {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>;
  return label ? <label className="field">{label}{sel}</label> : sel;
}

export function useEscape(onClose: () => void) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
}

export function Drawer({ title, sub, onClose, children, actions }: { title: ReactNode; sub?: ReactNode; onClose: () => void; children: ReactNode; actions?: ReactNode }) {
  useEscape(onClose);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.focus(); }, []);
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" tabIndex={-1} ref={ref}>
        <div className="drawer-h"><div style={{ flex: 1 }}><h3 style={{ fontSize: 16 }}>{title}</h3>{sub && <div className="subtle">{sub}</div>}</div>
          {actions}<button className="icon-btn" onClick={onClose} aria-label="Close"><X size={18} /></button></div>
        <div className="drawer-b">{children}</div>
      </aside>
    </>
  );
}

export function ConfirmDialog({ title, body, confirmLabel, onConfirm, onClose, danger, busy }:
  { title: string; body: ReactNode; confirmLabel: string; onConfirm: () => void; onClose: () => void; danger?: boolean; busy?: boolean }) {
  useEscape(onClose);
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <div className="dialog" role="alertdialog" aria-modal="true">
        <h3 style={{ fontSize: 16, marginBottom: 8 }}>{title}</h3>
        <div className="muted" style={{ marginBottom: 16 }}>{body}</div>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button variant={danger ? "danger" : "primary"} onClick={onConfirm} loading={busy} autoFocus>{confirmLabel}</Button>
        </div>
      </div>
    </>
  );
}

export function EmptyState({ icon, title, children }: { icon?: ReactNode; title: string; children?: ReactNode }) {
  return <div className="empty">{icon}<h4>{title}</h4>{children && <div>{children}</div>}</div>;
}

export function ErrorState({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return <div className="notice critical"><AlertCircle size={16} /><div style={{ flex: 1 }}>{error}</div>{onRetry && <Button size="sm" onClick={onRetry}>Retry</Button>}</div>;
}

export function Notice({ tone = "info", children }: { tone?: "info" | "warning" | "critical" | "success"; children: ReactNode }) {
  const icon = tone === "critical" ? <AlertCircle size={16} /> : tone === "warning" ? <AlertTriangle size={16} /> : tone === "success" ? <CheckCircle2 size={16} /> : <Info size={16} />;
  return <div className={`notice ${tone}`}>{icon}<div>{children}</div></div>;
}

export function Skeleton({ rows = 4 }: { rows?: number }) {
  return <div className="stack" aria-busy="true">{Array.from({ length: rows }).map((_, i) => <div key={i} className="skel" style={{ width: `${90 - i * 12}%` }} />)}</div>;
}

export type Column<T> = { key: string; label: ReactNode; render: (r: T) => ReactNode; sort?: (r: T) => number | string; right?: boolean; sticky?: boolean; width?: number };
export function DataTable<T>({ rows, columns, onRowClick, rowKey, empty, dense, maxHeight, rowClass, initialSort }:
  { rows: T[]; columns: Column<T>[]; onRowClick?: (r: T) => void; rowKey: (r: T) => string | number; empty?: ReactNode;
    dense?: boolean; maxHeight?: number; rowClass?: (r: T) => string; initialSort?: { key: string; dir: 1 | -1 } }) {
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(initialSort ?? null);
  const sorted = useMemo(() => {
    if (!sort) return rows;
    const col = columns.find((c) => c.key === sort.key);
    if (!col?.sort) return rows;
    return [...rows].sort((a, b) => {
      const x = col.sort!(a), y = col.sort!(b);
      return (x < y ? -1 : x > y ? 1 : 0) * sort.dir;
    });
  }, [rows, sort, columns]);
  if (!rows.length && empty) return <>{empty}</>;
  return (
    <div className="table-wrap" style={{ maxHeight }}>
      <table className={`t ${dense ? "dense" : ""}`}>
        <thead><tr>{columns.map((c) => (
          <th key={c.key} className={`${c.sort ? "sortable" : ""} ${c.right ? "r" : ""} ${c.sticky ? "sticky" : ""}`} style={{ width: c.width }}
            onClick={() => c.sort && setSort(sort?.key === c.key ? { key: c.key, dir: (sort.dir * -1) as 1 | -1 } : { key: c.key, dir: 1 })}
            aria-sort={sort?.key === c.key ? (sort.dir === 1 ? "ascending" : "descending") : undefined}>
            <span className="row" style={{ gap: 4, justifyContent: c.right ? "flex-end" : undefined }}>{c.label}
              {sort?.key === c.key && (sort.dir === 1 ? <ChevronUp size={12} /> : <ChevronDown size={12} />)}</span></th>))}</tr></thead>
        <tbody>{sorted.map((r) => (
          <tr key={rowKey(r)} className={`${onRowClick ? "click" : ""} ${rowClass?.(r) ?? ""}`} onClick={() => onRowClick?.(r)}>
            {columns.map((c) => <td key={c.key} className={`${c.right ? "r" : ""} ${c.sticky ? "sticky" : ""}`}>{c.render(r)}</td>)}</tr>))}</tbody>
      </table>
    </div>
  );
}

export function Bar({ value, max, label, tone = "primary" }: { value: number; max: number; label?: ReactNode; tone?: string }) {
  return (
    <div>
      {label && <div className="row" style={{ fontSize: 12, marginBottom: 4 }}>{label}</div>}
      <div className="bar-track"><div className="bar-fill" style={{ width: `${max ? Math.min(100, (value / max) * 100) : 0}%`, background: `var(--${tone})` }} /></div>
    </div>
  );
}
