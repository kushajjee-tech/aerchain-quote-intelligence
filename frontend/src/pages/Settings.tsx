import { useEffect, useState } from "react";
import { api } from "../api";
import { Chip } from "../components/StatusBadge";

// FX rate (DL-15/30) and constant-set versions (DL-18). Every change is audited and recomputes the comparison.
export default function Settings() {
  const [fx, setFx] = useState<any>({});
  const [sets, setSets] = useState<any[]>([]);
  const [rate, setRate] = useState(""); const [asOf, setAsOf] = useState(""); const [src, setSrc] = useState("");
  const [changes, setChanges] = useState<Record<string, string>>({}); const [ver, setVer] = useState(""); const [why, setWhy] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const load = () => { api("/settings/fx").then(setFx); api("/settings/constants").then(setSets); };
  useEffect(load, []);
  const act = async (fn: () => Promise<any>, ok: string) => { try { await fn(); setMsg(ok); load(); } catch (e) { setMsg(String(e)); } };
  const active = sets.find((s) => s.active);
  return (
    <section>
      <h2>Settings</h2>
      {msg && <p>{msg}</p>}
      <h3>FX rate (USD → INR)</h3>
      <p>Current: {fx.USD ? `${fx.USD.rate} as of ${fx.USD.as_of} (${fx.USD.source})` : <i>not set — USD prices stay Unresolved</i>}</p>
      <input placeholder="rate" value={rate} onChange={(e) => setRate(e.target.value)} style={{ width: 80 }} />{" "}
      <input placeholder="as of (YYYY-MM-DD)" value={asOf} onChange={(e) => setAsOf(e.target.value)} style={{ width: 130 }} />{" "}
      <input placeholder="source" value={src} onChange={(e) => setSrc(e.target.value)} />{" "}
      <button disabled={!rate || !asOf || !src} onClick={() => act(() => api("/settings/fx/USD", { method: "PUT", body: { rate_to_inr: rate, as_of: asOf, source: src } }),
        "FX rate saved; comparison recomputed")}>Save and recompute</button>

      <h3>Engineering constants and heuristics {active && <Chip text={`active: ${active.version} (${active.hash})`} />}</h3>
      {active && (<table style={{ fontSize: 12 }}><thead><tr><th>Key</th><th>Value</th><th>Unit</th><th>Validation</th><th>New value</th></tr></thead>
        <tbody>{active.constants.map((c: any) => (
          <tr key={c.key}><td>{c.key}</td><td>{c.value}</td><td>{c.unit}</td><td><Chip text={c.label} /></td>
            <td><input style={{ width: 70 }} value={changes[c.key] ?? ""} onChange={(e) => setChanges({ ...changes, [c.key]: e.target.value })} /></td></tr>))}</tbody></table>)}
      <input placeholder="new version name" value={ver} onChange={(e) => setVer(e.target.value)} />{" "}
      <input placeholder="reason / source" value={why} onChange={(e) => setWhy(e.target.value)} style={{ width: 240 }} />{" "}
      <button disabled={!ver || !why || !active} onClick={() => act(() => api("/settings/constants", { body: {
        base_version: active.version, new_version: ver, reason: why, changes: Object.fromEntries(Object.entries(changes).filter(([, v]) => v)) } }),
        `version ${ver} created (not active)`)}>Create version</button>
      <ul>{sets.map((s) => <li key={s.version}>{s.version} {s.active ? <Chip text="active" /> :
        <button onClick={() => act(() => api(`/settings/constants/${s.version}/activate`, { body: { reason: why || "activated in settings" } }),
          `${s.version} activated; comparison recomputed`)}>Activate</button>}</li>)}</ul>
    </section>
  );
}
