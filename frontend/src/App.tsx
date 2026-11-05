import { useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import Analyst from "./pages/Analyst";
import Award from "./pages/Award";
import Comparison from "./pages/Comparison";
import Copilot from "./pages/Copilot";
import Settings from "./pages/Settings";
import Review from "./pages/Review";
import Vendors from "./pages/Vendors";
import { RfxContext } from "./rfx";

const BUILT: Record<string, JSX.Element> = { "/comparison": <Comparison />, "/review": <Review />, "/vendors": <Vendors />, "/award": <Award />, "/analyst": <Analyst />, "/copilot": <Copilot />, "/settings": <Settings /> };

// M0 shell: one route per screen in architecture §4. Screens are filled in by later milestones.
const SCREENS: { path: string; label: string; milestone: string }[] = [
  { path: "/copilot", label: "Co-pilot", milestone: "M6" },
  { path: "/vendors", label: "Vendors & Inbox", milestone: "M6" },
  { path: "/review", label: "Review", milestone: "M5" },
  { path: "/comparison", label: "Comparison", milestone: "M5" },
  { path: "/analyst", label: "Analyst", milestone: "M8" },
  { path: "/award", label: "Award", milestone: "M7/M9" },
  { path: "/settings", label: "Settings", milestone: "M5" },
];

function Placeholder({ label, milestone }: { label: string; milestone: string }) {
  return (
    <section>
      <h2>{label}</h2>
      <p>Not built yet (planned in {milestone}).</p>
    </section>
  );
}

export default function App() {
  const [rfxId, setRfxId] = useState(1);
  return (
    <RfxContext.Provider value={{ rfxId, setRfxId }}>
    <div style={{ fontFamily: "system-ui, sans-serif", display: "flex", gap: 24, padding: 16 }}>
      <nav style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 160 }}>
        <strong>Quote Intelligence</strong>
        <label style={{ fontSize: 12 }}>RFx #<input type="number" value={rfxId} onChange={(e) => setRfxId(Number(e.target.value))} style={{ width: 50 }} /></label>
        {SCREENS.map((s) => (
          <NavLink key={s.path} to={s.path}>{s.label}</NavLink>
        ))}
      </nav>
      <main style={{ flex: 1 }}>
        <Routes>
          <Route path="/" element={<Placeholder label="Home" milestone="M0" />} />
          {Object.entries(BUILT).map(([path, el]) => <Route key={path} path={path} element={el} />)}
          {SCREENS.filter((s) => !(s.path in BUILT)).map((s) => (
            <Route key={s.path} path={s.path} element={<Placeholder label={s.label} milestone={s.milestone} />} />
          ))}
        </Routes>
      </main>
    </div>
    </RfxContext.Provider>
  );
}
