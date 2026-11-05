import { useEffect, useState } from "react";
import ProvenanceDrawer from "../components/ProvenanceDrawer";
import { Chip, EXCLUDED, StatusBadge, ValueStatus } from "../components/StatusBadge";
import { useRfx } from "../rfx";

type Cell = { value: string | null; status: ValueStatus | null; state?: string; reasons?: string[]; flags?: string[]; freight_basis?: string };
type Row = { line_no: number; sku_code: string; description: string; annual_qty: number; cells: Record<string, Cell>; best_vendor_id: number | null };
type Vendor = { vendor_id: number; name: string; state: string; eligibility?: { quality: string; commercial: string } | null;
  documents?: { filename: string; doc_type: string; expiry_date: string | null; fact_status: string }[] };
type Data = { title: string; basis: string; provisional: boolean; vendors: Vendor[]; rows: Row[] };

const inr = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function CellView({ c, best }: { c: Cell; best: boolean }) {
  if (c.state === "AWAITING_RESPONSE") return <Chip text="Awaiting response" />;
  if (c.state === "PENDING_PROCESSING" || !c.status) return <Chip text="Processing…" />;
  if (EXCLUDED.includes(c.status) || c.value === null) return <StatusBadge status={c.status} />; // never a number
  return (
    <div style={{ fontWeight: best ? 700 : 400, background: best ? "#f0fdf4" : undefined }}>
      ₹{inr.format(Number(c.value))} <StatusBadge status={c.status} />
      {c.flags?.includes("FX") && <Chip text="FX" />}
      {c.flags?.includes("ALTERNATE") && <Chip text="Alternate spec" />}
      {c.flags?.includes("NEW_WARNING_AFTER_REVIEW") && <Chip text="New warning" />}
    </div>
  );
}

export default function Comparison() {
  const { rfxId } = useRfx();
  const [open, setOpen] = useState<{ v: number; l: number } | null>(null);
  const [tick, setTick] = useState(0);
  const [basis, setBasis] = useState("unit");
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/rfx/${rfxId}/comparison?basis=${basis}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)))
      .then((d) => { setData(d); setError(null); })
      .catch((e) => setError(String(e)));
  }, [rfxId, basis, tick]);

  return (
    <section>
      <h2>Comparison {data && `— ${data.title}`}</h2>
      {["unit", "landed", "quoted"].map((b) => (
        <button key={b} onClick={() => setBasis(b)} disabled={basis === b}>{b === "unit" ? "Unit (ex-GST ₹/box)" : b === "landed" ? "Landed" : "As quoted"}</button>
      ))}
      {" "}<a href={`/api/rfx/${rfxId}/export.xlsx?basis=${basis === "quoted" ? "unit" : basis}`}>Export xlsx</a>{" · "}
      <a href={`/api/rfx/${rfxId}/audit.csv`}>Audit log (csv)</a>
      {error && <p role="alert">Could not load: {error}</p>}
      {data?.provisional && <p style={{ background: "#fef9c3", padding: 6 }}>Provisional — responses still processing. Analysis and award are disabled.</p>}
      {data && (
        <div style={{ overflowX: "auto", maxWidth: "100%" }}>
        <table style={{ borderCollapse: "collapse", fontSize: 13, marginTop: 8, whiteSpace: "nowrap" }}>
          <thead>
            <tr>
              <th>#</th><th>SKU</th><th>Description</th><th>Annual qty</th>
              {data.vendors.map((v) => <th key={v.vendor_id} style={{ verticalAlign: "top", textAlign: "left" }}>
                {v.name}{v.state === "AWAITING_RESPONSE" && " (awaiting)"}
                {v.eligibility && <div style={{ fontWeight: 400, fontSize: 11 }}>
                  <a href="/vendors">Quality: {v.eligibility.quality} · Commercial: {v.eligibility.commercial}</a></div>}
                {v.documents && v.documents.length > 0 && <div style={{ fontWeight: 400, fontSize: 11 }}>
                  {v.documents.map((d) => <span key={d.filename} title={`${d.doc_type}${d.expiry_date ? ", valid to " + d.expiry_date : ""}`}>
                    <Chip text={d.filename} /> </span>)}</div>}
              </th>)}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((r) => (
              <tr key={r.line_no} style={{ borderTop: "1px solid #e5e7eb" }}>
                <td>{r.line_no}</td><td>{r.sku_code}</td>
                <td title={r.description} style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis" }}>{r.description}</td><td>{r.annual_qty.toLocaleString("en-IN")}</td>
                {data.vendors.map((v) => (
                  <td key={v.vendor_id} style={{ padding: "2px 6px", cursor: "pointer" }}
                      onClick={() => r.cells[String(v.vendor_id)]?.status && setOpen({ v: v.vendor_id, l: r.line_no })}>
                    <CellView c={r.cells[String(v.vendor_id)]} best={r.best_vendor_id === v.vendor_id} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
      {open && <ProvenanceDrawer rfxId={rfxId} vendorId={open.v} lineNo={open.l} onClose={() => setOpen(null)} onChanged={() => setTick(tick + 1)} />}
    </section>
  );
}
