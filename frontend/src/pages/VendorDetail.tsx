// Supplier detail: Overview · Inbox & correspondence · Documents · Quoted items. Originals are served unchanged.
import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams, useNavigate } from "react-router-dom";
import { ArrowRight, ChevronRight, ExternalLink, FileImage, FileSpreadsheet, FileText, Mail, MailOpen, Paperclip, Send, Upload } from "lucide-react";
import { api, inr } from "../api";
import { OPEN, useRfx } from "../rfx";
import { Badge, Button, Card, DataTable, Drawer, EmptyState, ErrorState, Notice, PageHeader, Segmented, Skeleton, StatusBadge, Tabs } from "../ui";
import { UploadDialog } from "./Vendors";
import { useAssistantScope } from "../assistant";

type Tab = "overview" | "inbox" | "documents" | "items";
const icon = (kind: string) => kind === "image" ? <FileImage size={16} /> : kind === "xlsx" ? <FileSpreadsheet size={16} /> : kind === "email_body" ? <Mail size={16} /> : <FileText size={16} />;
const DOC_GROUP: Record<string, string> = { ISO_9001_CERTIFICATE: "Quality", BCT_ECT_TEST_REPORT: "Quality", FOOD_CONTACT_DECLARATION: "Compliance" };
const GROUPS = ["Quotation", "Questionnaire", "Quality", "Compliance", "Correspondence", "Other"];

export function Preview({ doc, onClose }: { doc: { filename: string; url: string; kind?: string }; onClose: () => void }) {
  const ext = doc.filename.split(".").pop()?.toLowerCase() ?? "";
  const img = ["jpg", "jpeg", "png"].includes(ext), pdf = ext === "pdf";
  const [text, setText] = useState<string | null>(null);
  useEffect(() => { if (doc.kind === "email_body") fetch(doc.url).then((r) => r.text()).then(setText).catch(() => setText(null)); }, [doc]);
  return (
    <Drawer title={doc.filename} sub="Original file as received — not modified" onClose={onClose}
      actions={<a className="btn sm" href={doc.url} target="_blank" rel="noreferrer"><ExternalLink size={14} />Open original</a>}>
      {doc.filename.includes("AI-generated") && <div style={{ marginBottom: 10 }}><Notice tone="warning">AI-generated image used as a synthetic rate-card fixture. It is not a camera photograph.</Notice></div>}
      {img && <img src={doc.url} alt={doc.filename} style={{ width: "100%", borderRadius: 8, border: "1px solid var(--border)" }} />}
      {pdf && <iframe title={doc.filename} src={doc.url} style={{ width: "100%", height: "75vh", border: "1px solid var(--border)", borderRadius: 8 }} />}
      {doc.kind === "email_body" && (text === null ? <Skeleton /> : <pre className="quote" style={{ whiteSpace: "pre-wrap" }}>{text}</pre>)}
      {!img && !pdf && doc.kind !== "email_body" && <EmptyState icon={icon(ext)} title="No in-app preview for this file type">
        Open or download the original to view it. <div style={{ marginTop: 10 }}><a className="btn primary" href={doc.url} target="_blank" rel="noreferrer">Download {ext.toUpperCase()}</a></div></EmptyState>}
    </Drawer>
  );
}

function Eligibility({ e }: { e: any }) {
  if (!e) return <Skeleton />;
  if (!e.configured) return <div className="muted">{e.note}</div>;
  return (
    <div className="stack" style={{ gap: 16 }}>
      {(["quality", "commercial"] as const).map((sec) => (
        <div key={sec}>
          <div className="row" style={{ marginBottom: 6 }}><b>{sec === "quality" ? "Quality questionnaire" : "Commercial terms"}</b><StatusBadge status={e[sec].label} /></div>
          <table className="t dense"><tbody>{e[sec].questions.map((q: any) => (
            <tr key={q.key}><td style={{ width: 70 }} className="mono">{q.key}</td><td style={{ width: 140 }}><StatusBadge status={q.label} /></td>
              <td>{q.reason}{q.provenance?.answer?.text && <div className="subtle">Supplier stated: “{q.provenance.answer.text}”</div>}
                {q.provenance?.documents?.[0]?.expiry && <div className="subtle">Document valid to {q.provenance.documents[0].expiry}</div>}</td></tr>))}</tbody></table>
        </div>))}
      {e.line_level?.length > 0 && <div><b>Line-level requirements</b>
        <table className="t dense" style={{ marginTop: 6 }}><tbody>{e.line_level.map((q: any) => (
          <tr key={q.key}><td className="mono" style={{ width: 70 }}>{q.key}</td><td style={{ width: 140 }}><StatusBadge status={q.label} /></td>
            <td>{q.flag.replace("_", "-")} lines {q.lines.join(", ")}</td></tr>))}</tbody></table></div>}
    </div>
  );
}

function Pack({ rfxId, vendorId }: { rfxId: number; vendorId: number }) {
  const [pack, setPack] = useState<any>(null);
  const [body, setBody] = useState("");
  const [msg, setMsg] = useState<{ tone: "success" | "critical"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const gen = async () => {
    setBusy(true);
    try { const p = await api(`/rfx/${rfxId}/vendors/${vendorId}/clarification-pack`, { body: {} }); setPack(p); setBody(p.body); setMsg(null); }
    catch (e) { setMsg({ tone: "critical", text: String(e) }); } finally { setBusy(false); }
  };
  const approve = async () => {
    setBusy(true);
    try {
      if (body !== pack.body) await api(`/clarification-packs/${pack.pack_id}`, { method: "PUT", body: { body } });
      const r = await api(`/clarification-packs/${pack.pack_id}/approve`, { body: { actor: "buyer" } });
      setMsg({ tone: "success", text: `Approved and placed in the outbox (message #${r.outbox_message_id}). No email integration is configured, so nothing is sent automatically.` });
      setPack({ ...pack, status: r.status });
    } catch (e) { setMsg({ tone: "critical", text: String(e) }); } finally { setBusy(false); }
  };
  return (
    <Card title="Clarification request" icon={<Send size={16} />} actions={<Button size="sm" onClick={gen} loading={busy && !pack}>{pack ? "Regenerate" : "Draft clarification"}</Button>}>
      {!pack && !msg && <div className="muted">Drafts a clarification email from this supplier’s open findings, ordered by how much they could change the decision. Template-generated, no AI. Nothing is sent without approval.</div>}
      {pack && (<div className="stack">
        <div className="row wrap" style={{ gap: 6 }}>{pack.items.map((i: any) => <span key={i.sensitivity_rank} className="chip">{i.sensitivity_rank}. {i.kind.replace(/_/g, " ").toLowerCase()}{i.line_no ? ` · L${i.line_no}` : ""}</span>)}</div>
        <textarea className="textarea mono" value={body} onChange={(e) => setBody(e.target.value)} disabled={pack.status !== "draft"} style={{ height: 240 }} />
        <div className="row"><Badge tone={pack.status === "draft" ? "neutral" : "success"}>{pack.status}</Badge>
          <Button className="ml-auto" variant="primary" disabled={pack.status !== "draft"} loading={busy} onClick={approve}>Approve and place in outbox</Button></div>
      </div>)}
      {msg && <div style={{ marginTop: 10 }}><Notice tone={msg.tone}>{msg.text}</Notice></div>}
    </Card>
  );
}

export default function VendorDetail() {
  const { vendorId } = useParams();
  const vid = Number(vendorId);
  const { rfxId, overview } = useRfx();
  const nav = useNavigate();
  const [sp, setSp] = useSearchParams();
  const tab = (sp.get("tab") as Tab) || "overview";
  const [elig, setElig] = useState<any>(null);
  const [msgs, setMsgs] = useState<any[] | null>(null);
  const [docs, setDocs] = useState<any[] | null>(null);
  const [cmp, setCmp] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [preview, setPreview] = useState<any>(null);
  const [openMsg, setOpenMsg] = useState(0);
  const [itemFilter, setItemFilter] = useState<"all" | "quoted" | "missing" | "exceptions">("all");
  const [upload, setUpload] = useState(false);
  const v = overview?.vendors.find((x) => x.vendor_id === vid);
  useAssistantScope(v ? { label: `${v.key} · ${v.name}`, context: `The buyer is viewing supplier ${v.key} ${v.name} (${v.state}; quality ${v.quality ?? "not evaluated"}, commercial ${v.commercial ?? "not evaluated"}; ${v.quoted_lines} of ${v.lines} SKUs quoted).`,
    prompts: [`What is missing or unresolved for ${v.name}?`, `Is ${v.name} qualified, and why?`, `Draft clarification questions for ${v.key}.`] } : null);

  useEffect(() => {
    setErr(null);
    api(`/rfx/${rfxId}/vendors/${vid}/eligibility`).then(setElig).catch(() => setElig({ configured: false, note: "Eligibility not available." }));
    api(`/rfx/${rfxId}/vendors/${vid}/messages`).then(setMsgs).catch((e) => { setMsgs([]); setErr(String(e)); });
    api(`/rfx/${rfxId}/vendors/${vid}/documents`).then(setDocs).catch(() => setDocs([]));
    api(`/rfx/${rfxId}/comparison?basis=unit`).then(setCmp).catch(() => setCmp(null));
  }, [rfxId, vid]);

  const facts = useMemo(() => Object.fromEntries((cmp?.vendors.find((x: any) => x.vendor_id === vid)?.documents ?? []).map((d: any) => [d.filename, d])), [cmp, vid]);
  const evid = useMemo(() => {
    const m: Record<string, any> = {};
    if (elig?.configured) ["quality", "commercial"].forEach((sec) => elig[sec].questions.forEach((q: any) => (q.provenance?.documents ?? []).forEach((d: any) => { if (d.filename) m[d.filename] = d; })));
    return m;
  }, [elig]);
  const msgKind = useMemo(() => Object.fromEntries((msgs ?? []).map((m) => [m.file, m.kind])), [msgs]);
  const grouped = useMemo(() => {
    const g: Record<string, any[]> = {};
    (docs ?? []).forEach((d) => {
      const f = facts[d.filename];
      const grp = f ? DOC_GROUP[f.doc_type] ?? "Other" : d.kind === "email_body" ? "Correspondence"
        : /question/i.test(d.filename) || msgKind[d.message] === "QUESTIONNAIRE" ? "Questionnaire" : "Quotation";
      (g[grp] ??= []).push({ ...d, fact: f });
    });
    return g;
  }, [docs, facts, msgKind]);
  if (!v) return <EmptyState title="Supplier not found">This supplier is not invited to the selected RFx. <Link to="/vendors">Back to suppliers</Link></EmptyState>;
  const findings = (overview?.findings ?? []).filter((f) => f.vendor_id === vid);
  const openF = findings.filter((f) => OPEN.includes(f.review.state));
  const rows = (cmp?.rows ?? []).map((r: any) => ({ ...r, c: r.cells[String(vid)] }));
  const items = rows.filter((r: any) => itemFilter === "all" ? true : itemFilter === "quoted" ? r.c?.status && r.c.status !== "MISSING"
    : itemFilter === "missing" ? r.c?.status === "MISSING" : r.c?.status && !["VERIFIED", "EXTRACTED", "ASSUMED", "MISSING"].includes(r.c.status));
  const setTab = (t: Tab) => setSp(t === "overview" ? {} : { tab: t });

  return (
    <div className="stack" style={{ gap: 20 }}>
      <PageHeader crumbs={<><Link to="/vendors">Vendors & Inbox</Link><ChevronRight size={13} /><span>{v.name}</span></>}
        title={v.name} sub={<span className="row" style={{ gap: 8 }}><span className="mono">{v.key}</span>·<span>{v.email}</span></span>}
        badge={<StatusBadge status={v.state} />}
        actions={<><Button icon={<Upload size={15} />} onClick={() => setUpload(true)}>Upload file</Button>
          <Button variant="primary" icon={<ArrowRight size={15} />} onClick={() => nav(`/comparison?vendor=${vid}`)}>View in comparison</Button></>} />
      <Tabs value={tab} onChange={setTab} tabs={[{ key: "overview", label: "Overview" }, { key: "inbox", label: <>Inbox & correspondence <Badge tone="neutral">{msgs?.length ?? "…"}</Badge></> },
        { key: "documents", label: <>Documents <Badge tone="neutral">{docs?.length ?? "…"}</Badge></> }, { key: "items", label: <>Quoted items <Badge tone="neutral">{v.quoted_lines}/{v.lines}</Badge></> }]} />
      {err && <ErrorState error={err} />}

      {tab === "overview" && (
        <div className="split">
          <div className="stack" style={{ gap: 20 }}>
            <Card title="Response summary">
              <dl className="kv">
                <dt>Response</dt><dd><StatusBadge status={v.state} /></dd>
                <dt>Messages received</dt><dd className="num">{v.messages}</dd>
                <dt>Quote coverage</dt><dd className="num">{v.quoted_lines} of {v.lines} SKUs ({v.coverage_pct}%)</dd>
                <dt>Quality</dt><dd>{v.quality ? <StatusBadge status={v.quality} /> : "Not evaluated"}</dd>
                <dt>Commercial</dt><dd>{v.commercial ? <StatusBadge status={v.commercial} /> : "Not evaluated"}</dd>
                <dt>Findings</dt><dd>{v.blockers} open blocker{v.blockers === 1 ? "" : "s"} · {v.exceptions} findings in total</dd>
              </dl>
            </Card>
            <Card title="Qualification evidence"><Eligibility e={elig} /></Card>
          </div>
          <div className="stack" style={{ gap: 20 }}>
            <Card title="Key findings" pad={false} actions={<Button size="sm" variant="ghost" onClick={() => nav(`/review?vendor=${vid}`)}>Open in Review</Button>}>
              {openF.length === 0 ? <EmptyState title="No open findings for this supplier" /> : openF.map((f) => (
                <button key={f.id} className="list-row" style={{ width: "100%", background: "none", border: 0, textAlign: "left", cursor: "pointer" }} onClick={() => nav(`/review?finding=${f.id}`)}>
                  <StatusBadge status={f.severity} /><div style={{ flex: 1 }}><div style={{ fontSize: 13 }}>{f.title}</div><div className="subtle">{f.category}</div></div>
                  <ArrowRight size={14} color="var(--text-3)" /></button>))}
            </Card>
            <Pack rfxId={rfxId} vendorId={vid} />
          </div>
        </div>)}

      {tab === "inbox" && (msgs === null ? <Skeleton rows={6} /> : msgs.length === 0 ? <EmptyState icon={<Mail size={22} />} title="No messages from this supplier yet" /> : (
        <div className="split" style={{ gridTemplateColumns: "340px 1fr" }}>
          <Card pad={false} title="Messages">
            {msgs.map((m, i) => (
              <button key={m.file} className="list-row" onClick={() => setOpenMsg(i)}
                style={{ width: "100%", border: 0, textAlign: "left", cursor: "pointer", background: i === openMsg ? "var(--primary-soft)" : "none" }}>
                {i === openMsg ? <MailOpen size={16} /> : <Mail size={16} />}
                <div style={{ flex: 1, minWidth: 0 }}><div style={{ fontWeight: 600, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.subject}</div>
                  <div className="subtle">{m.date}</div>
                  <div className="row" style={{ gap: 4, marginTop: 2 }}><Badge tone="outline">{m.kind.toLowerCase()}</Badge>{m.attachments.length > 0 && <span className="subtle row" style={{ gap: 2 }}><Paperclip size={11} />{m.attachments.length}</span>}</div></div>
              </button>))}
          </Card>
          {msgs[openMsg] && (() => { const m = msgs[openMsg]; return (
            <Card title={m.subject}>
              <dl className="kv" style={{ marginBottom: 14 }}><dt>From</dt><dd>{m.from}</dd><dt>Date</dt><dd>{m.date}</dd><dt>File</dt><dd className="mono">{m.file}</dd></dl>
              <pre className="quote" style={{ whiteSpace: "pre-wrap", fontFamily: "var(--font)", fontSize: 13 }}>{m.body}</pre>
              {m.attachments.length > 0 && <><div className="section-title" style={{ marginTop: 16 }}>Attachments</div>
                <div className="stack" style={{ gap: 8 }}>{m.attachments.map((a: any) => (
                  <div key={a.filename} className="row" style={{ border: "1px solid var(--border)", borderRadius: 8, padding: "8px 12px" }}>
                    {icon(a.kind)}<div style={{ flex: 1 }}><div style={{ fontWeight: 500 }}>{a.filename}</div>
                      <div className="subtle">{(a.size / 1024).toFixed(0)} KB · {a.mime}{a.ocr && ` · OCR read, ${a.ocr.ocr_lines} lines, mean confidence ${a.ocr.mean_conf}%`}</div></div>
                    <StatusBadge status={a.parse_status} />{a.filename.includes("AI-generated") && <Badge tone="warning">AI-generated image</Badge>}
                    <Button size="sm" onClick={() => setPreview(a)}>Preview</Button></div>))}</div></>}
            </Card>); })()}
        </div>))}

      {tab === "documents" && (docs === null ? <Skeleton rows={6} /> : docs.length === 0 ? <EmptyState title="No documents received" /> : (
        <div className="stack" style={{ gap: 16 }}>
          {GROUPS.filter((g) => grouped[g]?.length).map((g) => (
            <Card key={g} title={g} pad={false} actions={<Badge tone="neutral">{grouped[g].length}</Badge>}>
              <DataTable rows={grouped[g]} rowKey={(d) => d.message + d.ref} onRowClick={(d) => setPreview(d)} columns={[
                { key: "f", label: "File", render: (d) => <span className="row" style={{ gap: 8 }}>{icon(d.kind)}<span style={{ fontWeight: 500 }}>{d.filename}</span></span> },
                { key: "t", label: "Type", render: (d) => <span className="subtle">{d.fact ? d.fact.doc_type.replace(/_/g, " ").toLowerCase() : d.kind.replace("_", " ")}</span> },
                { key: "s", label: "Read status", render: (d) => <span className="row" style={{ gap: 6 }}><StatusBadge status={d.parse_status} />
                  {d.ocr && <Badge tone="warning" title="Single OCR read: prices need confirmation">OCR · {d.ocr.mean_conf}% conf.</Badge>}
                  {d.filename.includes("AI-generated") && <Badge tone="warning">AI-generated image</Badge>}</span> },
                { key: "v", label: "Validity", render: (d) => d.fact?.expiry_date ? <span className="num nowrap">to {d.fact.expiry_date}</span> : <span className="subtle">—</span> },
                { key: "x", label: "Evidence check", render: (d) => { const e = evid[d.filename]; if (!e) return <span className="subtle">—</span>;
                  return <div>{e.readable ? <Badge tone="success">Verified</Badge> : <Badge tone="warning" title="A stated value could not be found in the document text, or validity could not be resolved">Not verifiable</Badge>}
                    {e.entity_name && <div className="subtle">Issued to: {e.entity_name}</div>}</div>; } },
                { key: "m", label: "Received in", render: (d) => <span className="mono subtle">{d.message}</span> },
                { key: "a", label: "", render: (d) => <Button size="sm" onClick={(e) => { e.stopPropagation(); setPreview(d); }}>Preview</Button> },
              ]} />
              {grouped[g].some((d) => d.failure_reason) && <div style={{ padding: 12 }}><Notice tone="critical">{grouped[g].filter((d) => d.failure_reason).map((d) => `${d.filename}: ${d.failure_reason}`).join("; ")}</Notice></div>}
            </Card>))}
        </div>))}

      {tab === "items" && (
        <Card pad={false} title="Quoted items" actions={<Segmented value={itemFilter} onChange={setItemFilter}
          options={[{ key: "all", label: "All" }, { key: "quoted", label: "Quoted" }, { key: "missing", label: "Not quoted" }, { key: "exceptions", label: "Exceptions" }]} />}>
          {!cmp ? <div style={{ padding: 16 }}><Skeleton /></div> : <DataTable rows={items} rowKey={(r: any) => r.line_no} dense
            onRowClick={(r: any) => nav(`/comparison?line=${r.line_no}&vendor=${vid}`)}
            empty={<EmptyState title="No items in this view" />} columns={[
              { key: "l", label: "#", sort: (r: any) => r.line_no, render: (r: any) => <span className="num">{r.line_no}</span> },
              { key: "s", label: "SKU", sort: (r: any) => r.sku_code, render: (r: any) => <div><div className="mono">{r.sku_code}</div><div className="subtle">{r.description}</div></div> },
              { key: "q", label: "Annual qty", right: true, sort: (r: any) => r.annual_qty, render: (r: any) => <span className="num">{r.annual_qty.toLocaleString("en-IN")}</span> },
              { key: "as", label: "As quoted", render: (r: any) => r.c?.quoted?.value ? <span className="num">{r.c.quoted.currency} {r.c.quoted.value} <span className="subtle">{r.c.quoted.unit_class.replace("PER_", "/").toLowerCase()}</span></span> : <span className="subtle">—</span> },
              { key: "n", label: "Normalised ₹/box ex-GST", right: true, sort: (r: any) => Number(r.c?.value ?? 1e12), render: (r: any) => r.c?.value != null ? <span className="price num">{inr(r.c.value, 2)}</span> : <span className="subtle">No comparable value</span> },
              { key: "st", label: "Status", render: (r: any) => r.c?.status ? <StatusBadge status={r.c.status} /> : <StatusBadge status="Awaiting" /> },
            ]} />}
        </Card>)}
      {preview && <Preview doc={preview} onClose={() => setPreview(null)} />}
      {upload && <UploadDialog vendor={v} onClose={() => setUpload(false)} />}
    </div>
  );
}
