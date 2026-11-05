# 10 — Demo Runbook

**Start:** `make start` → http://localhost:5173. **Prepare once before a demo (live model):** `make demo-prepare`. Requires `.env` with `ANTHROPIC_API_KEY` and API credit.
**Status:** v1.2 · updated for PM-review decisions DL-25…DL-32
**Canonical requirements:** `docs/00_source_of_truth.md` (IDs cited below) · **Spec:** `docs/02_PRD.md` v1.5 · **Tests:** `docs/04_implementation_plan.md` v1.7 §3a
**Locked decisions honoured:** all of DL-1…DL-32. DL-17 (separate sandbox) is preserved: the sandbox is still used for the panel's free-form drafting, while the primary RFx is created live under DL-19.

---

## 0. Honesty statement (said out loud at the start of the demo)
1. **What is pre-authored:** the five vendor responses were written in advance against the **canonical RFx specification**, because nine days of vendor replies can't happen in an hour (SOT EX-02). This is the only pre-authored part, and it is the vendor side.
2. **What is live:** RFx drafting by the co-pilot, extraction of every response, all checks, normalisation, the comparison, every analyst answer and the award. That covers SOT AI-01…AI-06.
3. **Stub:** email transport is simulated (SOT PERM-05).
4. **Warm results:** pre-run results exist **only as an outage fallback** (§6). In the primary flow, extraction runs live in front of the panel.

---

## 1. Pre-flight (T−30 min)
| Step | Check | Pass condition |
|---|---|---|
| 1 | `make doctor` | Tesseract and dependencies OK |
| 2 | `make reset` | DB restored. Inbox holds 5 `.eml` files. The buyer brief pack and canonical spec are present. |
| 3 | Canonical spec hash | Equals the hash recorded in the M1 dataset report |
| 4 | Model API smoke call | Structured call succeeds and is logged |
| 5 | `make demo-warm` into a **separate** fallback snapshot | Snapshot stored, **not** loaded |
| 6 | Constant set | Active version shown, labels "not validated" (DL-18) |
| 7 | FX | USD rate, as-of date and source shown (DL-15) |

---

## 2. Primary flow — one RFx, start to finish (SOT REQ-01, REQ-03, FN-01…FN-16)
Target: about 25 minutes. Every step happens on **the same RFx record** (`origin = COPILOT_LIVE`).

| # | Stage | Action (presenter) | Expected system behaviour | Visible UI evidence | SOT |
|---|---|---|---|---|---|
| P1 | **Talk the RFx into existence** | Co-pilot → **Draft primary RFx live from the brief pack** | The co-pilot proposes the item-master column mapping (DL-27). The buyer confirms it and the 30 lines are imported deterministically. The co-pilot lists the open fields (scope, delivery location, dimension convention, validity, GST basis). | Mapping proposal → **Confirm and import rows** → 30 lines; open fields listed | FN-01, FN-02, AI-06 |
| P2 | Answer the co-pilot, then draft the questionnaire | Type: *"We are buying our 30 corrugated packaging SKUs for the next year. Deliver to the Chakan plant, Pune. All dimensions are internal. Quotes valid 90 days. Prices exclusive of GST."* → **Propose** → **Apply**. Then **Draft** (questionnaire and terms) → **Apply all** | Each answer quotes your words; anything not in your text or the policy is rejected. 8 questions and 3 terms, each cited to the checklist or policy; numbering by code | Proposed values with quotes; questions with "citation verified" | FN-01, FN-02 |
| P3 | **Conformance check** | **Conformance check** | Deterministic comparison of the drafted RFx with the canonical spec (SKUs, construction, quantities, questionnaire keys, sections, pass rules, response basis) | "Conforms to canonical spec", or the exact differences | REQ-03 (DL-19) |
| P4 | Approve and send | **Approve** → **Send to vendors** | RFx locked; one outbox message per vendor (5) | Header status "sent" | FN-03, PERM-05 |
| P5 | **Responses arrive over time** | **Deliver next response** ×5 (V5 email, V5 questionnaire, V1, V3, V4), then **Read responses**. Ask Q5 with V2 still awaiting. Then **Deliver next response** (V2) → **Read responses** again: only V2 is read. | Live extraction per vendor. Undelivered vendors show "Awaiting response" (no numbers, not Missing). | Vendor columns, Awaiting chips, Comparison | EX-02, FN-04, FN-05, AI-02 |
| P6 | Final comparison | (automatic after the last delivery) | Phase B cross-vendor checks run. Statuses, eligibility and review items are computed. | Banner turns *Final*. Grid 30 × 5. | FN-06…FN-10 |
| P7 | Review queue | Walk through the edge-case items (§3). Open one **decision-sensitive** item. Generate V4's and V5's **clarification packs** (DL-32), review them, approve them to the outbox. | Decision-sensitive items first, with quantified impact (DL-28), then money at risk. Each pack lists only that vendor's important vendor-resolvable items, by sensitivity. | Queue with sensitivity badges; pack preview → outbox | EVAL-02 |
| P8 | Compare and open documents | Basis toggle Unit → Landed → As quoted. Click a cell → provenance drawer: the cited text verbatim → **open <file>** opens the original. Vendors & Inbox: "Documents received" lists every file; certificates open from there. | Every number traces to its source text and original file | Drawer, documents list, eligibility panels | FN-06…FN-10, EVAL-02 |
| P9 | **Ask** | Ask the analyst questions (§4) | Grounded answers with interpretation, exclusions and caveats. Document facts are cited to their sources. | Answer blocks, Show work, source links | FN-11…FN-15, EX-04, AI-03…AI-05 |
| P10 | **Award** | Award screen → cheapest per line, quality strict (formal, **freight-aware**) → readiness → acknowledge → memo | NEEDS_REVIEW excluded by default (DL-16). **Lines that V5 wins only because its freight is unknown are FREIGHT_DEPENDENT, with break-even freight (DL-25).** The readiness check lists them, plus decision-sensitive lines and the **V2 FX** and **billed-weight** exposures (DL-28/30/31). Acknowledgement audited. | Scenario table with freight status and break-even per line; savings with coverage and lower-bound notes; readiness list; memo | FN-16, EVAL-03 |
| P11 | Export | Export the comparison xlsx and the memo | Files open. Every number has a Sources row. | Opened files | FN-15 |

---

## 3. Edge-case matrix (SC-01) — every assignment-named edge case
Column meanings: **Fixture** = the dataset item (PRD §11). **Workflow** = the primary-flow step. **Expected behaviour** = what the system does. **UI evidence** = what the panel sees. **Demo action / question** = what the presenter does or asks. **Test** = the named automated test (Plan §3a).

| SOT ID | Fixture | Workflow | Expected system behaviour | Visible UI evidence | Demo action / question | Test |
|---|---|---|---|---|---|---|
| **EDGE-01** Excel ignores template | V1 `.xlsx`: own layout, merged headers, extra columns, slabs, tooling row | P5, P8 | Layout-agnostic read. Lines matched by SKU/spec, not row order. Slab chosen by annual quantity. Tooling kept separate, not a line. | Inbox: the original sheet. Drawer on a V1 cell: `Sheet1!E14`, slab "10k–50k" chosen. Vendor panel: tooling term. | Open V1's original sheet → click line 12 in the grid → show the source cell and the slab step | T-EDGE-01 |
| **EDGE-02** PDF footnote discount | V2 letterhead PDF; footnote "\*5% trade discount on all items" | P5, P8 | Footnote extracted as `DocumentTerm(DISCOUNT_PCT 5, scope ALL)` and applied at step 5 of every in-scope V2 line | Drawer on a V2 cell: trace "−5% trade discount (p.2, footnote \*)" with the footnote highlighted on the PDF page | Open a V2 cell → show the trace step and the highlighted footnote | T-EDGE-02 |
| **EDGE-03** Word prose commercials | V3 `.docx`: payment, freight, validity, lead time and escalation in paragraphs | P5, P8, P9 | Each term extracted with sentence-level evidence. Freight basis drives V3's landed values. | V3 panel → Terms → click "Payment: 45 days" → the paragraph highlighted | Ask: *"What are V3's payment and freight terms, and where exactly did they say that?"* | T-EDGE-03 |
| **EDGE-04 / EDGE-06** Angled phone photo | V4 rate card: **AI-generated image (synthetic fixture, owner-approved deviation from DL-21; capture kit §8)**, labelled in its file name and on screen | P5, P8 | Page found and flattened; OCR read, one unit per line with confidence. There is one read path (OCR), so every price read from the image is **UNRESOLVED (READ_SINGLE_SOURCE, plus LOW_OCR_CONFIDENCE when < 80%)** with the candidate shown; never auto-verified | Vendors & Inbox: the image with "OCR read · confidence" and the AI-generated label; V4 cells Unresolved with candidates | Open the image from V4's documents; open a V4 cell's drawer (OCR line cited); confirm one value via Accept/Correct | T-EDGE-04 |
| **EDGE-05** Terse email | V5 `.eml` with the exact sentence, unchanged. Its questionnaire and certificates come in a separate V5 submission (DL-23). | P5, P8 | Turned into per-line values. Each part is handled as below. | V5 column with mixed badges | Open the V5 email next to the V5 column | T-EDGE-05 |
| EDGE-05a "₹42/kg for the 5-ply" | V5 + item-master reference weights | P8 | Group expansion to 5-ply lines. ₹/kg × reference weight → ₹/box, **ASSUMED (REFERENCE_WEIGHT)**, with a **billed-weight caveat** (DL-31). GST: V5 is silent → ASSUMED per the RFx basis (DL-26). Estimated-weight lines → NEEDS_REVIEW (DL-18). | Drawer: "₹42/kg × 0.412 kg (item master row 14, reference weight — assumed) = ₹17.30/box; invoiced on actual weight" | Open a 5-ply V5 cell, then one WEIGHT_ESTIMATED cell (constants labelled "not validated") | T-EDGE-05a, T-WGT-01, T-GST-01 |
| EDGE-05b "38 for the 3-ply" | V5 | P8 | Unit and currency inherited from "₹42/kg", recorded with both evidence spans → ASSUMED (UNIT_INHERITED) | Badge "unit inferred from '₹42/kg'". Drawer shows both spans highlighted. | Open a 3-ply V5 cell | T-EDGE-05b |
| EDGE-05c "rest same as last year" | V5 + baseline price rows (own same-spec, own changed-spec, other-vendor-only) + V5 **baseline terms** | P7, P8 | **Ambiguous (DL-20).** Reading A (remaining line prices) and reading B (remaining terms) are both kept. 7-ply cells are UNRESOLVED (REFERENCE_AMBIGUOUS) with candidates shown, or BASELINE_SPEC_CHANGED / BASELINE_NOT_FOR_VENDOR. Unstated terms show last-year candidates. Nothing is applied, and freight is never a candidate. A template clarification request is generated. | Reference panel: the vendor's phrase, the reading A lines with candidates and citations, the reading B terms with candidates, "Generate clarification request", "Confirm reading" | Generate the request → show both readings in it → approve to the outbox. Then (optional) record "Vendor confirmed: prices" with a source note → 2 cells become ASSUMED, the audit entry is shown, the VP split is re-asked | T-EDGE-05c-A, T-EDGE-05c-B, T-CLAR-01 |
| EDGE-05d "freight extra" | V5 | P8 | Freight UNKNOWN. Landed not calculable. Last year's freight never carried forward. | Landed toggle: V5 cells "Not calculable — freight unknown" | Toggle to Landed | T-EDGE-05d |
| **EDGE-07** 27 of 30 | V3 `.docx` quoting 27 lines | P8, P9, P10 | 3 × MISSING, never filled. Every ranking or total that involves V3 discloses the gap. Single-vendor totals for V3 use 27 lines. | Coverage chip "27/30". Exclusions list in answers naming lines. | Ask: *"Who didn't quote everything, and what does that do to the ranking?"* | T-EDGE-07 |
| **EDGE-08** USD vendor | V2 PDF entirely in USD: a domestic converter with USD-linked prices, **invoiced in INR at the rate on invoice date** (DL-30) | P8, P10 | Converted at the stated rate and date. Original kept. ASSUMED (FX_RATE). **FX exposure disclosed: ₹ per 1% USD/INR move on V2-awarded spend.** A rate edit → global recompute, scenarios stale, awards superseded. | As-quoted toggle shows USD. Settings: rate, date, source. Readiness/memo: FX exposure line. | Edit the USD rate in Settings → re-ask the VP question → show what changed and the exposure line | T-EDGE-08, T-FX-01 |
| **EDGE-09** per box vs per 100 | V4 card "Rate per 100 pcs" plus 2 unlabelled rows; V1/V2/V3/V5 per box | P7, P8 | Labelled per-100 → ÷100 (CONVERTED). Unlabelled ~100× peers → UNIT_SUSPECT with a ÷100 suggestion. V4 values also stay Unresolved as single OCR reads until confirmed | Review item with the suggestion | Accept the suggestion live → value and peer statuses update | T-EDGE-09 |

---

## 4. Analyst question set (DEL-02 recording, and live)
Each question is tagged with the SOT items it evidences. None is hardcoded (SOT AI-04). The recording uses the same running system.

| # | Question | Evidences |
|---|---|---|
| Q1 | "Which vendor is cheapest overall, and how confident are you?" | FN-11, FN-12, EVAL-02 |
| Q2 | "Show landed cost per box by vendor for the 5-ply lines as a chart." Then open Show work: the chart data equals the result table. | FN-14 (T-OUT-01), EDGE-05d |
| Q3 | "Who didn't quote everything, and what does that do to the ranking?" | EDGE-07, FN-13 |
| Q4 | "Which vendors cleared the quality questionnaire, and why didn't the others?" | EX-04 (premise), DL-3/14 |
| Q5 | **"What if we split it, cheapest per line, but only among vendors who cleared the quality questionnaire?"** | **EX-04**, EX-05 |
| Q6 | "How much of that saving depends on assumptions, such as FX, estimated or reference weights, freight or last year's prices? Which lines could change?" | EVAL-03, EDGE-08, EDGE-05c (DL-25/28/30/31) |
| Q7 | "Whose ISO 9001 certificate is valid through the contract period, and show me where it says so." | **FN-11 (document facts, SC-02)**, FN-10 |
| Q8 | "Which quotes deviate from our spec, and how much cheaper are they because of it?" | EVAL-04 |
| Q9 | "Which lines does the split leave uncovered, and what happens if we accept alternates there?" | FN-16 |
| Q10 | "Export that split as a spreadsheet." Then open the file and compare it with the on-screen table. | FN-15 (T-OUT-02) |

Trap questions, used live only if the panel goes there: "On what grounds did the others fail?" (premise correction); "What's V2's financial health?" (not in the data, SOT AI-03).

---

## 5. Sandbox segment (DL-17) and optional upload (DL-4)
- **Sandbox:** if the panel wants to draft something of their own, switch to the sandbox RFx. Anything goes there. The primary RFx and the prepared responses are untouched (hash check).
- **Unseen file (optional):** on request, upload a panel-supplied file to the primary RFx (or the sandbox). Same pipeline, then global recompute.

---

## 6. Contingencies
| Situation | Response |
|---|---|
| The co-pilot draft doesn't conform at P3 | Fix by chat or direct edit (the normal workflow). If it still fails after 2 attempts, load the canonical spec as **"seeded fallback"** (origin shown on screen) and say so. |
| Real phone photo not yet registered | The demo can't use the synthetic image as the primary fixture (DL-21). Postpone the demo, or present V4 as "pending real photo" and say so. |
| Model API outage | Load the warm fallback snapshot (origin "stored results from the real pipeline", shown on screen). Analyst questions then run from the recording (DEL-02). |
| Extraction slower than budget | Continue narrating other vendors. Phase A runs in parallel. |
| Panel changes a primary line so it no longer conforms | Explain: the prepared responses answer the canonical spec. Do the change in the sandbox, or accept that those lines will be unmatched. |

---

## 7. Evidence checklist (sign-off before each dry run)
- [ ] Every row of §3 was shown at least once (or is scheduled for the recording).
- [ ] Q1–Q10 answered on the live system. The grounding and label-lint status of each answer is visible in Show work.
- [ ] One RFx went from P1 to P11 without a seeded fallback.
- [ ] The honesty statement (§0) was given.
- [ ] One dry run was driven by a person not involved in writing this runbook (FD-7 rev. 2, C1; audit SC-12 resolved).
- [ ] V4 is the genuine phone photograph (manifest checked).
- [ ] The clarification request for "rest same as last year" was shown, with both readings.
- [ ] One document was opened from each of the 4 entry points.
- [ ] "Awaiting response" was visible for at least one vendor during P5.
- [ ] P1 showed the AI column mapping and the deterministic import (no AI-typed line values).
- [ ] P10 showed at least one FREIGHT_DEPENDENT line with its break-even, and the readiness acknowledgement.
