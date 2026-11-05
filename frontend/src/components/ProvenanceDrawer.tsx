// Cell evidence drawer: what the supplier stated (verbatim source), what the system calculated (trace), and the
// buyer's resolution controls. Every action is a recorded resolution; the original read is never overwritten.
import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { api, inr } from "../api";
import { Badge, Button, Drawer, ErrorState, Notice, Skeleton, StatusBadge } from "../ui";

const REASON: Record<string, string> = {
  UNIT_INHERITED: "Unit taken from the table header or a document-wide statement", WEIGHT_ESTIMATED: "₹/kg converted with an estimated box weight",
  REFERENCE_WEIGHT: "₹/kg converted with the SKU’s reference weight", METHOD_CONSTANTS: "Conversion uses engineering constants",
  GST_PER_RFX_BASIS: "GST treatment taken from the RFx basis", READ_SINGLE_SOURCE: "Read once by OCR — needs confirmation",
  LOW_OCR_CONFIDENCE: "Low OCR confidence", VALUE_NOT_IN_SOURCE: "Value not found in the cited source", REFERENCE_AMBIGUOUS: "“Same as last year” is ambiguous",
};
export const reasonText = (r: string) => REASON[r] ?? r.replace(/_/g, " ").toLowerCase();

export default function ProvenanceDrawer({ rfxId, vendorId, lineNo, onClose, onChanged }:
  { rfxId: number; vendorId: number; lineNo: number; onClose: () => void; onChanged: () => void }) {
  const [p, setP] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const load = () => api(`/rfx/${rfxId}/cells/${vendorId}/${lineNo}`).then((d) => { setP(d); setErr(null); }).catch((e) => setErr(String(e)));
  useEffect(() => { setP(null); load(); }, [rfxId, vendorId, lineNo]);

  const act = async (type: string, label: string, extra: Record<string, unknown> = {}) => {
    setBusy(true);
    try {
      await api(`/rfx/${rfxId}/resolutions`, { body: { vendor_id: vendorId, line_no: lineNo, type, ...extra } });
      setValue(""); setReason(""); setDone(`${label} recorded. The comparison has been recomputed.`); await load(); onChanged();
    } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  };
  const sug = p?.trace?.find((t: any) => t.suggestion)?.suggestion;
  return (
    <Drawer title={p ? `Line ${p.line.line_no} · ${p.line.sku}` : "Loading…"} sub={p ? `${p.vendor ?? ""} ${p.line.description} · ${p.line.annual_qty.toLocaleString("en-IN")} / yr` : undefined} onClose={onClose}>
      {!p && !err && <Skeleton rows={8} />}
      {err && <ErrorState error={err} onRetry={load} />}
      {p && (<div className="stack" style={{ gap: 18 }}>
        <div className="card" style={{ padding: 14 }}>
          <div className="row" style={{ alignItems: "baseline" }}>
            {p.cell.value !== null ? <span className="price" style={{ fontSize: 22 }}>{inr(p.cell.value, 2)}</span> : <span className="muted">No number is used for this cell</span>}
            {p.cell.value !== null && <span className="subtle">per box, ex-GST</span>}
            <span className="ml-auto"><StatusBadge status={p.cell.status} /></span>
          </div>
          <div className="row wrap" style={{ gap: 6, marginTop: 8 }}>
            {p.cell.flags.map((f: string) => <Badge key={f} tone="outline">{f.replace(/_/g, " ").toLowerCase()}</Badge>)}</div>
          <dl className="kv" style={{ marginTop: 10 }}>
            <dt>Freight</dt><dd>{p.cell.freight_basis?.replace(/_/g, " ").toLowerCase()}{p.cell.landed !== null && <> · landed {inr(p.cell.landed, 2)}</>}</dd>
            {p.cell.weight_source && <><dt>Box weight</dt><dd>{Number(p.cell.weight_g)} g ({p.cell.weight_source.replace(/_/g, " ").toLowerCase()})</dd></>}
          </dl>
          {p.cell.reasons.length > 0 && <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 13 }} className="muted">{p.cell.reasons.map((r: string) => <li key={r}>{reasonText(r)}</li>)}</ul>}
        </div>

        <div><div className="section-title">What the supplier stated</div>
          {p.source ? p.source.cites.map((c: any, i: number) => (
            <div key={i} className="quote" style={{ marginBottom: 8 }}>
              <div className="subtle" style={{ marginBottom: 4 }}>{c.role} · quoted “{c.quote}”</div>
              {c.units.map((u: any) => <div key={u.id} style={{ marginTop: 4 }}>
                <div>{u.text}</div>
                <div className="row subtle" style={{ gap: 6, marginTop: 2 }}><span className="mono">{u.id}</span>
                  {u.document && <a href={`/api/rfx/${rfxId}/vendors/${vendorId}/file?name=${encodeURIComponent(u.document)}`} target="_blank" rel="noreferrer" className="row" style={{ gap: 3 }}>
                    <ExternalLink size={11} />{u.document}</a>}</div></div>)}
            </div>)) : <div className="muted">No priced statement for this line (not quoted, or priced by reference).</div>}
        </div>

        <div><div className="section-title">What the system calculated</div>
          <ol style={{ paddingLeft: 18, margin: 0, fontSize: 13 }} className="stack">
            {p.trace.filter((t: any) => t.step !== "evidence").map((t: any, i: number) => (
              <li key={i}><b>{t.step.replace(/_/g, " ")}</b> {t.label ?? ""} {t.output && <span className="mono">→ {t.output}</span>}
                {t.reference && <span className="muted"> (reference {t.reference} {t.reference_kind}, ratio {t.ratio})</span>}
                {t.candidate && <span className="muted"> candidate {t.candidate}</span>}
                {t.differences?.length > 0 && <span className="muted"> — {t.differences.map((d: any) => `${d.field}: RFx ${d.rfx} → offered ${d.vendor}`).join("; ")}</span>}
              </li>))}
          </ol>
        </div>

        <div><div className="section-title">Buyer resolution</div>
          {done && <div style={{ marginBottom: 8 }}><Notice tone="success">{done}</Notice></div>}
          <div className="row wrap">
            <Button size="sm" variant="primary" loading={busy} onClick={() => act("ACCEPT", "Acceptance")}>Accept as read</Button>
            {sug && <Button size="sm" onClick={() => act("ACCEPT_SUGGESTION", "Suggestion")}>Accept suggestion (÷{sug.divide_by} → {inr(sug.suggested_unit_price, 2)})</Button>}
            <Button size="sm" onClick={() => act("MARK_MISSING", "Mark not quoted", { reason: reason || undefined })}>Mark not quoted</Button>
          </div>
          <div className="row wrap" style={{ marginTop: 10 }}>
            <input className="input" placeholder="₹/box ex-GST" value={value} onChange={(e) => setValue(e.target.value)} style={{ width: 130 }} aria-label="Corrected value" />
            <input className="input" placeholder="Reason / source note" value={reason} onChange={(e) => setReason(e.target.value)} style={{ flex: 1, minWidth: 180 }} aria-label="Reason" />
          </div>
          <div className="row wrap" style={{ marginTop: 8 }}>
            <Button size="sm" disabled={!value} onClick={() => act("CORRECT", "Correction", { value, reason: reason || undefined })}>Correct value</Button>
            <Button size="sm" disabled={!value || !reason} onClick={() => act("OVERRIDE", "Override", { value, reason })}>Override (reason required)</Button>
            <Button size="sm" disabled={!value || !reason} onClick={() => act("FREIGHT_ESTIMATE", "Freight estimate", { value, reason, line_no: undefined })}>Set freight estimate (vendor-wide)</Button>
          </div>
          {p.cell.reasons.includes("REFERENCE_AMBIGUOUS") && (
            <div style={{ marginTop: 10 }}><div className="subtle" style={{ marginBottom: 6 }}>Confirm what “same as last year” covers (reason required):</div>
              <div className="row wrap">{["prices", "terms", "both", "neither"].map((ch) => (
                <Button key={ch} size="sm" disabled={!reason} onClick={() => act("REFERENCE_CONFIRMATION", "Reference confirmation", { choice: ch, reason, line_no: undefined })}>{ch}</Button>))}</div></div>)}
        </div>

        {p.resolutions.length > 0 && <div><div className="section-title">Resolution history</div>
          <table className="t dense"><tbody>{p.resolutions.map((r: any) => (
            <tr key={r.id}><td>{r.type.replace(/_/g, " ").toLowerCase()}</td><td className="num">{r.value ?? r.choice ?? ""}</td><td><Badge tone="outline">{r.state}</Badge></td>
              <td className="subtle">{r.actor}{r.reason ? ` · ${r.reason}` : ""}</td></tr>))}</tbody></table></div>}
      </div>)}
    </Drawer>
  );
}
