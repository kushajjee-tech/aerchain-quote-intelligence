// The RFx assistant, available on every screen. One conversation per RFx, shared by the side panel and the Co-pilot page.
// Each question carries what the buyer is looking at (page + selected supplier / line / finding), so "why is this
// unresolved?" works without naming it. Numbers in answers come from analyst tool results, never from the model.
import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { ArrowUp, Bot, Mic, MicOff, Minimize2, RotateCcw, Sparkles, User, Volume2, VolumeX } from "lucide-react";
import { api } from "./api";
import { Answer } from "./components/Answer";
import { useRfx } from "./rfx";
import { Badge, Button, EmptyState, ErrorState } from "./ui";

export type Turn = { q: string; context?: string; a?: any; err?: string };
export type Scope = { label: string; context?: string; prompts: string[] };

const PAGE: Record<string, Scope> = {
  "/": { label: "Home · RFx overview", prompts: ["Summarize the supplier responses and key exceptions.", "What is blocking an award decision right now?", "Which suppliers have quality-document gaps?"] },
  "/vendors": { label: "Vendors & Inbox", prompts: ["Compare quote coverage and open issues across suppliers.", "Who didn't quote everything, and what does that do to the ranking?"] },
  "/review": { label: "Review", prompts: ["Which suppliers cleared the quality questionnaire, and why didn't the others?", "Whose ISO 9001 certificate is valid, and until when?"] },
  "/comparison": { label: "Comparison", prompts: ["Show unit price per box by vendor for lines 1 to 6 as a chart.", "Which lines have the widest price spread between qualified suppliers?"] },
  "/analyst": { label: "Analyst", prompts: ["How much of the saving depends on assumptions, such as FX, reference weights, freight or last year's prices?", "What if we split it cheapest per line, but only among vendors who cleared the quality questionnaire?"] },
  "/award": { label: "Award", prompts: ["Which awarded lines depend on unknown freight, and what is the break-even?", "What changes if we exclude Sahyadri Paper Mills?"] },
  "/settings": { label: "Settings", prompts: ["Which FX rate is used, and which prices depend on it?"] },
  "/copilot": { label: "Co-pilot", prompts: ["Summarize the supplier responses and key exceptions.", "Which suppliers have quality-document gaps?", "Compare the delivered cost for SKU PK-C101.", "Draft clarification questions for V5."] },
};

type Ctx = {
  turns: Turn[]; busy: boolean; ask: (q: string) => void; retry: (i: number) => void; reset: () => void;
  open: boolean; setOpen: (o: boolean) => void; scope: Scope; setDetail: (s: Scope | null) => void;
  useContextInQuestion: boolean; setUseContext: (b: boolean) => void;
};
const AssistantCtx = createContext<Ctx>(null as unknown as Ctx);
export const useAssistant = () => useContext(AssistantCtx);

/** Pages call this to tell the assistant what is selected (supplier, line, finding). Cleared on unmount. */
export function useAssistantScope(scope: Scope | null) {
  const { setDetail } = useAssistant();
  const key = scope ? `${scope.label}|${scope.context}` : "";
  useEffect(() => { setDetail(scope); return () => setDetail(null); }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
}

const store = (rfx: number) => `qi.chat.${rfx}`;
function load(rfx: number): { turns: Turn[]; session: string | null } {
  try { const v = JSON.parse(localStorage.getItem(store(rfx)) ?? "null"); if (v?.turns) return v; } catch { /* storage unavailable */ }
  return { turns: [], session: null };
}

export function AssistantProvider({ children }: { children: ReactNode }) {
  const { rfxId } = useRfx();
  const { pathname } = useLocation();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [session, setSession] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<Scope | null>(null);
  const [useContextInQuestion, setUseContext] = useState(true);
  useEffect(() => { const s = load(rfxId); setTurns(s.turns); setSession(s.session); }, [rfxId]);
  useEffect(() => {
    if (!rfxId) return;
    try { localStorage.setItem(store(rfxId), JSON.stringify({ turns: turns.filter((t) => t.a || t.err).slice(-30), session })); } catch { /* ignore */ }
  }, [turns, session, rfxId]);
  useEffect(() => { setUseContext(true); }, [pathname, detail?.context]);

  const base = PAGE["/" + (pathname.split("/")[1] ?? "")] ?? PAGE["/"];
  const scope: Scope = detail ? { label: detail.label, context: detail.context, prompts: [...detail.prompts, ...base.prompts].slice(0, 4) } : base;

  const ask = useCallback(async (q: string, ctxOverride?: string | null) => {
    if (!q.trim() || busy || !rfxId) return;
    const onCopilot = pathname.startsWith("/copilot");
    const context = ctxOverride !== undefined ? ctxOverride ?? undefined
      : (useContextInQuestion && !onCopilot ? scope.context ?? `The buyer is on the ${scope.label} screen.` : undefined);
    const question = context ? `${q}\n\n[Screen context, for reference only: ${context}]` : q;
    setBusy(true); setTurns((t) => [...t, { q, context }]);
    try {
      const a = await api("/analyst/ask", { body: { rfx_id: rfxId, question, session_id: session } });
      setSession(a.session_id); setTurns((t) => t.map((x, i) => i === t.length - 1 ? { ...x, a } : x));
    } catch (e) { setTurns((t) => t.map((x, i) => i === t.length - 1 ? { ...x, err: String(e).replace(/^Error: /, "") } : x)); }
    finally { setBusy(false); }
  }, [busy, rfxId, session, scope.context, scope.label, useContextInQuestion, pathname]);
  const retry = (i: number) => { const t = turns[i]; setTurns((ts) => ts.filter((_, k) => k !== i)); setTimeout(() => ask(t.q, t.context ?? null), 0); };
  const reset = () => { setTurns([]); setSession(null); };
  return <AssistantCtx.Provider value={{ turns, busy, ask: (q) => ask(q), retry, reset, open, setOpen, scope, setDetail, useContextInQuestion, setUseContext }}>{children}</AssistantCtx.Provider>;
}

// ---- voice (browser speech recognition; optional) ----
type SR = { start: () => void; stop: () => void; lang: string; interimResults: boolean; continuous: boolean;
  onresult: ((e: any) => void) | null; onend: (() => void) | null; onerror: ((e: any) => void) | null };
function useSpeech(onText: (t: string) => void) {
  const Ctor = (typeof window !== "undefined" ? (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition : null) as (new () => SR) | null;
  const [listening, setListening] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const rec = useRef<SR | null>(null);
  const toggle = () => {
    if (!Ctor) return;
    if (listening) { rec.current?.stop(); return; }
    const r = new Ctor(); r.lang = "en-IN"; r.interimResults = true; r.continuous = false;
    r.onresult = (e: any) => onText(Array.from(e.results).map((x: any) => x[0].transcript).join(""));
    r.onend = () => setListening(false);
    r.onerror = (e: any) => { setErr(e.error === "not-allowed" ? "Microphone permission was denied." : `Voice input failed (${e.error}).`); setListening(false); };
    rec.current = r; setErr(null); setListening(true); r.start();
  };
  return { supported: !!Ctor, listening, toggle, err };
}

function speak(text: string) {
  try { window.speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(text.slice(0, 1200)); u.lang = "en-IN"; window.speechSynthesis.speak(u); } catch { /* unsupported */ }
}

export function ChatThread({ compact }: { compact?: boolean }) {
  const { turns, busy, ask, retry, scope, useContextInQuestion, setUseContext } = useAssistant();
  const [q, setQ] = useState("");
  const [readAloud, setReadAloud] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const voice = useSpeech(setQ);
  const lastAnswered = useRef(0);
  useEffect(() => { if (turns.length) end.current?.scrollIntoView?.({ behavior: "smooth", block: "end" }); }, [turns, busy]);
  useEffect(() => {
    const done = turns.filter((t) => t.a).length;
    if (readAloud && done > lastAnswered.current) { const a = [...turns].reverse().find((t) => t.a)?.a; if (a?.narrative) speak(a.narrative); }
    lastAnswered.current = done;
  }, [turns, readAloud]);
  const send = (text: string) => { ask(text); setQ(""); };
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <div className="chat" style={{ flex: 1, overflow: "auto", padding: compact ? 14 : 20, minHeight: 0 }}>
        {turns.length === 0 && (
          <EmptyState icon={<Sparkles size={22} />} title="Ask about this RFx">
            Answers use the normalised comparison, eligibility results and documents. The model writes the words; every number comes from a calculation.
            <div className="stack" style={{ gap: 8, alignItems: "center", marginTop: 14 }}>
              {scope.prompts.map((p) => <button key={p} className="prompt-chip" style={{ textAlign: "left" }} onClick={() => send(p)}>{p}</button>)}</div>
          </EmptyState>)}
        {turns.map((t, i) => (
          <div key={i} className="stack" style={{ gap: 10, marginBottom: 16 }}>
            <div className="msg-user"><User size={14} style={{ flex: "none", marginTop: 3 }} /><div>{t.q}
              {t.context && <div className="subtle" style={{ marginTop: 2 }}>Context: {t.context.replace(/^The buyer is (viewing|on) /, "")}</div>}</div></div>
            <div className="msg-ai"><Bot size={16} style={{ flex: "none", marginTop: 2 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                {!t.a && !t.err && <div className="row muted"><span className="spin" style={{ display: "inline-flex" }}><RotateCcw size={14} /></span> Working — querying the data and checking every number…</div>}
                {t.err && <ErrorState error={/unavailable|503|API key|credential/i.test(t.err) ? `The AI service is unavailable (${t.err}). Start the app with your API key using make start. Every other screen works without it.` : t.err} onRetry={() => retry(i)} />}
                {t.a && (t.a.narrative || t.a.tables?.length ? <Answer a={t.a} compact={compact} onAsk={send} /> : <EmptyState title="No result">The question did not match data in this RFx. Try naming a supplier, SKU or line.</EmptyState>)}
              </div></div>
          </div>))}
        <div ref={end} />
      </div>
      <div style={{ borderTop: "1px solid var(--border)", padding: 12 }}>
        {compact && <div className="row" style={{ marginBottom: 8, gap: 6, flexWrap: "wrap" }}>
          <label className="chip" style={{ cursor: "pointer" }} title="Send what you are looking at with the question">
            <input type="checkbox" checked={useContextInQuestion} onChange={(e) => setUseContext(e.target.checked)} /> Use this screen: {scope.label}</label>
          {turns.length > 0 && compact && scope.prompts.slice(0, 1).map((p) => <button key={p} className="prompt-chip" onClick={() => send(p)}>{p.length > 46 ? p.slice(0, 44) + "…" : p}</button>)}
        </div>}
        <div className="row" style={{ alignItems: "flex-end" }}>
          <textarea className="textarea" style={{ height: 44, flex: 1, resize: "none" }} value={q} placeholder={voice.listening ? "Listening…" : "Ask about suppliers, SKUs, prices, documents…"} aria-label="Question"
            onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(q); } }} />
          {voice.supported && <button className={`icon-btn ${voice.listening ? "listening" : ""}`} aria-label={voice.listening ? "Stop voice input" : "Speak your question"} onClick={voice.toggle}
            title="Voice input uses your browser's speech recognition (in Chrome, audio is processed by Google). Review the text before sending.">{voice.listening ? <MicOff size={17} /> : <Mic size={17} />}</button>}
          <button className="icon-btn" aria-label={readAloud ? "Stop reading answers aloud" : "Read answers aloud"} onClick={() => { if (readAloud) window.speechSynthesis?.cancel(); setReadAloud(!readAloud); }}
            title={readAloud ? "Reading answers aloud" : "Read answers aloud"}>{readAloud ? <Volume2 size={17} /> : <VolumeX size={17} />}</button>
          <Button variant="primary" onClick={() => send(q)} disabled={!q.trim()} loading={busy} icon={<ArrowUp size={15} />}>Ask</Button>
        </div>
        {voice.err && <div className="subtle" style={{ color: "var(--critical)", marginTop: 6 }}>{voice.err}</div>}
      </div>
    </div>
  );
}

export function AssistantPanel() {
  const { open, setOpen, turns, reset, busy } = useAssistant();
  const { pathname } = useLocation();
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "j") { e.preventDefault(); setOpen(!open); }
      else if (e.key === "Escape" && open && !document.querySelector(".drawer")) setOpen(false);
    };
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  }, [open, setOpen]);
  const onCopilot = pathname.startsWith("/copilot");
  const answered = useMemo(() => turns.filter((t) => t.a).length, [turns]);
  if (onCopilot) return null;  // the Co-pilot page shows the same conversation full-size
  return (<>
    {!open && <button className="assistant-fab" onClick={() => setOpen(true)} aria-label="Open the RFx assistant (Ctrl/Cmd+J)">
      <Sparkles size={17} />Ask AI{busy && <span className="spin" style={{ display: "inline-flex" }}><RotateCcw size={13} /></span>}
      {!busy && answered > 0 && <span className="fab-count">{answered}</span>}</button>}
    {open && (
      <aside className="assistant-panel" role="complementary" aria-label="RFx assistant">
        <div className="drawer-h"><Sparkles size={17} color="var(--primary)" /><div style={{ flex: 1 }}><h3 style={{ fontSize: 15 }}>RFx assistant</h3>
          <div className="subtle">Same conversation as the Co-pilot page · Ctrl/Cmd+J</div></div>
          {turns.length > 0 && <button className="icon-btn" aria-label="New conversation" title="New conversation" onClick={reset}><RotateCcw size={16} /></button>}
          <button className="icon-btn" aria-label="Minimise assistant" onClick={() => setOpen(false)}><Minimize2 size={16} /></button>
        </div>
        <div style={{ flex: 1, minHeight: 0 }}><ChatThread compact /></div>
        <div className="subtle" style={{ padding: "6px 14px 10px", borderTop: "1px solid var(--border)" }}>
          <Badge tone="outline">Analysis, not a decision</Badge> The assistant never saves awards or dismisses findings; you do.</div>
      </aside>)}
  </>);
}
