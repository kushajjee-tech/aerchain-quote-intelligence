// Renders a bound chart exactly as served: every bar/point is a row of the tool result (SC-09).
// No values are computed here beyond scaling to pixels.
const OK = ["VERIFIED", "EXTRACTED", "ASSUMED"];
const PALETTE = ["#2563eb", "#d97706", "#059669", "#7c3aed", "#dc2626"];

export default function Chart({ c }: { c: any }) {
  const W = 640, H = 260, L = 56, B = 40, T = 24;
  const xs: string[] = [...new Set<string>(c.data.map((d: any) => String(d.x)))];
  const series: string[] = c.series ? [...new Set<string>(c.data.map((d: any) => String(d.series)))] : ["_"];
  const ys = c.data.map((d: any) => Number(d.y));
  const max = Math.max(...ys) * 1.1 || 1;
  const plotW = W - L - 10, plotH = H - B - T;
  const groupW = plotW / xs.length, barW = Math.max(4, (groupW * 0.8) / series.length);
  const yPix = (v: number) => T + plotH - (v / max) * plotH;
  return (
    <figure style={{ margin: "8px 0" }}>
      <figcaption style={{ fontSize: 12, fontWeight: 600 }}>{c.title} <small style={{ fontWeight: 400, color: "#6b7280" }}>
        ({c.y} by {c.x}{c.series ? `, per ${c.series}` : ""}; from result {c.result_index})</small></figcaption>
      <svg width={W} height={H} role="img" aria-label={c.title} style={{ fontSize: 10 }}>
        <line x1={L} y1={T + plotH} x2={W - 10} y2={T + plotH} stroke="#9ca3af" />
        {[0, 0.5, 1].map((f) => <text key={f} x={L - 6} y={yPix(max * f / 1.1) + 3} textAnchor="end">{(max * f / 1.1).toFixed(2)}</text>)}
        {c.type === "line"
          ? series.map((s, si) => {
              const pts = c.data.filter((d: any) => (c.series ? String(d.series) : "_") === s)
                .map((d: any) => `${L + xs.indexOf(String(d.x)) * groupW + groupW / 2},${yPix(Number(d.y))}`).join(" ");
              return <polyline key={s} points={pts} fill="none" stroke={PALETTE[si % 5]} strokeWidth={2} />;
            })
          : c.data.map((d: any, i: number) => {
              const si = series.indexOf(c.series ? String(d.series) : "_");
              const x = L + xs.indexOf(String(d.x)) * groupW + groupW * 0.1 + si * barW;
              const weak = d.status && !OK.includes(d.status);
              return <rect key={i} x={x} y={yPix(Number(d.y))} width={barW - 1} height={T + plotH - yPix(Number(d.y))}
                fill={weak ? "#fff" : PALETTE[si % 5]} stroke={PALETTE[si % 5]} strokeDasharray={weak ? "3 2" : undefined} strokeWidth={weak ? 1.5 : 0}>
                <title>{`${c.x} ${d.x}${c.series ? ` · ${d.series}` : ""}: ${d.y}${d.status ? ` (${d.status})` : ""}`}</title></rect>;
            })}
        {xs.map((x, i) => <text key={x} x={L + i * groupW + groupW / 2} y={T + plotH + 14} textAnchor="middle">{x}</text>)}
      </svg>
      {c.series && <div style={{ fontSize: 11 }}>{series.map((s, i) => <span key={s} style={{ marginRight: 10 }}>
        <span style={{ display: "inline-block", width: 10, height: 10, background: PALETTE[i % 5], marginRight: 3 }} />{s}</span>)}</div>}
      {c.flagged_points > 0 && <div style={{ fontSize: 11, color: "#9a3412" }}>
        Outlined bars are not includable as they stand (e.g. Needs review): {c.data.filter((d: any) => d.status && !OK.includes(d.status))
          .map((d: any) => `${c.x} ${d.x}${c.series ? " " + d.series : ""} (${d.status})`).join(", ")}</div>}
      {c.omitted.length > 0 && <div style={{ fontSize: 11, color: "#9a3412" }}>
        Not plotted (no usable number): {c.omitted.map((o: any) => `${c.x} ${o.x}`).join(", ")}</div>}
    </figure>
  );
}
