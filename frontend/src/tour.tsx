// Product walkthrough: six plain-English steps. Each step opens its screen and highlights the main area.
// It never blocks the page (no overlay), it can be skipped at any time, and it makes no AI calls.
import { createContext, ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, X } from "lucide-react";
import { Button } from "./ui";

export type Step = { route: string; title: string; body: string; target?: string };

export const STEPS: Step[] = [
  { route: "/", title: "Start here: the command centre",
    body: "This is one tender for 30 packaging items from 5 suppliers. The top row shows where things stand. \"Needs your attention\" lists what must be decided before an award.",
    target: ".grid.g4" },
  { route: "/vendors", title: "Supplier replies",
    body: "Each supplier's emails and files, kept exactly as they were received. Click a supplier to see its inbox, documents and prices. You can also upload a new response.",
    target: "table.t" },
  { route: "/review", title: "Decisions to make",
    body: "Each finding is something the system could not settle on its own, such as an expired certificate or a price it can't read. Pick one to see the evidence and record your decision. Every decision is logged.",
    target: "table.t" },
  { route: "/comparison", title: "One side-by-side grid",
    body: "Every supplier's price for every item, converted to ₹ per box before tax. The supplier's own figure sits beside the converted one. Click any price to see exactly where it came from.",
    target: "table.t" },
  { route: "/analyst", title: "Ask questions in plain English",
    body: "Click \"Ask AI\" at the bottom right and ask anything, for example \"Which suppliers cleared the quality questionnaire?\" The AI writes the answer, but every number comes from a calculation and is checked.",
    target: ".assistant-fab" },
  { route: "/award", title: "The recommendation",
    body: "The cheapest qualified supplier for each item, with the reasons. Saving is blocked while an open issue affects the award, and saving needs a reason. Nothing is ordered automatically.",
    target: "table.t" },
];

type Ctx = { start: () => void };
const TourCtx = createContext<Ctx>({ start: () => {} });
export const useTour = () => useContext(TourCtx);

export function TourProvider({ children }: { children: ReactNode }) {
  const [index, setIndex] = useState<number | null>(null);
  const start = useCallback(() => setIndex(0), []);
  return (
    <TourCtx.Provider value={{ start }}>
      {children}
      <TourCard index={index} setIndex={setIndex} />
    </TourCtx.Provider>
  );
}

function TourCard({ index, setIndex }: { index: number | null; setIndex: (i: number | null) => void }) {
  const nav = useNavigate();
  const [missing, setMissing] = useState(false);
  const step = index === null ? null : STEPS[index];
  const next = () => (index === null ? undefined : index < STEPS.length - 1 ? setIndex(index + 1) : setIndex(null));
  const back = () => index !== null && index > 0 && setIndex(index - 1);

  // Open the step's screen, then highlight its target once the data has loaded (the page shows skeletons first).
  useEffect(() => {
    if (!step) return;
    nav(step.route);
    setMissing(false);
    if (!step.target) return;
    const selector = step.target;
    let tries = 0;
    const timer = window.setInterval(() => {
      tries += 1;
      const el = document.querySelector(selector);
      if (el || tries > 40) {
        window.clearInterval(timer);
        if (el) {
          el.classList.add("tour-target");
          el.scrollIntoView({ block: "center", behavior: "smooth" });
        } else setMissing(true);
      }
    }, 100);
    return () => {
      window.clearInterval(timer);
      document.querySelectorAll(".tour-target").forEach((e) => e.classList.remove("tour-target"));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index]);

  // Keyboard: Esc ends, arrows move (but not while typing in a box).
  useEffect(() => {
    if (index === null) return;
    const k = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLElement && /INPUT|TEXTAREA|SELECT/.test(e.target.tagName);
      if (e.key === "Escape") setIndex(null);
      else if (!typing && e.key === "ArrowRight") next();
      else if (!typing && e.key === "ArrowLeft") back();
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index]);

  if (index === null || !step) return null;
  const last = index === STEPS.length - 1;
  return (
    <aside className="tour-card" role="dialog" aria-label="Product walkthrough" aria-live="polite">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <span className="tour-count">Step {index + 1} of {STEPS.length}</span>
        <button className="icon-btn" aria-label="End the walkthrough" onClick={() => setIndex(null)}><X size={16} /></button>
      </div>
      <h3 className="tour-title">{step.title}</h3>
      <p className="tour-body">{step.body}</p>
      {missing && <p className="subtle">Nothing to highlight on this screen yet. The data may still be loading.</p>}
      <div className="tour-dots" aria-hidden>{STEPS.map((_, i) => <span key={i} className={i === index ? "on" : ""} />)}</div>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <Button variant="ghost" size="sm" onClick={back} disabled={index === 0} icon={<ArrowLeft size={14} />}>Back</Button>
        <Button variant="primary" size="sm" onClick={next}>{last ? "Finish" : "Next"}{!last && <ArrowRight size={14} />}</Button>
      </div>
    </aside>
  );
}
