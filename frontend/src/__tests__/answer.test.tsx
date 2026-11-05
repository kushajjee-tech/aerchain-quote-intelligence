// Answer rendering: direct answer first, short points, one chosen table, clickable follow-up, details folded away.
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Answer, parseNarrative } from "../components/Answer";

afterEach(cleanup);
const a = {
  answer_id: 9, grounded: true, banner: null, interpretation_note: "query over approved read-only views", caveats: {}, exclusions: [], tool_calls: [],
  narrative: "**Four of five** ISO 9001 certificates are valid today.\n- Malwa's certificate expired on 2026-09-28.\n- Shivam's names a different company.\nNext: Which suppliers are eligible for the award?",
  display_table: 1, charts: [],
  tables: [{ source: "query", columns: ["vendor_id", "vendor"], rows: [{ vendor_id: 1, vendor: "Hidden" }] },
           { source: "query", columns: ["vendor_id", "vendor", "valid_today"], rows: [{ vendor_id: 3, vendor: "Malwa Corrugators", valid_today: 0 }] }],
};

describe("answer layout", () => {
  it("parses lead, bullets, next and legacy markdown tables", () => {
    const b = parseNarrative("Lead.\n| A | B |\n|---|---|\n| 1 | 2 |\n- point\nNext: ask more");
    expect(b.map((x) => x.kind)).toEqual(["p", "table", "bullet", "next"]);
    expect(b[1].rows).toEqual([["A", "B"], ["1", "2"]]);
  });
  it("shows only the chosen table, readable, with a clickable follow-up", () => {
    const onAsk = vi.fn();
    render(<MemoryRouter><Answer a={a} compact onAsk={onAsk} /></MemoryRouter>);
    expect(screen.getByText("Four of five").tagName).toBe("B");
    expect(screen.getByText("Malwa Corrugators")).toBeTruthy();
    expect(screen.getByText("No")).toBeTruthy();                       // 0 → "No", ids hidden
    expect(screen.queryByText("Hidden")).toBeNull();                     // other results stay folded
    expect(screen.queryByText("vendor id")).toBeNull();
    fireEvent.click(screen.getByText("Which suppliers are eligible for the award?"));
    expect(onAsk).toHaveBeenCalledWith("Which suppliers are eligible for the award?");
    fireEvent.click(screen.getByText(/Sources & details/));
    expect(screen.getByText(/Result 1: query/)).toBeTruthy();
  });
});
