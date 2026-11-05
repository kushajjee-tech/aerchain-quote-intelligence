// RFx context: the list of RFxs, the selected one (persisted per browser), and its overview (findings, vendors,
// stages, activity), which most pages and the shell read. Every number comes from the backend.
import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { api } from "./api";

export type RfxMeta = { code?: string; buyer?: string; buyer_name?: string; category?: string; plant?: string; currency?: string };
export type RfxCtx = { rfx_id: number; title: string; scope?: string | null; status: string; origin: string; kind: string; meta: RfxMeta; demo: boolean };
export type Finding = {
  id: string; kind: string; severity: "blocker" | "warning" | "info"; category: string; vendor_id: number | null; vendor: string | null;
  vendor_key: string | null; title: string; statement: string | null; requirement: string | null; concern: string; lines: number[];
  source: any; confidence: string | null; target: string; review: { state: string; comment?: string; actor?: string; at?: string };
};
export type VendorRow = { vendor_id: number; key: string; name: string; email: string | null; state: string; messages: number;
  quoted_lines: number; lines: number; coverage_pct: number; quality: string | null; commercial: string | null; blockers: number;
  exceptions: number; last_activity: string | null };
export type Overview = { rfx: RfxCtx; metrics: Record<string, number>; findings: Finding[]; vendors: VendorRow[];
  stages: { key: string; label: string; route: string; state: string; detail: string }[];
  activity: { id: number; at: string; actor: string; action: string; text: string }[]; provisional: boolean };

const KEY = "qi.rfx";
type Ctx = { rfxId: number; setRfxId: (n: number) => void; list: RfxCtx[]; overview: Overview | null; error: string | null;
  refresh: () => Promise<void>; reloadList: () => Promise<void> };
export const RfxContext = createContext<Ctx>(null as unknown as Ctx);
export const useRfx = () => useContext(RfxContext);
export const OPEN = ["open", "confirmed", "clarification_requested"];

export function RfxProvider({ children }: { children: ReactNode }) {
  const [list, setList] = useState<RfxCtx[]>([]);
  const [rfxId, setId] = useState<number>(() => { try { return Number(localStorage.getItem(KEY)) || 0; } catch { return 0; } });
  const [overview, setOverview] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reloadList = useCallback(async () => {
    try {
      const l = await api<RfxCtx[]>("/rfx");
      setList(l);
      setId((cur) => (l.some((r) => r.rfx_id === cur) ? cur : l.find((r) => r.kind === "primary")?.rfx_id ?? l[0]?.rfx_id ?? 0));
      setError(null);
    } catch (e) { setError(String(e)); }
  }, []);
  useEffect(() => { reloadList(); }, [reloadList]);

  const refresh = useCallback(async () => {
    if (!rfxId) return;
    try { setOverview(await api<Overview>(`/rfx/${rfxId}/overview`)); setError(null); }
    catch (e) { setError(String(e)); }
  }, [rfxId]);
  useEffect(() => { setOverview(null); refresh(); }, [refresh]);

  const setRfxId = (n: number) => { setId(n); try { localStorage.setItem(KEY, String(n)); } catch { /* storage unavailable */ } };
  return <RfxContext.Provider value={{ rfxId, setRfxId, list, overview, error, refresh, reloadList }}>{children}</RfxContext.Provider>;
}
