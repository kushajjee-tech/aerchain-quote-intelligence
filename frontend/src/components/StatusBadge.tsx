// The single place that renders value statuses (architecture §4: one shared vocabulary everywhere).
export type ValueStatus =
  | "VERIFIED" | "EXTRACTED" | "ASSUMED" | "NEEDS_REVIEW" | "UNRESOLVED" | "NOT_CONVERTIBLE" | "MISSING";

const STYLE: Record<ValueStatus, { label: string; bg: string; fg: string }> = {
  VERIFIED: { label: "Verified", bg: "#dcfce7", fg: "#166534" },
  EXTRACTED: { label: "Extracted", bg: "#dbeafe", fg: "#1e40af" },
  ASSUMED: { label: "Assumed", bg: "#ede9fe", fg: "#5b21b6" },
  NEEDS_REVIEW: { label: "Needs review", bg: "#ffedd5", fg: "#9a3412" },
  UNRESOLVED: { label: "Unresolved", bg: "#fee2e2", fg: "#991b1b" },
  NOT_CONVERTIBLE: { label: "Not convertible", bg: "#e5e7eb", fg: "#374151" },
  MISSING: { label: "Missing", bg: "#f3f4f6", fg: "#6b7280" },
};

// Statuses that never carry a number into calculations (PRD §6.2).
export const EXCLUDED: ValueStatus[] = ["UNRESOLVED", "NOT_CONVERTIBLE", "MISSING"];

export function StatusBadge({ status }: { status: ValueStatus }) {
  const s = STYLE[status];
  return (
    <span style={{ background: s.bg, color: s.fg, borderRadius: 4, padding: "1px 6px", fontSize: 11, whiteSpace: "nowrap" }}>
      {s.label}
    </span>
  );
}

export function Chip({ text }: { text: string }) {
  return <span style={{ border: "1px dashed #9ca3af", borderRadius: 4, padding: "1px 6px", fontSize: 11, color: "#4b5563" }}>{text}</span>;
}
