// Thin API client. The UI does no business arithmetic: every number shown comes from the backend.
export async function api<T = any>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  const r = await fetch(`/api${path}`, {
    method: init?.method ?? (init?.body !== undefined ? "POST" : "GET"),
    headers: init?.body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  const text = await r.text();
  const data = text ? JSON.parse(text) : null;
  if (!r.ok) throw new Error(typeof data?.detail === "string" ? data.detail : JSON.stringify(data?.detail ?? r.statusText));
  return data as T;
}

export const inr = (v: string | number | null | undefined, dp = 2) =>
  v === null || v === undefined ? "—" :
  "₹" + new Intl.NumberFormat("en-IN", { minimumFractionDigits: dp, maximumFractionDigits: dp }).format(Number(v));
