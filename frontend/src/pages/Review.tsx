import { useEffect, useState } from "react";
import { api, inr } from "../api";
import ProvenanceDrawer from "../components/ProvenanceDrawer";
import { Chip, StatusBadge } from "../components/StatusBadge";
import { useRfx } from "../rfx";

// REV-1/2: one queue, decision-sensitive first (DL-28), then money at risk.
export default function Review() {
  const { rfxId } = useRfx();
  const [items, setItems] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [open, setOpen] = useState<{ v: number; l: number } | null>(null);
  const load = () => api(`/rfx/${rfxId}/review`).then((d) => { setItems(d.items); setErr(null); }).catch((e) => setErr(String(e)));
  useEffect(() => { load(); }, [rfxId]);

  return (
    <section>
      <h2>Review queue <small style={{ color: "#6b7280" }}>({items.length})</small></h2>
      {err && <p role="alert">{err}</p>}
      <table style={{ borderCollapse: "collapse", fontSize: 13 }}>
        <thead><tr><th>Impact</th><th>Vendor</th><th>Line</th><th>Status</th><th>Why</th><th>Value / candidate</th><th>Money at risk</th><th /></tr></thead>
        <tbody>
          {items.map((i, k) => (
            <tr key={k} style={{ borderTop: "1px solid #e5e7eb", background: i.decision_sensitive ? "#fff7ed" : undefined }}>
              <td>{i.decision_sensitive ? <span title={i.sensitivity.map((s: any) => s.detail).join("\n")}>
                ⚑ decision-sensitive{Number(i.impact_inr) > 1 && <> · {inr(i.impact_inr, 0)}/yr</>}</span> : ""}</td>
              <td>{i.vendor}</td>
              <td>{i.line_no ?? (i.question ? `${i.question} ${i.key}` : "")} {i.sku}</td>
              <td>{i.status ? <StatusBadge status={i.status === "UNVERIFIED" ? "NEEDS_REVIEW" : i.status} /> : <Chip text="freight unknown" />}
                {i.status === "UNVERIFIED" && <> <Chip text="Eligibility: Unverified" /></>}</td>
              <td>{(i.reasons ?? []).map((r: string) => <Chip key={r} text={r} />)}
                {i.flags?.includes("NEW_WARNING_AFTER_REVIEW") && <Chip text="NEW_WARNING_AFTER_REVIEW" />}
                {i.break_even && <> wins unless freight &gt; {inr(i.break_even, 4)}/box</>}</td>
              <td>{i.value ? inr(i.value, 4) : i.candidate ? <>candidate {inr(i.candidate, 4)}</> : "—"}
                {i.suggestion && <> · suggest ÷{i.suggestion.divide_by}</>}</td>
              <td>{inr(i.money_at_risk_inr, 0)}</td>
              <td>{i.line_no && <button onClick={() => setOpen({ v: i.vendor_id, l: i.line_no })}>Open</button>}</td>
            </tr>))}
        </tbody>
      </table>
      {open && <ProvenanceDrawer rfxId={rfxId} vendorId={open.v} lineNo={open.l} onClose={() => setOpen(null)} onChanged={load} />}
    </section>
  );
}
