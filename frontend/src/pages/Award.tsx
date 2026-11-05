import { useState } from "react";
import { api, inr } from "../api";
import { Chip, StatusBadge } from "../components/StatusBadge";
import { useRfx } from "../rfx";

// AWD-1…4: formal scenario (freight-aware by default), readiness, audited acknowledgement, memo.
export default function Award() {
  const { rfxId } = useRfx();
  const [basis, setBasis] = useState("freight_aware");
  const [mode, setMode] = useState("strict");
  const [sc, setSc] = useState<any>(null);
  const [ready, setReady] = useState<any>(null);
  const [memo, setMemo] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const run = async () => {
    try {
      const r = await api(`/rfx/${rfxId}/scenarios`, { body: { name: "Award", basis, eligibility_mode: mode } });
      setSc(r); setReady(await api(`/scenarios/${r.scenario_id}/readiness`)); setMemo(null); setErr(null);
    } catch (e) { setErr(String(e)); }
  };
  const ack = async () => {
    try { await api(`/scenarios/${sc.scenario_id}/acknowledge`, { body: { actor: "buyer", reason: "reviewed readiness items" } });
          setMemo((await api(`/scenarios/${sc.scenario_id}/memo`, { body: {} })).memo_markdown); }
    catch (e) { setErr(String(e)); }
  };
  const sv = sc?.savings;
  return (
    <section>
      <h2>Award</h2>
      <label>Basis <select value={basis} onChange={(e) => setBasis(e.target.value)}>
        <option value="freight_aware">Freight-aware (formal default)</option><option value="unit">Unit</option><option value="landed">Landed</option></select></label>{" "}
      <label>Eligibility <select value={mode} onChange={(e) => setMode(e.target.value)}>
        <option value="strict">Strict (quality)</option><option value="inclusive">Inclusive</option><option value="none">None</option></select></label>{" "}
      <button onClick={run}>Run cheapest-per-line</button>
      {err && <p role="alert">{err}</p>}
      {sc && (<>
        <p><b>{inr(sc.total_annual_spend_inr, 0)}</b>/yr across {sc.awards.length} lines ·{" "}
          {Object.entries(sc.per_vendor_spend_inr).map(([v, a]) => `${v} ${inr(a as string, 0)} (${sc.per_vendor_share_pct[v]}%)`).join(" · ")}</p>
        {sv && <p>Savings vs last year: {inr(sv.vs_last_year.savings_inr, 0)} {sv.vs_last_year.savings_pct && `(${sv.vs_last_year.savings_pct}%)`}, {sv.vs_last_year.statement}.
          {sv.vs_best_single_vendor && <> vs best single vendor: {inr(sv.vs_best_single_vendor.savings_inr, 0)}, {sv.vs_best_single_vendor.statement}.</>}
          {sv.vs_last_year.bound_note && <><br /><small>{sv.vs_last_year.bound_note}.</small></>}</p>}
        <table style={{ borderCollapse: "collapse", fontSize: 13 }}>
          <thead><tr><th>Line</th><th>Vendor</th><th>₹/box (basis)</th><th>Status</th><th>Spend</th><th>Freight</th></tr></thead>
          <tbody>{sc.awards.map((a: any) => (
            <tr key={a.line_no} style={{ borderTop: "1px solid #e5e7eb" }}>
              <td>{a.line_no} {a.sku}</td><td>{a.vendor}</td><td>{inr(a.price_on_basis_inr, 4)}</td><td><StatusBadge status={a.status} /></td>
              <td>{inr(a.annual_spend_inr, 0)}</td>
              <td>{a.freight_status === "FREIGHT_DEPENDENT" ? <Chip text={`Freight-dependent · break-even ${inr(a.break_even_inr_per_box, 4)}`} /> : a.freight_basis}</td>
            </tr>))}</tbody>
        </table>
        {sc.uncovered_lines.length > 0 && <p>Not awarded: {sc.uncovered_lines.map((u: any) => u.line_no).join(", ")} (no includable quote)</p>}
        {(sc.ineligible_vendors.failed.length > 0 || sc.ineligible_vendors.unverified.length > 0) && <p>
          {sc.ineligible_vendors.failed.map((x: any) => `Failed: ${x.vendor}`).join("; ")}{" "}
          {sc.ineligible_vendors.unverified.map((x: any) => `Unverified (not failed): ${x.vendor}`).join("; ")}</p>}
        {ready && (<div style={{ border: "1px solid #fbbf24", padding: 8, marginTop: 8 }}>
          <b>Readiness check</b>
          <ul>{ready.items.map((i: any, k: number) => (
            <li key={k}><b>{i.kind}</b>{" "}
              {i.kind === "FREIGHT_DEPENDENT" && i.lines.map((l: any) => `L${l.line_no} ${l.vendor} (break-even ${inr(l.break_even_inr_per_box, 4)})`).join(", ")}
              {i.kind === "DECISION_SENSITIVE" && i.lines.map((l: any) => `L${l.line_no}`).join(", ")}
              {i.kind === "AWAITING_RESPONSE" && i.vendors.join(", ")}
              {i.kind === "FX_EXPOSURE" && i.exposures.map((x: any) => x.statement).join("; ")}
              {i.kind === "BILLED_WEIGHT_EXPOSURE" && i.statement}
              {i.kind === "REFERENCE_AMBIGUOUS" && `${i.cells.length} cells`}</li>))}</ul>
          <button onClick={ack} disabled={!ready.can_acknowledge}>Acknowledge and draft memo</button>
        </div>)}
        {memo && <p><a href={`/api/scenarios/${sc.scenario_id}/memo.md`}>Download memo (.md)</a> · <a href={`/api/scenarios/${sc.scenario_id}/memo.html`} target="_blank">Printable memo</a></p>}
        {memo && <pre style={{ whiteSpace: "pre-wrap", background: "#f9fafb", padding: 8, fontSize: 12 }}>{memo}</pre>}
      </>)}
    </section>
  );
}
