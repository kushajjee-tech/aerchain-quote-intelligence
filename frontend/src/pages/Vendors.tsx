// Vendors & Inbox: searchable, filterable supplier list (from the overview) and the upload affordance.
import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Inbox, Upload, Users } from "lucide-react";
import { api } from "../api";
import { useRfx, VendorRow } from "../rfx";
import { Badge, Button, Card, DataTable, EmptyState, Notice, PageHeader, SearchInput, Select, StatusBadge, useEscape } from "../ui";
import { fmtTime } from "./Home";

const ACCEPT = [".eml", ".pdf", ".xlsx", ".docx", ".jpg", ".jpeg", ".png"];
const MAX_MB = 15;

export function UploadDialog({ onClose, vendor }: { onClose: () => void; vendor?: VendorRow }) {
  const { rfxId, refresh } = useRfx();
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState(vendor?.name ?? "");
  const [email, setEmail] = useState(vendor?.email ?? "");
  const [state, setState] = useState<"idle" | "uploading" | "done">("idle");
  const [err, setErr] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  useEscape(onClose);
  const pick = (f: File | undefined) => {
    setErr(null);
    if (!f) return;
    const ext = "." + (f.name.split(".").pop() ?? "").toLowerCase();
    if (!ACCEPT.includes(ext)) return setErr(`${f.name}: file type ${ext} is not accepted. Accepted: ${ACCEPT.join(", ")}.`);
    if (f.size > MAX_MB * 1024 * 1024) return setErr(`${f.name} is ${(f.size / 1048576).toFixed(1)} MB; the limit is ${MAX_MB} MB.`);
    setFile(f);
  };
  const submit = async () => {
    if (!file) return;
    setState("uploading"); setErr(null);
    try {
      const buf = new Uint8Array(await file.arrayBuffer());
      let bin = ""; for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode(...buf.subarray(i, i + 0x8000));
      await api(`/rfx/${rfxId}/upload`, { body: { vendor_name: name, vendor_email: email, filename: file.name, content_b64: btoa(bin) } });
      setState("done"); await refresh();
    } catch (e) { setErr(String(e).replace(/^Error: /, "")); setState("idle"); }
  };
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <div className="dialog" role="dialog" aria-modal="true" style={{ width: 520 }}>
        <h3 style={{ fontSize: 16, marginBottom: 4 }}>Upload a supplier response</h3>
        <div className="subtle" style={{ marginBottom: 14 }}>The original file is stored unchanged. Accepted: {ACCEPT.join(", ")} · up to {MAX_MB} MB.</div>
        {state === "done" ? (<>
          <Notice tone="success">Uploaded: <b>{file?.name}</b>. Status: <b>Uploaded</b>. It is read when you run <b>Read responses</b> in the Co-pilot’s RFx workflow
            (uses the AI extraction service, which needs the API key).</Notice>
          <div className="row" style={{ justifyContent: "flex-end", marginTop: 16 }}><Button variant="primary" onClick={onClose}>Done</Button></div>
        </>) : (<div className="stack">
          <label className="field">Supplier name<input className="input" value={name} onChange={(e) => setName(e.target.value)} /></label>
          <label className="field">Supplier email<input className="input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="sales@vendor.example" /></label>
          <div className="empty" style={{ border: "1px dashed var(--border-strong)", borderRadius: 8, cursor: "pointer", padding: 20 }}
            onClick={() => input.current?.click()} onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); pick(e.dataTransfer.files[0]); }}>
            <Upload size={20} /><h4>{file ? file.name : "Drop a file here or click to choose"}</h4>
            {file && <div className="subtle">{(file.size / 1024).toFixed(0)} KB</div>}
            <input ref={input} type="file" accept={ACCEPT.join(",")} hidden onChange={(e) => pick(e.target.files?.[0])} />
          </div>
          {err && <Notice tone="critical">{err}</Notice>}
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <Button variant="ghost" onClick={onClose}>Cancel</Button>
            <Button variant="primary" disabled={!file || !name.trim() || !email.includes("@")} loading={state === "uploading"} onClick={submit} icon={<Upload size={14} />}>Upload</Button>
          </div>
        </div>)}
      </div>
    </>
  );
}

export default function Vendors() {
  const { overview } = useRfx();
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [resp, setResp] = useState("all");
  const [qual, setQual] = useState("all");
  const [com, setCom] = useState("all");
  const [upload, setUpload] = useState(false);
  const vendors = overview?.vendors ?? [];
  const opts = (k: "state" | "quality" | "commercial") => [{ value: "all", label: "All" },
    ...[...new Set(vendors.map((v) => v[k] ?? "Not evaluated"))].map((s) => ({ value: s, label: s }))];
  const rows = useMemo(() => vendors.filter((v) =>
    `${v.name} ${v.key} ${v.email ?? ""}`.toLowerCase().includes(q.toLowerCase()) &&
    (resp === "all" || v.state === resp) && (qual === "all" || (v.quality ?? "Not evaluated") === qual) &&
    (com === "all" || (v.commercial ?? "Not evaluated") === com)), [vendors, q, resp, qual, com]);
  return (
    <div className="stack" style={{ gap: 20 }}>
      <PageHeader title="Vendors & Inbox" sub={`${overview?.metrics.vendors_responded ?? 0} of ${overview?.metrics.vendors_invited ?? 0} invited suppliers have responded`}
        actions={<Button variant="primary" icon={<Upload size={15} />} onClick={() => setUpload(true)}>Upload response</Button>} />
      <Card pad={false} title={<span className="row" style={{ gap: 8 }}><Users size={16} />Suppliers <Badge tone="neutral">{rows.length}</Badge></span>}
        actions={<>
          <SearchInput value={q} onChange={setQ} placeholder="Search name, ID or email" width={240} />
          <Select label="" value={resp} onChange={setResp} options={opts("state").map((o) => ({ ...o, label: o.value === "all" ? "Response: all" : o.label }))} />
          <Select value={qual} onChange={setQual} options={opts("quality").map((o) => ({ ...o, label: o.value === "all" ? "Quality: all" : o.label }))} />
          <Select value={com} onChange={setCom} options={opts("commercial").map((o) => ({ ...o, label: o.value === "all" ? "Commercial: all" : o.label }))} />
        </>}>
        <DataTable rows={rows} rowKey={(v) => v.vendor_id} onRowClick={(v) => nav(`/vendors/${v.vendor_id}`)}
          empty={<EmptyState icon={<Inbox size={22} />} title="No suppliers match these filters" />}
          columns={[
            { key: "n", label: "Supplier", sort: (v) => v.name, render: (v) => <div><div style={{ fontWeight: 600 }}>{v.name}</div><div className="subtle" style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={v.email ?? ""}><span className="mono">{v.key}</span> · {v.email}</div></div> },
            { key: "r", label: "Response", sort: (v) => v.state, render: (v) => <StatusBadge status={v.state} /> },
            { key: "c", label: "Quote coverage", sort: (v) => v.coverage_pct, render: (v) => (
              <div style={{ minWidth: 118 }}><div className="row nowrap" style={{ fontSize: 12 }}><span className="num">{v.quoted_lines} of {v.lines} SKUs</span><span className="ml-auto subtle num">{v.coverage_pct}%</span></div>
                <div className="bar-track"><div className="bar-fill" style={{ width: `${v.coverage_pct}%` }} /></div></div>) },
            { key: "q", label: "Quality docs", sort: (v) => v.quality ?? "", render: (v) => v.quality ? <StatusBadge status={v.quality} /> : <span className="subtle">Not evaluated</span> },
            { key: "m", label: "Commercial", sort: (v) => v.commercial ?? "", render: (v) => v.commercial ? <StatusBadge status={v.commercial} /> : <span className="subtle">Not evaluated</span> },
            { key: "b", label: "Open findings", sort: (v) => v.blockers * 100 + v.exceptions, render: (v) => <span className="row nowrap" style={{ gap: 6 }}>
              {v.blockers > 0 ? <Badge tone="critical">{v.blockers} blocker{v.blockers > 1 ? "s" : ""}</Badge> : <span className="subtle">No blockers</span>}
              <span className="subtle">{v.exceptions} total</span></span> },
            { key: "l", label: "Last response", sort: (v) => v.last_activity ?? "", render: (v) => <span className="subtle" style={{ display: "inline-block", maxWidth: 70 }}>{fmtTime(v.last_activity)}</span> },
            { key: "a", label: "", render: (v) => <Button size="sm" className="nowrap" onClick={(e) => { e.stopPropagation(); nav(`/vendors/${v.vendor_id}`); }}>Open supplier</Button> },
          ]} />
      </Card>
      {upload && <UploadDialog onClose={() => setUpload(false)} />}
    </div>
  );
}
