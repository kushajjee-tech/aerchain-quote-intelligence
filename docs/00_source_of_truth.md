# 00 — Source of Truth: Assignment Requirements Catalogue
**Canonical requirements reference.** Extracted directly from `docs/assignment.pdf` (2 pages, "Kill the Quote Spreadsheet", Aerchain), not from any derived document.
**Created:** 2026-11-04 · **Change control:** this file changes **only** if the assignment PDF changes. Product decisions live in `01`–`08`. They must cite the IDs below and may never weaken them without explicit flagging and owner approval (see root `CLAUDE.md`).

---

## How to read this catalogue

| Field | Meaning |
|---|---|
| **ID** | Stable identifier. Prefixes: `REQ` explicit requirement · `FN` functional expectation · `EX` narrative example · `EDGE` named edge case · `AI` AI-related constraint · `DEL` deliverable · `EVAL` evaluation signal · `PERM` permission · `LIM` limitation / unspecified item · `INFO` informational |
| **Source text** | Verbatim from the PDF. `…` marks an omission within the same sentence. |
| **Pg** | PDF page (1 or 2) |
| **Obligation** | **M-E** mandatory, explicit · **M-I** mandatory, implied by narrative or evaluation emphasis · **O** optional / invited · **P** permission (a freedom, not an obligation) · **I** informational |
| **Expected product behaviour** | What the product must do to satisfy the item. This is the minimum reading of the text, not our design. |
| **Required test** | The kind of test that must exist to prove the behaviour. Concrete test names live in the implementation plan. |
| **Demo evidence** | What the panel must be able to *see* in the live demo or recording |

Interpretation rule: where the PDF is ambiguous, the catalogue records the ambiguity in the item rather than choosing a reading. Readings are product decisions and belong in `01`–`08`.

---

## 1. Explicit requirements (REQ)

| ID | Source text | Pg | Type | Obl. | Expected product behaviour | Required test | Demo evidence |
|---|---|---|---|---|---|---|---|
| REQ-01 | "Build the system that drafts an RFx, reads whatever vendors send back, and lets a buyer interrogate the result in plain language." | 1 | Scope statement | M-E | All three capabilities exist and are connected: RFx drafting, reading of arbitrary vendor responses, plain-language interrogation. | E2E test covering draft → responses read → NL question answered | One continuous session showing all three |
| REQ-02 | "Build the thing that ends it." | 1 | Outcome | M-E | Removes the manual retyping (EX-03) and the day-long what-if (EX-05) | Timed E2E: responses → comparison with no manual data entry; what-if answered in minutes | Responses land in the comparison with no retyping; VP question answered live |
| REQ-03 | "One flow, end to end." | 1 | Scope constraint | M-E | A single connected flow from RFx creation through to the award decision, not disconnected tools | E2E test traversing every stage on one RFx | The panel can follow one RFx from creation to award |
| REQ-04 | "Build the demo at a size where it actually hurts: five vendors, thirty line items, a questionnaire, attached documents." | 1 | Scale | M-E | Demo dataset has exactly 5 vendors, 30 line items, a questionnaire, and attached documents | Dataset assertion: counts = 5 / 30 / ≥1 questionnaire / ≥1 attached doc per relevant vendor | Grid shows 30 × 5. Questionnaire and attachments visible. |
| REQ-05 | "Fabricate a dataset a procurement person would nod at." | 1 | Data realism | M-E | Realistic specs, prices, terms and documents for the chosen category | Domain-realism review by a human with procurement knowledge (not only an AI review) + plausibility checks | Dataset looks credible on inspection (specs, price spreads, terms, certificates) |

## 2. Functional expectations (FN)

| ID | Source text | Pg | Type | Obl. | Expected product behaviour | Required test | Demo evidence |
|---|---|---|---|---|---|---|---|
| FN-01 | "A buyer *talks* an RFx into existence with an AI co-pilot" | 1 | RFx creation | M-E | RFx created conversationally with a real AI co-pilot (see AI-06) | Co-pilot eval: natural-language instructions → correct structured RFx changes | Live conversational drafting of an RFx |
| FN-02 | "— scope, line items, questionnaire, terms." | 1 | RFx content | M-E | The co-pilot produces all four parts: scope, line items, questionnaire, terms | Co-pilot eval asserts all four parts are present and editable | Drafted RFx shows scope, lines, questionnaire, terms |
| FN-03 | "It goes out to vendors over a channel you choose." | 1 | Distribution | M-E | The RFx is sent to vendors over one chosen channel (the channel may be stubbed, PERM-05) | Send creates one outbound message per vendor | Sent messages visible per vendor |
| FN-04 | "Vendors reply however they like; nobody is forced into your template." | 1 | Response freedom | M-E | No template, portal or format is required of vendors. Any template is optional. | Ingestion succeeds on non-template responses of every planted shape | Non-template responses processed |
| FN-05 | "Your system reads every response, whatever shape it arrives in," | 1 | Ingestion | M-E | Every response is read, whatever its format or layout, including EDGE-01…05 | Per-format extraction tests + unseen-layout (perturbation) tests | Each of the five responses read on screen |
| FN-06 | "and lands them all in a single side-by-side comparison" | 1 | Comparison | M-E | All vendors' data in one side-by-side view | Comparison contract test: all vendors × all lines present | One grid with every vendor side by side |
| FN-07 | "— same lines," | 1 | Normalisation | M-E | Vendor lines are mapped to the RFx's lines regardless of how vendors ordered or named them | Line-matching accuracy test incl. shuffled rows | Vendor lines aligned to RFx lines |
| FN-08 | "same units," | 1 | Normalisation | M-E | Prices converted to one common unit. Where conversion isn't possible, the reason is shown (see EVAL-02). | Unit-conversion tests (per 100, per kg, etc.) + not-convertible disclosure test | Converted unit prices with the conversion visible |
| FN-09 | "same currency" | 1 | Normalisation | M-E | Prices converted to one common currency | FX conversion test incl. a whole-USD vendor | INR values for the USD vendor, with the original visible |
| FN-10 | "— with questionnaire answers and attached docs sitting alongside the numbers." | 1 | Comparison content | M-E | Questionnaire answers and attached documents are shown in the comparison next to the prices | UI/contract test: per-vendor answers + documents reachable from the comparison | Answers and documents opened from the comparison |
| FN-11 | "Then the buyer stops clicking and starts asking. Natural language, over the whole comparison." | 1 | NL analysis | M-E | NL questions can cover the **whole** comparison: prices, lines, questionnaire answers, attached-document content, terms | Analyst eval incl. questions about questionnaire answers and document facts, not only prices | Questions spanning prices, answers and documents |
| FN-12 | "Text answers," | 1 | Output | M-E | Narrative answers | Analyst eval | Text answer |
| FN-13 | "tables," | 1 | Output | M-E | Tabular answers | Analyst eval asserts a table block | Table answer |
| FN-14 | "charts," | 1 | Output | M-E | Chart answers built from the analysed data | Chart test: chart data equals the tool-result data | Chart answer |
| FN-15 | "exports." | 1 | Output | M-E | Downloadable exports of answers or the comparison | Export test: file opens, contents equal the source data | File exported and opened |
| FN-16 | "all the way to a defensible award decision." | 1 | Decision | M-E | The flow ends in an award decision whose basis can be defended (sources, assumptions, exclusions) | Award test: every number traces to sources; assumptions and exclusions listed | Award decision with its justification |

## 3. Narrative examples (EX)

| ID | Source text | Pg | Type | Obl. | Expected product behaviour | Required test | Demo evidence |
|---|---|---|---|---|---|---|---|
| EX-01 | "A category buyer needs 30 line items of corrugated packaging." | 1 | Persona + category example | M-I (persona) / P (category, PERM-01) | Primary user is a category buyer. The category is chosen (corrugated is one offered example). | — (design) | Buyer-centred UI |
| EX-02 | "They write an RFx. They email five vendors. Over the next nine days, this comes back:" | 1 | Process example | M-I | Responses arrive from five vendors **over time**, not all at once. The product handles staggered arrival. | Ingestion test with responses arriving at different times, and one vendor not yet responded | Status per vendor while responses arrive |
| EX-03 | "The buyer opens Excel and retypes all of it. Three days gone." | 1 | Pain point | M-I | No manual retyping of vendor data | Timed E2E with zero manual data entry | No retyping in the demo |
| EX-04 | "“what if we split it, cheapest per line, but only among vendors who cleared the quality questionnaire?”" | 1 | Analytical example | M-I | Answers this compound question: (a) per-line split, (b) cheapest per line, (c) restricted to vendors who **cleared the quality questionnaire** | Analyst + scenario test with an independently computed expected answer | This exact question asked and answered |
| EX-05 | "— and there goes the fourth." | 1 | Pain point | M-I | A what-if like EX-04 takes minutes, not a day | Latency test on EX-04 | Answer in minutes |
| EX-06 | "This happens every day, in every procurement team on earth, and everyone has quietly accepted it as the cost of doing business. We haven't." | 1 | Motivation | I | — | — | — |

## 4. Named edge cases (EDGE)

Every EDGE item needs a **dataset fixture, a test, and a demonstration strategy** (root `CLAUDE.md`).

| ID | Source text | Pg | Type | Obl. | Expected product behaviour | Required test | Demo evidence |
|---|---|---|---|---|---|---|---|
| EDGE-01 | "a beautiful Excel that ignores the template entirely." | 1 | Response shape | M-I | Reads a spreadsheet in its own layout, without depending on the template | Fixture: own-layout xlsx. Test: extraction + matching accuracy, shuffled-layout variant. | That Excel's data in the grid |
| EDGE-02 | "A PDF on letterhead with the discount buried in a footnote." | 1 | Response shape + hidden term | M-I | Reads a letterhead PDF **and** finds the footnote discount and applies it | Fixture: PDF with a footnote discount. Test: discount extracted, scoped, applied. | Footnote discount shown applied, with its source |
| EDGE-03 | "A Word doc where the commercials are in a paragraph." | 1 | Response shape + prose terms | M-I | Pulls commercial terms out of prose | Fixture: docx with prose commercials. Test: each term extracted with its sentence. | Terms linked to their sentences |
| EDGE-04 | "A photo of a printed rate card, taken at an angle, on a phone." | 1 | Response shape (image) | M-I | Reads an angled phone photo of a printed rate card | Fixture: angled photo (ideally a real phone photo of a printout). Test: values read or flagged. | Photo read; uncertain values shown (see EDGE-06) |
| EDGE-05 | "And one email that just says “₹42/kg for the 5-ply, 38 for the 3-ply, rest same as last year, freight extra.”" | 1 | Response shape (terse email) | M-I | Reads a terse free-text email into structured quotes (components below) | Fixture: email with this exact sentence. Tests: EDGE-05a–d. | This email turned into comparison values, with each interpretation visible |
| EDGE-05a | "₹42/kg for the 5-ply" | 1 | Weight-based, group price | M-I | A per-kg price applied to a **group** (5-ply items), then converted to the comparison unit | Group expansion + kg → unit conversion test | 5-ply lines priced from ₹42/kg, with the conversion shown |
| EDGE-05b | "38 for the 3-ply" | 1 | Elliptical price (no unit or currency stated) | M-I | "38" has no stated unit or currency. The product must interpret it, and show that it did. | Elliptical-unit test (interpretation recorded) | How "38" was interpreted is visible |
| EDGE-05c | "rest same as last year" | 1 | Reference to history | M-I | Resolves "the rest" against historical data or flags it. *Ambiguity in the source:* "rest" may mean the remaining **lines** or the remaining **terms**. | Reference-resolution test, incl. the ambiguity handling | "Same as last year" values or flags, with their source |
| EDGE-05d | "freight extra" | 1 | Commercial term | M-I | Freight is not included in the price, and the comparison must reflect that | Freight-basis test | Freight shown as extra / not included |
| EDGE-06 | "The angled photo." | 2 | Evaluated edge (re-emphasises EDGE-04) | M-E | As EDGE-04, **plus** EVAL-02: what the product does and shows when unsure about the photo | As EDGE-04 + uncertainty display test | Uncertain photo values shown to the buyer |
| EDGE-07 | "The vendor who quoted 27 of 30 lines." | 2 | Partial coverage | M-E | Handles a vendor missing 3 of 30 lines without inventing values, and shows the gap | Fixture: 27/30 vendor. Test: 3 missing cells, never filled; analyses disclose them. | Coverage 27/30 and how the gaps affect answers |
| EDGE-08 | "The one who quoted in USD." | 2 | Currency | M-E | A vendor quoting in USD is converted to the common currency transparently | Fixture: USD vendor. Test: conversion, original preserved, rate disclosed. | USD vendor compared in INR with the original USD visible |
| EDGE-09 | "The one whose “per box” is someone else's “per 100 pieces.”" | 2 | Unit inconsistency across vendors | M-E | Different vendors' units ("per box" vs "per 100 pieces") are reconciled. Unclear cases are not silently mis-compared. | Fixture: a per-100 vendor among per-box vendors. Test: conversion, and detection when the unit is unclear. | Per-100 prices normalised. Unclear cases flagged. |

## 5. AI-related constraints (AI)

| ID | Source text | Pg | Type | Obl. | Expected product behaviour | Required test | Demo evidence |
|---|---|---|---|---|---|---|---|
| AI-01 | "One rule: stub the plumbing, but the AI loops must be real." | 2 | The single hard rule | M-E | Every AI loop (co-pilot, extraction, analysis) runs a real model at runtime | Call-log test: real model calls for each AI loop; no canned outputs | AI call activity visible or provable live |
| AI-02 | "Don't fake the extraction," | 2 | AI integrity | M-E | Extraction is done by the live system on the actual files, with no pre-parsed or hand-entered data | Perturbation test: changed files → changed, correct extraction with no code changes | Re-run extraction live, or extract a new file |
| AI-03 | "don't fake the reasoning," | 2 | AI integrity | M-E | Analytical reasoning is produced live from the data, not scripted | Off-script analyst questions answered correctly | Panel-chosen questions answered |
| AI-04 | "don't hardcode the answers to your demo questions." | 2 | AI integrity | M-E | No question→answer mappings. Answers derive from the data. | Static check (no demo literals in prompts/code) + perturbed-dataset analyst eval | Changed data → changed answers, if asked |
| AI-05 | "Real analysis on real extracted data," | 1 | AI integrity | M-E | Analysis runs on the data the system actually extracted | Analyst numbers trace to extracted values | Answer → source drill-down |
| AI-06 | "with an AI co-pilot" | 1 | AI integrity (co-pilot) | M-E | The co-pilot is a real AI loop (falls under AI-01) | Co-pilot calls logged; varied instructions handled | Live co-pilot turn |

## 6. Deliverables (DEL)

| ID | Source text | Pg | Type | Obl. | Expected product behaviour | Required test | Demo evidence |
|---|---|---|---|---|---|---|---|
| DEL-01 | "A working prototype, ready for a live demo we'll drive with you." | 2 | Deliverable | M-E | A runnable prototype that holds up when **the panel drives it** (their clicks, their questions, possibly their files) | Dry runs with an unscripted driver; off-script analyst eval | Live demo driven by the panel |
| DEL-02 | "A recorded walkthrough of the analyst conversation — you choose the questions worth asking." | 2 | Deliverable | M-E | A recording of the NL analyst conversation, with questions we choose | Recording exists; questions run on the real system | Recording |
| DEL-03 | "And a one-page note on what you decided," | 2 | Deliverable | M-E | A **one-page** note of key decisions | Length check (one page) + content check | Note |
| DEL-04 | "and what you deliberately left out." | 2 | Deliverable | M-E | The same note lists deliberate exclusions | Content check | Note section |
| DEL-05 | "If you finish this and think “the interesting problem was actually somewhere else” — tell us that too." | 2 | Invited deliverable | O | Optionally state where the better problem lies | — | Note / addendum |

## 7. Evaluation signals (EVAL)

| ID | Source text | Pg | Type | Obl. | Expected product behaviour | Required test | Demo evidence |
|---|---|---|---|---|---|---|---|
| EVAL-01 | "Everyone can build the happy path. We care about the rest:" | 2 | Emphasis | M-I | Non-happy paths are first-class (EDGE-*) | Edge-case coverage audit | Edge cases shown deliberately |
| EVAL-02 | "What does your system do — and what does it *show the buyer* — when it isn't sure?" | 2 | Uncertainty UX | M-E | Uncertainty is (a) handled safely **and** (b) **shown** to the buyer in the UI | Tests that uncertain values are marked and never silently mixed in | Uncertain values visibly marked, with reasons |
| EVAL-03 | "Trust. Would a buyer with ₹4 crore on the line act on what's on your screen? What did you build to earn that?" | 2 | Trust | M-E | Trust mechanisms (provenance, checks, auditability) good enough for a ₹4 crore decision. Demo spend at that scale. | Traceability test (every number → source); silent-error metric | Drill from any number to its source |
| EVAL-04 | "Judgment and taste. A thousand decisions here have no correct answer. We want to see how you made them, and whether you can say why." | 2 | Judgment | M-E | Decisions are explicit and explained | Decision log exists and is reflected in DEL-03 | Able to explain any decision on request |
| EVAL-05 | "We'd rather hire the person who found the better problem than the one who followed the brief perfectly." | 2 | Problem-finding | O (weighs DEL-05) | — | — | Better-problem statement |
| EVAL-06 | "ready for a live demo we'll drive with you" | 2 | Robustness | M-E | Works off-script (see DEL-01) | Off-script eval; unseen-input drill | Panel-driven interaction succeeds |

## 8. Permissions and limitations (PERM / LIM / INFO)

| ID | Source text | Pg | Type | Obl. | Expected product behaviour | Required test | Demo evidence |
|---|---|---|---|---|---|---|---|
| PERM-01 | "Or IT hardware, or MRO spares, or freight lanes — you'll pick the category." | 1 | Category choice | P | We choose one category (chosen: corrugated packaging). | — | Category stated |
| PERM-02 | "over a channel you choose." | 1 | Channel choice | P | Any channel | — | Channel stated |
| PERM-03 | "You pick everything — the agent framework, the model(s), the email path, the storage, the UI, the personas, the industry, the data, the export formats, the guardrails." | 2 | Total liberty | P | All listed choices are ours. They don't relax REQ/FN/AI/DEL items. | — | Choices explained (EVAL-04) |
| PERM-04 | "No house style, no hidden right answer." | 2 | Liberty | P | — | — | — |
| PERM-05 | "Fake the SMTP server if you like." | 2 | Stubbing permission | P | Email transport may be simulated. Only plumbing may be stubbed (AI-01). | — | Stub disclosed |
| PERM-06 | "you choose the questions worth asking." | 2 | Walkthrough freedom | P | We pick the walkthrough questions (still bound by AI-04) | — | — |
| LIM-01 | "One rule:" | 2 | Sole hard rule | M-E | AI-01 is the only explicitly stated rule. Everything else is judged on EVAL-*. | — | — |
| LIM-02 | "TIMELINE" / "DEMO" (labelled fields left blank) | 2 | Unspecified | I | No timeline or demo date is given in the PDF. Any schedule is our estimate. | — | — |
| INFO-01 | "Have fun with it." | 2 | Tone | I | — | — | — |

---

## 9. Counts
REQ 5 · FN 16 · EX 6 · EDGE 13 (9 parent + 4 sub-items of EDGE-05) · AI 6 · DEL 5 · EVAL 6 · PERM 6 · LIM 2 · INFO 1. **Total: 66 catalogued items.**
Mandatory items (M-E + M-I, incl. LIM-01): 55 · Optional: 2 (DEL-05, EVAL-05) · Permissions: 6 · Informational: 3 (EX-06, LIM-02, INFO-01). 55 + 2 + 6 + 3 = 66.
