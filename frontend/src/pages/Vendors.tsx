import { useEffect, useState } from "react";
import { api } from "../api";
import { Chip } from "../components/StatusBadge";
import { useRfx } from "../rfx";

const LABEL_STYLE: Record<string, string> = { Passed: "#166534", Failed: "#991b1b", Unverified: "#9a3412", "Not applicable": "#6b7280" };

function Eligibility({ rfxId, vendorId }: { rfxId: number; vendorId: number }) {
  const [e, setE] = useState<any>(null);
  useEffect(() => { api(`/rfx/${rfxId}/vendors/${vendorId}/eligibility`).then(setE).catch(() => setE(null)); }, [rfxId, vendorId]);
  if (!e) return null;
  if (!e.configured) return <p><i>{e.note}</i></p>;
  return (
    <div style={{ display: "flex", gap: 24 }}>
      {(["quality", "commercial"] as const).map((sec) => (
        <div key={sec}>
          <b>{sec === "quality" ? "Quality" : "Commercial"}: <span style={{ color: LABEL_STYLE[e[sec].label] }}>{e[sec].label}</span></b>
          <ul style={{ margin: 4 }}>{e[sec].questions.map((q: any) => (
            <li key={q.key}>{q.no} {q.key}: <span style={{ color: LABEL_STYLE[q.label] }}>{q.label}</span> — {q.reason}
              {q.provenance?.documents?.[0]?.expiry && <small> (valid to {q.provenance.documents[0].expiry})</small>}</li>))}</ul>
        </div>))}
      <div>
        <b>Line-level</b>
        <ul style={{ margin: 4 }}>{e.line_level.map((q: any) => (
          <li key={q.key}>{q.key} on {q.flag.replace("_", "-")} lines {q.lines.join(", ")}: <span style={{ color: LABEL_STYLE[q.label] }}>{q.label}</span></li>))}</ul>
      </div>
    </div>
  );
}

function Documents({ rfxId, vendorId }: { rfxId: number; vendorId: number }) {
  const [docs, setDocs] = useState<any[]>([]);
  useEffect(() => { api(`/rfx/${rfxId}/vendors/${vendorId}/documents`).then(setDocs).catch(() => setDocs([])); }, [rfxId, vendorId]);
  if (!docs.length) return null;
  return (
    <div style={{ fontSize: 12, margin: "6px 0" }}><b>Documents received</b>
      <ul style={{ margin: 2 }}>{docs.map((d, i) => (
        <li key={i}><a href={d.url} target="_blank">{d.filename}</a> <Chip text={d.kind} />{" "}
          {d.parse_status !== "parsed" && <Chip text={`${d.parse_status}: ${d.failure_reason}`} />}
          {d.ocr && <Chip text={`OCR read · ${d.ocr.ocr_lines} lines · mean confidence ${d.ocr.mean_conf}% · single read → values need confirmation`} />}
          {d.filename.includes("AI-generated") && <Chip text="AI-generated image (synthetic fixture, not a camera photo)" />}
          <small style={{ color: "#6b7280" }}> · {d.message}</small></li>))}</ul></div>
  );
}

function Pack({ rfxId, vendorId }: { rfxId: number; vendorId: number }) {
  const [pack, setPack] = useState<any>(null);
  const [body, setBody] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const gen = async () => { const p = await api(`/rfx/${rfxId}/vendors/${vendorId}/clarification-pack`, { body: {} }); setPack(p); setBody(p.body); setMsg(null); };
  const approve = async () => {
    try {
      if (body !== pack.body) await api(`/clarification-packs/${pack.pack_id}`, { method: "PUT", body: { body } });
      const r = await api(`/clarification-packs/${pack.pack_id}/approve`, { body: { actor: "buyer" } });
      setMsg(`Approved — placed in the outbox (message #${r.outbox_message_id}). Record the vendor's answers as resolutions.`);
      setPack({ ...pack, status: r.status });
    } catch (e) { setMsg(String(e)); }
  };
  return (
    <div style={{ marginTop: 8 }}>
      <button onClick={gen}>Generate clarification pack</button>
      {pack && (<div>
        <p>{pack.items.length} items, ordered by decision sensitivity:{" "}
          {pack.items.map((i: any) => <Chip key={i.sensitivity_rank} text={`${i.sensitivity_rank}. ${i.kind}${i.line_no ? " L" + i.line_no : ""}`} />)}</p>
        <textarea value={body} onChange={(e) => setBody(e.target.value)} disabled={pack.status !== "draft"}
                  style={{ width: "100%", height: 260, fontFamily: "ui-monospace, monospace", fontSize: 12 }} />
        <button onClick={approve} disabled={pack.status !== "draft"}>Approve → outbox</button>
        <small style={{ marginLeft: 8, color: "#6b7280" }}>Template-generated, no AI. Nothing is sent without approval.</small>
      </div>)}
      {msg && <p>{msg}</p>}
    </div>
  );
}

export default function Vendors() {
  const { rfxId } = useRfx();
  const [vendors, setVendors] = useState<any[]>([]);
  useEffect(() => { api(`/rfx/${rfxId}/comparison`).then((d) => setVendors(d.vendors)).catch(() => setVendors([])); }, [rfxId]);
  return (
    <section>
      <h2>Vendors</h2>
      {vendors.map((v) => (
        <div key={v.vendor_id} style={{ border: "1px solid #e5e7eb", borderRadius: 6, padding: 10, marginBottom: 10 }}>
          <h3 style={{ margin: 0 }}>{v.name} <Chip text={v.state === "RESPONDED" ? "Responded" : "Awaiting response"} /></h3>
          {v.state === "RESPONDED" && <><Documents rfxId={rfxId} vendorId={v.vendor_id} /><Eligibility rfxId={rfxId} vendorId={v.vendor_id} /><Pack rfxId={rfxId} vendorId={v.vendor_id} /></>}
        </div>))}
    </section>
  );
}
