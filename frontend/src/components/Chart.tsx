// Renders a bound chart exactly as served: every bar/point is a row of the tool result (SC-09).
// No values are computed here beyond scaling to pixels. Responsive: scales to the panel width.
const OK = ["VERIFIED", "EXTRACTED", "ASSUMED"];
const PALETTE = ["#3157c8", "#9a5b00", "#1f7a4d", "#5b3fa8", "#b42318", "#1e5aa8"];
const nice = (s: string) => /^[A-Z_]{4,}$/.test(s) ? s.replace(/_/g, " ").toLowerCase() : s;
const shortX = (s: string) => { const t = s.replace(/ (Pvt\.|Ltd\.|Private|Limited).*$/, ""); return t.length > 14 ? t.split(" ")[0] : t; };

export default function Chart({ c }: { c: any }) {
  const W = 640, H = 240, L = 48, B = 34, T = 14;
  const xs: string[] = [...new Set<string>(c.data.map((d: any) => String(d.x)))];
  const series: string[] = c.series ? [...new Set<string>(c.data.map((d: any) => String(d.series)))] : ["_"];
  const ys = c.data.map((d: any) => Number(d.y));
  const max = Math.max(...ys) * 1.1 || 1;
  const plotW = W - L - 10, plotH = H - B - T;
  const groupW = plotW / xs.length, barW = Math.max(4, (groupW * 0.8) / series.length);
  const yPix = (v: number) => T + plotH - (v / max) * plotH;
  const flagged = c.data.filter((d: any) => d.status && !OK.includes(d.status));
  return (
    <figure style={{ margin: "4px 0" }}>
      <figcaption style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>{c.title}</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={c.title} style={{ fontSize: 11, maxWidth: W, display: "block" }}>
        <line x1={L} y1={T + plotH} x2={W - 10} y2={T + plotH} stroke="#cfd5de" />
        {[0, 0.5, 1].map((f) => <g key={f}><line x1={L} x2={W - 10} y1={yPix(max * f / 1.1)} y2={yPix(max * f / 1.1)} stroke="#eef0f3" />
          <text x={L - 6} y={yPix(max * f / 1.1) + 4} textAnchor="end" fill="#657184">{Number((max * f / 1.1).toFixed(2))}</text></g>)}
        {c.type === "line"
          ? series.map((s, si) => {
              const pts = c.data.filter((d: any) => (c.series ? String(d.series) : "_") === s)
                .map((d: any) => `${L + xs.indexOf(String(d.x)) * groupW + groupW / 2},${yPix(Number(d.y))}`).join(" ");
              return <polyline key={s} points={pts} fill="none" stroke={PALETTE[si % 6]} strokeWidth={2} />;
            })
          : c.data.map((d: any, i: number) => {
              const si = series.indexOf(c.series ? String(d.series) : "_");
              const x = L + xs.indexOf(String(d.x)) * groupW + groupW * 0.1 + si * barW;
              const weak = d.status && !OK.includes(d.status);
              return <rect key={i} x={x} y={yPix(Number(d.y))} width={barW - 1} height={T + plotH - yPix(Number(d.y))} rx={1.5}
                fill={weak ? "#fff" : PALETTE[si % 6]} stroke={PALETTE[si % 6]} strokeDasharray={weak ? "3 2" : undefined} strokeWidth={weak ? 1.5 : 0}>
                <title>{`${d.x}${c.series ? ` · ${nice(String(d.series))}` : ""}: ${d.y}${d.status ? ` (${nice(d.status)})` : ""}`}</title></rect>;
            })}
        {xs.map((x, i) => <text key={x} x={L + i * groupW + groupW / 2} y={T + plotH + 16} textAnchor="middle" fill="#3b4656">{shortX(x)}</text>)}
      </svg>
      {c.series && <div className="row wrap" style={{ gap: 10, fontSize: 11, marginTop: 4 }}>{series.map((s, i) => <span key={s} className="row" style={{ gap: 4 }}>
        <span style={{ display: "inline-block", width: 9, height: 9, borderRadius: 2, background: PALETTE[i % 6] }} />{nice(s)}</span>)}</div>}
      {flagged.length > 0 && <div className="subtle" style={{ marginTop: 4 }} title={flagged.map((d: any) => `${d.x}${c.series ? " " + nice(String(d.series)) : ""}: ${nice(d.status)}`).join("\n")}>
        Dashed bars ({flagged.length}) are values that can't be used as they stand (hover for the list).</div>}
      {c.omitted.length > 0 && <div className="subtle">Not plotted (no usable number): {c.omitted.map((o: any) => shortX(String(o.x))).join(", ")}</div>}
    </figure>
  );
}
