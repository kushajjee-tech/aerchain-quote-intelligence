// Route, blocker-logic and "never a false zero" tests. fetch is stubbed with a tiny fixture shaped like the API.
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { outcome } from "../pages/Review";

const ctx = { rfx_id: 1, title: "Test RFx", status: "sent", origin: "SEEDED_FALLBACK", kind: "primary", demo: true,
  meta: { code: "PUNE-PKG-2026", buyer: "Buyer Org", buyer_name: "A Buyer", category: "Corrugated packaging", currency: "INR" } };
const f = (o: any) => ({ id: o.id, kind: "cells", severity: "warning", category: "Commercial terms", vendor_id: 2, vendor: "Beta Boxes", vendor_key: "V2",
  title: "t", statement: null, requirement: null, concern: "c", lines: [], source: null, confidence: null, target: "/review", review: { state: "open" }, ...o });
const findings = [
  f({ id: "b1", kind: "eligibility", severity: "blocker", title: "CP-01: Failed", vendor_id: 2, category: "Commercial terms" }),
  f({ id: "m1", kind: "missing", title: "Not quoted: 1 of 2 lines", vendor_id: 1, vendor: "Alpha Kraft", vendor_key: "V1", lines: [2] }),
];
const vendors = [
  { vendor_id: 1, key: "V1", name: "Alpha Kraft", email: "a@x", state: "Received", messages: 1, quoted_lines: 1, lines: 2, coverage_pct: 50, quality: "Passed", commercial: "Passed", blockers: 0, exceptions: 1, last_activity: null },
  { vendor_id: 2, key: "V2", name: "Beta Boxes", email: "b@x", state: "Received", messages: 1, quoted_lines: 2, lines: 2, coverage_pct: 100, quality: "Passed", commercial: "Failed", blockers: 1, exceptions: 1, last_activity: null },
];
const overview = { rfx: ctx, metrics: { vendors_invited: 2, vendors_responded: 2, skus: 2, annual_demand: 3000, open_blockers: 1, findings: 2 }, findings, vendors,
  stages: [{ key: "issued", label: "RFx issued", route: "/copilot", state: "done", detail: "sent" }], activity: [], provisional: false };
const cell = (o: any) => ({ value: null, status: "VERIFIED", reasons: [], flags: [], freight_basis: "INCLUDED", quoted: null, ...o });
const comparison = { rfx_id: 1, title: "Test RFx", basis: "unit", provisional: false, vendors: [
  { vendor_id: 1, name: "Alpha Kraft", state: "RESPONDED", eligibility: { quality: "Passed", commercial: "Passed" }, documents: [] },
  { vendor_id: 2, name: "Beta Boxes", state: "RESPONDED", eligibility: { quality: "Passed", commercial: "Failed" }, documents: [] }],
  rows: [
    { line_no: 1, sku_code: "PK-1", description: "Box one", item_type: "RSC", ply: 3, flute: "B", dims_mm: null, gsm: [], printing: null, food_contact: false, annual_qty: 1000,
      best_vendor_id: 2, baseline: null, best_vs_baseline_pct: null,
      cells: { 1: cell({ value: "9.5000" }), 2: cell({ value: "8.2500" }) } },
    { line_no: 2, sku_code: "PK-2", description: "Box two", item_type: "RSC", ply: 3, flute: "B", dims_mm: null, gsm: [], printing: null, food_contact: false, annual_qty: 2000,
      best_vendor_id: null, baseline: null, best_vs_baseline_pct: null,
      cells: { 1: cell({ status: "MISSING" }), 2: cell({ status: "UNRESOLVED", value: null }) } }],
  vendor_summary: [{ vendor_id: 1, name: "Alpha Kraft", lines: 2, quoted: 1, not_quoted: 1, comparable: 1, exceptions: 0, comparable_spend_inr: "9500", complete_total_inr: null },
    { vendor_id: 2, name: "Beta Boxes", lines: 2, quoted: 2, not_quoted: 0, comparable: 1, exceptions: 1, comparable_spend_inr: "16500", complete_total_inr: null }] };
const scenario = { scenario_id: 7, tie_break: "lower price", total_annual_spend_inr: "8250", awards: [
  { line_no: 1, sku: "PK-1", vendor_id: 2, vendor: "Beta Boxes", price_on_basis_inr: "8.25", price_kind: "unit", status: "VERIFIED", annual_qty: 1000, annual_spend_inr: "8250", freight_status: "OK", eligibility: "Passed" }],
  uncovered_lines: [{ line_no: 2, sku: "PK-2" }], per_vendor_spend_inr: { "Beta Boxes": "8250" }, per_vendor_share_pct: { "Beta Boxes": "100.0" },
  ineligible_vendors: { failed: [], unverified: [] }, freight_dependent_lines: [], savings: null };

function route(url: string): any {
  const u = url.replace(/^\/api/, "").split("?")[0];
  if (u === "/rfx") return [ctx];
  if (u === "/rfx/1/overview") return overview;
  if (u === "/rfx/1/comparison") return comparison;
  if (u === "/rfx/1/scenarios") return scenario;
  if (u === "/scenarios/7/readiness") return { items: [], can_acknowledge: true };
  if (/\/eligibility$/.test(u)) return { configured: false, note: "No questionnaire" };
  if (/\/(messages|documents|audit)$/.test(u)) return [];
  if (u === "/rfx/1") return { rfx_id: 1, title: "Test RFx", status: "sent", label: "Seeded", patches: [], terms: [], questions: [], conformance: null };
  if (u === "/settings/fx") return {};
  if (u === "/settings/constants") return [];
  if (u === "/analyst/ask") return { answer_id: 1, session_id: "s1", narrative: "Alpha Kraft did not quote line 2.", tables: [], charts: [], caveats: {}, tool_calls: [], results: [] };
  throw new Error("unmocked " + u);
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: any) => { calls.push({ url, body: init?.body }); return new Response(JSON.stringify(route(url)), { status: 200 }); }));
  calls.length = 0;
  try { localStorage.clear(); } catch { /* ignore */ }
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const calls: { url: string; body?: string }[] = [];
const at = (path: string) => render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>);

describe("every primary route renders", () => {
  it.each([
    ["/", "Pune Packaging RFx"], ["/copilot", "Co-pilot"], ["/vendors", "Vendors & Inbox"], ["/vendors/1", "Alpha Kraft"],
    ["/review", "Review"], ["/comparison", "Comparison"], ["/analyst", "Analyst"], ["/award", "Award recommendation"], ["/settings", "Settings"],
  ])("%s", async (path, heading) => {
    at(path);
    expect(await screen.findByRole("heading", { level: 1, name: heading })).toBeTruthy();
  });
});

describe("blocker logic", () => {
  it("classifies blockers as fail and missing evidence as not provided", () => {
    expect(outcome(findings[0] as any)).toBe("fail");
    expect(outcome(findings[1] as any)).toBe("not_provided");
  });
  it("shows the open blocker count in the sidebar and on Home", async () => {
    at("/");
    expect(await screen.findByLabelText("1 open blockers")).toBeTruthy();
    expect(screen.getByText("1 open")).toBeTruthy();
  });
  it("locks Save recommendation while an open blocker affects the allocation", async () => {
    at("/award");
    await screen.findByText(/open blocker affect/);
    const save = screen.getByRole("button", { name: /Save recommendation/ }) as HTMLButtonElement;
    expect(save.disabled).toBe(true);
  });
});

describe("normalisation display", () => {
  it("never renders a zero for unquoted or unresolved cells", async () => {
    at("/comparison");
    await screen.findByText("PK-2");
    expect(screen.getAllByText("Not quoted").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Unresolved").length).toBeGreaterThan(0);
    expect(screen.queryByText(/₹0\.00/)).toBeNull();
    expect(screen.getByText("Lowest")).toBeTruthy();                        // best comparable price is labelled in words
    await waitFor(() => expect(screen.getByText("Not available")).toBeTruthy()); // no complete supplier → no total
  });
});

describe("assistant on every screen", () => {
  it("opens from any page and sends the screen context with the question", async () => {
    at("/vendors/1");
    fireEvent.click(await screen.findByRole("button", { name: /Open the RFx assistant/ }));
    fireEvent.click(await screen.findByText("What is missing or unresolved for Alpha Kraft?"));
    expect(await screen.findByText("Alpha Kraft did not quote line 2.")).toBeTruthy();
    const ask = calls.find((c) => c.url.endsWith("/analyst/ask"))!;
    const q = JSON.parse(ask.body!).question as string;
    expect(q).toMatch(/^What is missing or unresolved for Alpha Kraft\?/);
    expect(q).toContain("supplier V1 Alpha Kraft");
    expect(screen.getByRole("button", { name: /Line 2/ })).toBeTruthy();       // answer links back into the app
  });
  it("is not duplicated on the Co-pilot page, which shows the same thread full-size", async () => {
    at("/copilot");
    await screen.findByRole("heading", { level: 1, name: "Co-pilot" });
    expect(screen.queryByRole("button", { name: /Open the RFx assistant/ })).toBeNull();
  });
});

describe("product walkthrough", () => {
  it("starts from the top bar, moves forward and back, and can be ended at any time", async () => {
    at("/vendors");
    fireEvent.click(await screen.findByRole("button", { name: /Take the tour/ }));
    expect(await screen.findByText("Start here: the command centre")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(await screen.findByText("Supplier replies")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Back" }));
    expect(await screen.findByText("Start here: the command centre")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "End the walkthrough" }));
    expect(screen.queryByRole("dialog", { name: "Product walkthrough" })).toBeNull();
  });
});
