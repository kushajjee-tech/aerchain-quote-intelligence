import { Route, Routes } from "react-router-dom";
import Analyst from "./pages/Analyst";
import Award from "./pages/Award";
import Comparison from "./pages/Comparison";
import Copilot from "./pages/Copilot";
import Home from "./pages/Home";
import Review from "./pages/Review";
import Settings from "./pages/Settings";
import VendorDetail from "./pages/VendorDetail";
import Vendors from "./pages/Vendors";
import { RfxProvider, useRfx } from "./rfx";
import Shell from "./Shell";
import { AssistantProvider } from "./assistant";
import { TourProvider } from "./tour";
import { EmptyState, ErrorState, Skeleton } from "./ui";
import { Link } from "react-router-dom";

function Gate({ children }: { children: JSX.Element }) {
  const { rfxId, list, overview, error, refresh } = useRfx();
  if (error && !overview) return <ErrorState error={`Could not load the RFx: ${error}. Is the backend running (make start)?`} onRetry={refresh} />;
  if (!list.length || !rfxId) return list.length === 0 && !error ? <Skeleton rows={6} /> : <EmptyState title="No RFx yet">Create one in the Co-pilot.</EmptyState>;
  if (!overview) return <Skeleton rows={8} />;
  return children;
}

export default function App() {
  return (
    <RfxProvider>
      <AssistantProvider>
      <TourProvider>
      <Shell>
        <Routes>
          <Route path="/" element={<Gate><Home /></Gate>} />
          <Route path="/copilot" element={<Gate><Copilot /></Gate>} />
          <Route path="/vendors" element={<Gate><Vendors /></Gate>} />
          <Route path="/vendors/:vendorId" element={<Gate><VendorDetail /></Gate>} />
          <Route path="/review" element={<Gate><Review /></Gate>} />
          <Route path="/comparison" element={<Gate><Comparison /></Gate>} />
          <Route path="/analyst" element={<Gate><Analyst /></Gate>} />
          <Route path="/award" element={<Gate><Award /></Gate>} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<EmptyState title="Page not found"><Link to="/">Go to Home</Link></EmptyState>} />
        </Routes>
      </Shell>
      </TourProvider>
      </AssistantProvider>
    </RfxProvider>
  );
}
