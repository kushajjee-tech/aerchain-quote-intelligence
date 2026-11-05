import { useEffect, useState } from "react";
import { api, inr } from "../api";
import { Chip, StatusBadge } from "./StatusBadge";

// REV-3: source view (cited units, verbatim), full trace, original Phase A read, resolutions, actions.
export default function ProvenanceDrawer({ rfxId, vendorId, lineNo, onClose, onChanged }:
  { rfxId: number; vendorId: number; lineNo: number; onClose: () => void; onChanged: () => void }) {
  const [p, setP] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");
  const load = () => api(`/rfx/${rfxId}/cells/${vendorId}/${lineNo}`).then(setP).catch((e) => setErr(String(e)));
  useEffect(() => { load(); }, [rfxId, vendorId, lineNo]);

  const act = async (type: string, extra: Record<string, unknown> = {}) => {
    try {
      await api(`/rfx/${rfxId}/resolutions`, { body: { vendor_id: vendorId, line_no: lineNo, type, ...extra } });
      setErr(null); setValue(""); setReason(""); await load(); onChanged();
    } catch (e) { setErr(String(e)); }
  };
  const sug = p?.trace?.find((t: any) => t.suggestion)?.suggestion;

  return (
    <aside style={{ position: "fixed", right: 0, top: 0, bottom: 0, width: 460, background: "#fff", borderLeft: "1px solid #d1d5db",
                    padding: 16, overflowY: "auto", boxShadow: "-4px 0 12px rgba(0,0,0,.08)", fontSize: 13 }}>
      <button onClick={onClose} style={{ float: "right" }}>Close</button>
      {!p && !err && <p>Loading…</p>}
      {err && <p role="alert" style={{ color: "#991b1b" }}>{err}</p>}
      {p && (<>
        <h3 style={{ marginTop: 0 }}>Line {p.line.line_no} · {p.line.sku}</h3>
        <p style={{ color: "#4b5563" }}>{p.line.description} · {p.line.annual_qty.toLocaleString("en-IN")}/yr</p>
        <p>
          {p.cell.value !== null ? <b>{inr(p.cell.value, 4)}/box</b> : <i>no number used</i>} <StatusBadge status={p.cell.status} />{" "}
          {p.cell.reasons.map((r: string) => <Chip key={r} text={r} />)} {p.cell.flags.map((f: string) => <Chip key={f} text={f} />)}
        </p>
        <p>Freight: {p.cell.freight_basis}{p.cell.landed !== null && <> · landed {inr(p.cell.landed, 4)}</>}
          {p.cell.weight_source && <> · weight {p.cell.weight_g} g ({p.cell.weight_source})</>}</p>

        <h4>Source</h4>
        {p.source ? p.source.cites.map((c: any, i: number) => (
          <div key={i} style={{ background: "#f9fafb", border: "1px solid #e5e7eb", padding: 6, marginBottom: 6 }}>
            <div style={{ color: "#6b7280" }}>{c.role} — quoted: “{c.quote}”</div>
            {c.units.map((u: any) => <div key={u.id}><code>{u.id}</code>{" "}
              {u.document && <a href={`/api/rfx/${rfxId}/vendors/${vendorId}/file?name=${encodeURIComponent(u.document)}`} target="_blank">
                open {u.document}</a>}<br />{u.text}</div>)}
          </div>
        )) : <p><i>No priced statement (reference or not quoted).</i></p>}

        <h4>How this value was derived</h4>
        <ol style={{ paddingLeft: 18 }}>
          {p.trace.filter((t: any) => t.step !== "evidence").map((t: any, i: number) => (
            <li key={i}><b>{t.step}</b> {t.label ?? ""} {t.output && <>→ {t.output}</>}
              {t.reference && <> (reference {t.reference} {t.reference_kind}, ratio {t.ratio})</>}
              {t.candidate && <> candidate {t.candidate}</>}
              {t.differences?.length > 0 && <> — {t.differences.map((d: any) => `${d.field} ${d.rfx}→${d.vendor}`).join("; ")}</>}
            </li>))}
        </ol>

        <h4>Resolve</h4>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          <button onClick={() => act("ACCEPT")}>Accept</button>
          {sug && <button onClick={() => act("ACCEPT_SUGGESTION")}>Accept suggestion (÷{sug.divide_by} → {inr(sug.suggested_unit_price, 4)})</button>}
          <button onClick={() => act("MARK_MISSING", { reason: reason || undefined })}>Mark missing</button>
        </div>
        <div style={{ marginTop: 6 }}>
          <input placeholder="₹/box ex-GST" value={value} onChange={(e) => setValue(e.target.value)} style={{ width: 110 }} />{" "}
          <input placeholder="reason / source note" value={reason} onChange={(e) => setReason(e.target.value)} style={{ width: 200 }} />
          <div style={{ marginTop: 4, display: "flex", gap: 6 }}>
            <button disabled={!value} onClick={() => act("CORRECT", { value, reason: reason || undefined })}>Correct</button>
            <button disabled={!value || !reason} onClick={() => act("OVERRIDE", { value, reason })}>Override (reason required)</button>
            <button disabled={!value || !reason} onClick={() => act("FREIGHT_ESTIMATE", { value, reason, line_no: undefined })}>Freight estimate (vendor-wide)</button>
          </div>
        </div>
        {p.cell.reasons.includes("REFERENCE_AMBIGUOUS") && (
          <div style={{ marginTop: 8 }}>
            Confirm “same as last year” (note required):{" "}
            {["prices", "terms", "both", "neither"].map((ch) => (
              <button key={ch} disabled={!reason} onClick={() => act("REFERENCE_CONFIRMATION", { choice: ch, reason, line_no: undefined })}>{ch}</button>))}
          </div>)}

        {p.resolutions.length > 0 && (<>
          <h4>Resolutions</h4>
          <ul>{p.resolutions.map((r: any) => <li key={r.id}>{r.type} {r.value ?? r.choice ?? ""} — {r.state} · {r.actor} · {r.reason ?? ""}</li>)}</ul>
        </>)}
      </>)}
    </aside>
  );
}
