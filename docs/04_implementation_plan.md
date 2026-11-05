# Implementation Plan — Quote Intelligence Prototype
**Status:** v1.7 · PM review changes (DL-25…DL-32), vertical-slice re-sequencing, FD-7 rev. 4 · **Implements:** `docs/02_PRD.md` v1.5 via `docs/03_architecture.md` v1.5 · **Runbook:** `docs/10_demo_runbook.md` · **Canonical requirements:** `docs/00_source_of_truth.md` · **Decisions:** `docs/08_final_product_decisions.md` · **Fix log:** `docs/06_fix_log.md`
**Effort assumption [R]:** one builder with AI coding assistance, 1 day = one focused working day. The assignment leaves the timeline blank (SOT LIM-02).
- **FD-7 rev. 4 (2026-11-04):** **29.0 days** of estimated effort for one builder: **20.5** P0 essential implementation + **6.5** testing, evaluation & integration + **2.0** demo preparation. This is rev. 3 (25.75) **+3.5** for the approved PM-review changes **−0.25** scope cut, itemised in §2.6. It's an estimate, **not a calendar deadline or contractual commitment**. P1 (3.25 d) is outside the committed schedule.
- **History:** 17.0 (rev. 0) → 18.5 (rev. 1) → 23.25 (rev. 2) → 25.75 (rev. 3) → **29.0 (rev. 4)**. Every change is shown; none is compressed elsewhere.
- **Protected allocations (unchanged or larger, not reducible):** B1 oracle/harness 0.75 · B2 extraction tuning 1.0 · B4 analyst evaluation 0.75 · **B5 test suites 2.0** · B6 integration & debugging 1.0 · C1 dry runs incl. the unscripted run 1.0 · demo preparation total 2.0. O3 and X1–X4 stay rejected. O1/O2 are optional only without loss of functionality. (B3 is not protected; it is reduced by the P0-3 scope cut.)

Tags: **[A]** · **[R]** · **[DL-n]** · **(Bn/In)** = review finding.

---

## 1. Sequencing logic **[R]** (re-sequenced for P0-4)
1. **Isolation and a thin dataset first, then a working vertical slice by day ~6.5.** One RFx, imported from the item master, goes through send, two vendors' responses (V5's two messages + V1), live extraction, normalisation, the comparison, the VP question and a draft award. This proves the end-to-end path before anything is widened.
2. **Widen in layers behind the slice:** full dataset and all formats (day 10) → full deterministic core and extraction gate (day ~15) → full UI, co-pilot and scenario engine (day ~20) → analyst, test suites, integration, code freeze (day 27) → demo preparation (day 29).
3. **Milestones M0–M9 remain the work packages** (§3 detail). The schedule (§2.8) runs each one as a thin slice part (*a*) and a widening part (*b*). The split doesn't change any milestone's scope. The slice overhead is costed separately (S, 0.5 d).
4. **Testing and demo preparation are never moved earlier at the cost of their duration:** B1–B7 and C keep their full allocations.
5. **DL-13:** nothing in the dataset or demo script may depend on a P1/P2 feature. This is checked at M1 and again at M10.

## 2. Effort estimate (bottom-up, rev. 4)

### 2.1 Summary by category
| Category | Days | Scheduled? | Contents |
|---|---|---|---|
| **A. P0 essential implementation** | **20.5** | Yes | M0–M9 (code + co-located unit/golden/property tests) + S (vertical-slice integration). +2.75 in rev. 4. |
| **B. Testing, evaluation & integration** | **6.5** | Yes | Workstream MT (B1–B7). +0.75 (B5), −0.25 (B3) in rev. 4. |
| **C. Demo preparation** | **2.0** | Yes | M10: dry runs (incl. one unscripted), recorded walkthrough, one-page note |
| **P0 total** | **29.0** | | |
| D. P1 enhancements | 3.25 | **No** | §2.5 (all other PM-review P1/P2 items are deferred, and none is added here) |

### 2.2 A — P0 essential implementation (20.5 d)
| # | Milestone | Days | Rev. 4 Δ | Slice part (a) / widening part (b) |
|---|---|---|---|---|
| M0 | Skeleton, schemas, storage guard, LLM gateway, append-only store | 0.5 | 0 | all in the slice |
| M1 | Eval workspace, generator, dataset, brief pack, canonical spec, baseline + terms, answer keys, negative fixtures (**+ FSC-required, food-grade line-level, no-GST-basis, item-master header variants**), lints, V4 print card + photo registration, realism review cycle | 3.25 | 0 (fixture changes absorbed by removing the FSC question from the primary set) | **a 1.5**: canonical spec, item master/brief pack, V1, V5 (both messages), baseline, truth for these, isolation · **b 1.75**: V2–V4, certificates, print card, negative fixtures, perturbation, review pack |
| M2 | Deterministic core + **GST silence rule (DL-26)** + **line-level food-grade gating (DL-29)** + reference weight ASSUMED (DL-31) | **2.25** | **+0.5** | **a 0.75**: status table, units, weight (reference path), freight basis, GST, money · **b 1.5**: the rest |
| M3 | Parsers, OCR, TEXT extraction, OCR path, independent vision path, reconcile, verify, document facts | 2.5 | 0 | **a 0.75**: eml + xlsx parsers, TEXT extraction, verify · **b 1.75**: pdf, docx, image/OCR, vision, reconcile, document facts |
| M4 | Matching, group expansion, Phase A/B, recompute, re-run, awaiting state, submission linking | 1.75 | 0 | **a 0.5**: basic matching + minimal Phase A/B · **b 1.25** |
| M5 | Grid, provenance drawer, review queue (**sorted by decision sensitivity, DL-28**), resolutions, vendor panel, settings, reference panel + **clarification pack (DL-32)**, document entry points | **3.0** | **+0.5** | **a 0.5**: minimal grid with statuses · **b 2.5** |
| M6 | Co-pilot with **deterministic item-master import + AI column mapping (DL-27)**, gap questions, questionnaire/terms drafting, diff UI, conformance, provenance, fallback, sandbox; outbox, deliver, status board, upload | 2.0 | 0 (+0.25 import/mapping, −0.25 batched transcription) | **a 0.75**: import + mapping + approve + send/deliver · **b 1.25** |
| M7 | Scenario engine, savings, readiness, NEEDS_REVIEW override + **freight-aware selection & break-even (DL-25)** + **decision sensitivity (DL-28)** + **FX/billed-weight exposure (DL-30/31)** | **2.25** | **+1.25** | **a 0.25**: cheapest-per-line minimal · **b 2.0** |
| M8 | Views, SQL guard, tools, loop, steering, caveats, grounding, label lint, regeneration, charts, export, Show work | 2.0 | 0 | **a 0.25**: loop with `query` + `run_scenario`, basic grounding · **b 1.75** |
| M9 | Memo, exports, audit views | 0.5 | 0 | **a 0.25**: draft memo · **b 0.25** |
| S | **Vertical-slice integration (P0-4):** slice E2E test, thin-then-widen stubs and rework allowance | **0.5** | **+0.5** | — |
| | **Subtotal A** | **20.5** | **+2.75** | |

### 2.3 B — Testing, evaluation & integration (6.5 d), workstream MT
| # | Item | Days | Rev. 4 Δ | Covers |
|---|---|---|---|---|
| B1 | Independent oracle + HTTP-only eval runner | 0.75 | 0 | Plan §4.2 |
| B2 | Live extraction + matching eval and tuning (real photo primary) | 1.0 | 0 | PRD §1.2; SOT AI-02 |
| B3 | Co-pilot eval (mapping, gaps, questionnaire/terms, edits) + primary-RFx rehearsals (≥ 4/5 conform) | **0.25** | **−0.25** (scope cut, P0-3) | RFX-9/10, DL-19/27 |
| B4 | Analyst eval sets + tuning | 0.75 | 0 | NLA-1…13 |
| B5 | Test suites: T-EDGE, T-OUT, T-ARR, T-CLAR, T-DOC + **T-FRT, T-SENS, T-PACK** (+ fixes) | **2.0** | **+0.75** | CLAUDE.md rule 3; DL-25/28/32 |
| B6 | Cross-component integration and debugging | 1.0 | 0 | E2E stability |
| B7 | Regression, perturbation, drills, performance, DL sweep | 0.75 | 0 | NF-1…5 |
| | **Subtotal B** | **6.5** | **+0.5 net** | |

### 2.4 C — Demo preparation (2.0 d), M10
| # | Item | Days |
|---|---|---|
| C1 | Runbook dry runs: 2 by the builder + **1 driven by someone uninvolved**, with fixes between runs | 1.0 |
| C2 | Recorded analyst walkthrough (DEL-02) | 0.5 |
| C3 | One-page note re-check, regeneration and T-NOTE-01 (`docs/deliverables/one_page_note.pdf`, updated for rev. 4 decisions) | 0.5 |
| | **Subtotal C** | **2.0** |

### 2.5 D — P1 enhancements (3.25 d, unscheduled)
None of these is needed by the assignment, the dataset or the runbook (DL-13). **All can be deferred without compromising any source-of-truth item.**
| P1 item | Days | SOT impact if deferred |
|---|---|---|
| Optional Excel response template (RFX-7) | 0.25 | None. FN-04 says no template is forced. |
| J9b: AI-drafted free-text clarification emails (the deterministic clarification pack is P0, DL-32) | 0.5 | None |
| Bulk accept (REV-5) | 0.25 | None |
| Tooling amortisation in the annual-cost view | 0.25 | None. Tooling is still separated (P0). |
| Vendor share cap (AWD-6) | 0.5 | None |
| Save analyst answer as a scenario (NLA-8) | 0.25 | None. Scenarios are saved from Award (P0). |
| Analyst ask-back (NLA-6) | 0.25 | None. A stated interpretation is P0. |
| Extraction run-history browser (EXT-11b) | 0.5 | None. Basic re-run is P0. |
| FX sensitivity tool | 0.5 | None. A rate edit + recompute is P0 (EDGE-08). |

### 2.6 Reconciliation (nothing hidden)
| Step | Days |
|---|---|
| v1.2 baseline (FD-7 original): 15 build + 2 demo | 17.0 |
| + SC-01…SC-04 fixes (approved, visible) | **+1.5** → 18.5 (approved: 16.5 + 2) |
| Moves between categories: M6 −0.5, M8 −0.5, M10 −0.75 → B3 +0.5, B4 +0.5, B7 +0.75 | 0 |
| + M5 UI re-estimate | +0.5 |
| + B1 oracle and eval harness | +0.75 |
| + B2 extraction tuning iterations | +1.0 |
| + B4 document-fact eval set | +0.25 |
| + B5 named edge-case live suite | +0.5 |
| + B6 integration and debugging | +1.0 |
| + C1/C3 unscripted dry run, rehearsal fixes, one-page editing | +0.75 |
| **Bottom-up P0 total (rev. 2, approved)** | **23.25** (+4.75 vs rev. 1) |
| + SC-05 "rest same as last year", both readings: M2 +0.25, M5 +0.25, B5 +0.25 | +0.75 |
| + SC-06 one-page note: generated now; re-validation inside C3 | 0 |
| + SC-07 human realism review cycle (M1) | +0.5 |
| + SC-08 print card + real-photo registration (M1) | +0.25 |
| + SC-09 chart/export output tests (B5) | +0.25 |
| + SC-10 awaiting-response state: M4 +0.25, B5 +0.25 | +0.5 |
| + SC-11 documents openable from the comparison (M5, incl. tests) | +0.25 |
| **FD-7 rev. 3 total** | **25.75** (+2.5 vs rev. 2) |
| + P0-1 freight-aware award + break-even + readiness acknowledgement: M7 +0.5, B5 +0.25 | +0.75 |
| + P0-2 GST silence rule (M2) | +0.25 |
| + P0-3 deterministic item-master import + AI mapping: M6 +0.25 mapping/import − 0.25 batched transcription | 0 |
| − P0-3 scope cut: B3 rehearsal tuning 0.5 → 0.25 (deterministic import removes transcription variance) | **−0.25** |
| + P0-4 vertical-slice re-sequencing: thin-then-widen overhead + slice E2E integration (S) | +0.5 |
| + P1-5 decision sensitivity: M7 +0.5, M5 queue ordering +0.25, B5 +0.25 | +1.0 |
| + P1-9 line-level food-grade gating (M2); FSC question removed (no measurable saving) | +0.25 |
| + P1-10 / P1-11 FX and billed-weight exposure caveats (M7); reference weight → ASSUMED (M2, no measurable cost) | +0.25 |
| + P1-6 clarification pack: M5 +0.25, B5 +0.25 | +0.5 |
| **FD-7 rev. 4 total** | **29.0** (+3.25 vs rev. 3: +3.5 additions, −0.25 cut) |


**Deferred (PM review, C):** all other P1/P2 recommendations. None is required to make an accepted change work or to fix a correctness problem.

### 2.7 Trade-off decisions (FD-7 rev. 2)
**Outcome:** O3 and X1–X4 are **rejected**. O1 and O2 are **optional efficiency improvements, allowed only with no loss of functionality** (O1 keeps the AuditEvent, recompute and stale-marking; O2 keeps automatic status updates). Any time saved becomes slack and does not reduce the committed estimate (now 29.0 d). P1 stays outside the schedule. The original options table is kept below for the record.
1. **Defer all P1 (§2.5):** already the plan. It saves nothing from the committed estimate, because P1 isn't scheduled.
2. **Options that don't weaken any SOT item:**
   | Option | Saves | Cost / risk |
   |---|---|---|
   | O1. Constant-set activation via config file + restart instead of a UI action (DL-18 versioning kept) | ≤ 0.25 | **Optional.** Allowed only if activation still writes an `AuditEvent`, triggers the global recompute and marks scenarios stale. |
   | O2. Status board as a simple list; progress via polling instead of SSE | ≤ 0.25 | **Optional.** Allowed only if statuses still update automatically, without a manual refresh |
   | O3. Reduce B6 integration buffer from 1.0 to 0.5 | 0.5 | **Rejected (FD-7 rev. 2)** |
3. **Options that would weaken a SOT item: listed, not recommended:**
   | Option | Saves | Weakens |
   |---|---|---|
   | X1. **Rejected.** Drop `.xls`/`.heic`/scanned-PDF support (not in the dataset) | 0.25 | FN-05 "whatever shape" for unseen uploads (DEL-01, DL-4) |
   | X2. **Rejected.** Perturbation limited to values, names and order (no layout change) | 0.25 | AI-02/AI-04 evidence |
   | X3. **Rejected.** Skip the unscripted dry run | 0.5 | DEL-01 / EVAL-06 "we'll drive" |
   | X4. **Rejected.** Skip B2 tuning iterations | 1.0 | EVAL-03 trust; silent-error gate at risk |

   No trade-off may touch named edge cases, real AI extraction or reasoning, or trust functionality (provenance, statuses, grounding, label lint, audit, isolation).

### 2.8 Schedule (single builder, sequential, vertical slice first)
| Days (cumulative) | Work | Checkpoint / gate |
|---|---|---|
| 0 – 0.5 | M0 | Guard + gateway green |
| 0.5 – 2.0 | M1a | Canonical spec, item master, V1 + V5 (both messages), baseline, truth subset |
| 2.0 – 2.75 | M3a | eml/xlsx parse + TEXT extraction + verify |
| 2.75 – 3.5 | M2a | Core rules (units, reference weight, freight basis, GST, money, status table) |
| 3.5 – 4.0 | M4a | Basic matching + minimal Phase A/B |
| 4.0 – 4.75 | M6a | Item-master import with AI mapping → approve → send → deliver |
| 4.75 – 5.25 | M5a | Minimal grid with statuses |
| 5.25 – 5.5 | M7a | Cheapest-per-line minimal scenario |
| 5.5 – 5.75 | M8a | Analyst loop: `query` + `run_scenario` |
| 5.75 – 6.0 | M9a | Draft award memo |
| 6.0 – 6.5 | **S** | **✅ VERTICAL SLICE (day 6.5):** one RFx: item-master import (AI mapping, buyer confirms) → approve → send → V5 email + V5 questionnaire submission + V1 xlsx delivered → live extraction → normalised grid with statuses (V5 ₹/kg via reference weight, ASSUMED; GST per RFx basis) → VP-style question answered via `run_scenario` → draft award memo. Slice E2E test green. |
| 6.5 – 8.25 | M1b | Full dataset generated. **Print card → owner, review pack → reviewer (external work starts).** |
| 8.25 – 10.0 | M3b | **✅ DAY 10:** all 5 vendors' artefacts exist and **all formats extract**, incl. the photo dual-read on the synthetic image. Dataset lints green. |
| 10.0 – 10.75 | B1 | Oracle + runner ready |
| 10.75 – 12.25 | M2b | Full deterministic core (DL-8/20/24/26/29/31 …) golden tests 100% |
| 12.25 – 13.5 | M4b | Order-shuffle determinism, awaiting state, submission linking |
| — (before B2) | **M1-final** (external) | Real photo registered (DL-21) + realism review signed off (DL-22) → **dataset freeze** |
| 13.5 – 14.5 | B2 | **✅ DAY ~15:** extraction gate passed **on the real photo**. Full pipeline + deterministic core complete for all 5 vendors. |
| 14.5 – 17.0 | M5b | Review queue (sensitivity-ordered), provenance, clarification pack, documents |
| 17.0 – 18.25 | M6b | Full co-pilot: gaps, questionnaire/terms, conformance, provenance, sandbox |
| 18.25 – 18.5 | B3 | Co-pilot conforms ≥ 4/5 |
| 18.5 – 20.5 | M7b | **✅ DAY ~20:** full UI review flow, live co-pilot primary RFx with conformance, scenario engine with freight-aware selection, break-even, sensitivity and exposures; oracle parity on scenarios |
| 20.5 – 22.25 | M8b | Full analyst |
| 22.25 – 23.0 | B4 | Analyst gate |
| 23.0 – 23.25 | M9b | Memo/exports/audit complete (J7 end to end) |
| 23.25 – 25.25 | B5 | All named suites pass |
| 25.25 – 26.25 | B6 (drawn down earlier as needed; remainder here) | E2E stable |
| 26.25 – 27.0 | B7 | **Code freeze (day 27)** |
| 27.0 – 29.0 | M10 (C1–C3) | Dry runs incl. unscripted; walkthrough; T-NOTE-01 |

---

## 3. Milestones in detail

### M0 — Skeleton (0.5 d)
**Build:**
- Repo layout per architecture §5.1.
- `storage.safe_path` guard + the startup check (refuse if `EVAL_ROOT` is set, or if the roots overlap).
- Domain enums for the **canonical status model** (PRD §6), reason codes split into blocking and advisory, and eligibility with sections.
- SQLAlchemy models (PRD §7).
- LLM gateway:
  - explicit effort per route;
  - structured outputs;
  - stop-reason handling and refusal fallback;
  - call log with request summaries;
  - **append-only conversation store** (stores the exact `response.content`).
- `make dev`, `make test`, `make doctor` (Tesseract check), `make reset`.

**Tests:**
- Guard refuses paths outside `DATA_ROOT`, including via symlinks.
- Startup refuses when `EVAL_ROOT` is set.
- AST static test: no file I/O outside `storage/`, and no references to `EVAL_ROOT`/`answer_key`/`truth`.
- Conversation store: appending is the only way to write; an attempt to edit earlier turns raises an error.
- Gateway: refusal → error; transport retry resends a byte-identical body (mocked transport).

**Exit:** all of the above green, plus one live structured call logged.

### M1 — Eval workspace, generator, dataset (3.25 d; slice part a 1.5 + b 1.75) (I7, I10, I3, DL-13, SC-02/03/04)
**Build in `EVAL_ROOT`:**
- A generator with a truth spec. It writes **inputs only** into `DATA_ROOT`: **buyer brief pack** (item master xlsx, quality checklist, commercial policy), **canonical RFx spec** (content-hashed), sandbox RFx, baseline, inbox `.eml` + attachments. Answer keys stay in `EVAL_ROOT`.
- **Canonical-first authoring (DL-19):** the canonical spec is generated first. The brief pack is derived from it, minus the facts the co-pilot must ask for. All five vendor responses are rendered against its SKU codes, descriptions and requirement keys.
- Dataset per PRD §11:
  - 30 lines with an item-type mix, and **documented reference unit weights (with item-master source) for 21 SKUs: 16 RSC, 3 die-cut, 2 pads** (DL-18); 3 `food_contact` lines; **no FSC question and no `requires_fsc` line in the primary RFx** (DL-29); RFx GST basis "prices exclusive of GST" (DL-26);
  - Quality/Commercial questionnaire;
  - V1–V5 with their planted behaviours;
  - **V2 entirely in USD**: every line, freight and terms. Original USD values are present in the artefact (DL-15). Framed as a **domestic converter, USD-linked prices invoiced in INR at the RBI rate on the invoice date** (DL-30).
  - V5 with the exact assignment sentence as message 1 (no attachments), plus **a separate questionnaire submission (message 2)** with the questionnaire, ISO 9001, BCT report and food-grade declaration, and payment terms "No" (DL-23);
  - V5 baseline rows: own + same spec, own + changed spec, and other-vendor-only. Some baseline rows are deliberately on a *delivered* basis, to test that historical freight is never carried forward (DL-8);
  - the 2 V5 group-priced RSC lines **without** reference weight (→ WEIGHT_ESTIMATED);
  - headline eligibility: V1, V2, V5 Pass (quality); V3 Unverified; V4 Fail;
  - 2 die-cut mailers uncovered like-for-like;
  - **document facts (SC-02):** every certificate/report prints type, standard, number, entity, issue and expiry dates. Planted: V3 ISO expired, V4 entity mismatch, V1 provides no FSC certificate (irrelevant to eligibility, since there is no FSC question; used for the "not in the data" check);
  - **edge fixtures per PRD §11:** V2 footnote text; V3 prose terms (5 sentences); V4 per-100 header + 2 unlabelled rows overlapping ≥ 3 per-box lines; V3's 3 missing line numbers fixed in truth.
- **Negative fixtures (EVAL_ROOT only):** **FSC-required RFx variant** (one `requires_fsc` line + an FSC question, DL-29); **food-grade line-level variant** (an eligible vendor without a food-grade declaration); **no-GST-basis RFx variant** (DL-26); **3 item-master header variants** (renamed, reordered, merged headers; DL-27); **V5 freight-estimate variant** (DL-25); V2 footnote scoped "5-ply only"; V2 without a footnote; V3 with a conditional term and with a term removed; V4 high-but-genuine per-box price; a non-conforming RFx draft.
- Photo: synthetic rendered rate card → perspective warp/blur/shadow/JPEG noise, with planted 3/8 and 1/7 ambiguities, **for additional tests only**. The primary fixture is the owner's genuine phone photo (DL-21).
- **Perturbation scope (reduced, I10):** a seed changes values, vendor names and row order, plus **one layout change per format**:
  - xlsx: column order and header row position;
  - PDF: table column order;
  - docx: commercials paragraph order;
  - photo: a different warp angle;
  - email: clause order.
  No new layouts are invented.
- Answer keys: raw values, `unit_source`, expected statuses and reasons, eligibility per question and section, matches, expected scenario outputs for the walkthrough parameters.
- **Banned-literal list** (vendor names, SKU codes, prices) for the prompt hygiene test.
- **V4 print card (SC-08):** render `v4_rate_card_print.pdf` + `v4_rate_card_truth.json` per `12_phone_photo_capture_kit.md` §2 and hand them to the owner. **Register** the owner's original photo (§5 checks: original file hash, camera EXIF, no editing tag, measured skew ≥ 20°) and annotate per-value readability (§6). An AI-generated or edited image is never accepted.
- **Realism review (SC-07):** hand the review pack (`11_dataset_realism_review.md` §2) to a procurement-literate reviewer. Log feedback (§4), apply corrections to the truth spec (§5), regenerate, and have the reviewer re-check (§6). AI self-review is never recorded as external validation.
- **Baseline terms (SC-05):** `BaselineTerm` rows for V5 incl. ≥ 2 term types V5 doesn't state this year. Ground truth for both readings.
- **Arrival subsets (SC-10):** the oracle's expected snapshots after each runbook arrival.

**Tests:**
- Generator deterministic per seed.
- Answer key schema valid.
- **DL-13 dependency lint:** every planted behaviour is tagged with the FR(s) it exercises, and every tagged FR must be P0 in the PRD. The build fails otherwise.
- Eligibility mix assertion: ≥ 3 vendors Pass in quality-strict; ≥ 1 Fail; ≥ 1 Unverified; ≥ 1 uncovered line.
- **USD assertion (DL-15):** V2's artefact has every price in USD and none in INR. Fails the build if the USD vendor scenario is missing.
- **Sandbox isolation (DL-17):** the generator writes the sandbox RFx with no inbox; the prepared five-vendor inputs have a recorded hash.
- **Canonical consistency (DL-19):** every SKU code and requirement key referenced in any vendor artefact exists in the canonical spec. The brief pack plus the runbook's scripted answers contain every canonical value (so a conforming draft is possible). The brief pack does **not** contain the canonical spec file.
- **V5 fidelity lint (DL-23):** the message-1 body equals, byte for byte, "₹42/kg for the 5-ply, 38 for the 3-ply, rest same as last year, freight extra." Message 1 has no attachments. All V5 questionnaire and certificate evidence is in message 2.
- **Edge fixture presence (CLAUDE.md rule 3):** a lint that fails the build if any `EDGE-*` item in `00_source_of_truth.md` lacks a tagged fixture.

**Exit (M1, day ~3.75):** the builder's domain checklist passes (GSM ranges, ±15–25% price spread, plausible terms). Artefacts open correctly in their native apps. The app can't read `EVAL_ROOT` (manual probe + M0 tests). The print card and review pack have been handed over.
**Exit (M1-final, before B2):** the real photo is registered and annotated (DL-21), and `11_dataset_realism_review.md` is signed off by the external reviewer with all "Unrealistic" items resolved (DL-22). Only then is the dataset frozen.

### M2 — Deterministic core (2.25 d; slice part a 0.75 + b 1.5; +0.5 in rev. 4 for DL-26/29)
**Build:**
- `validate/status.py`, the canonical table (PRD §6.2–6.4), as data plus `includable()`.
- **Versioned constant sets (DL-18):** loader with content hash, `validation_status` per constant, activation (audited), the version stamped on every normalised value.
- `normalize/`:
  - slabs (P0);
  - units with dictionary "no opinion";
  - weight with the **weight-source hierarchy** (reference → vendor → estimate → not convertible), the item-type matrix and flute mapping;
  - FX, freight, GST, discounts;
  - baseline per DL-8 (unit price only, no historical freight);
  - money (Decimal).
- `eligibility/` with sections.
- Resolution application (stickiness, fingerprints).

**Tests (golden, table-driven, property-based):**
- **Status table:** every (status × context × policy × override) → includable as specified. Property tests: no `UNRESOLVED`/`NOT_CONVERTIBLE`/`MISSING` cell is ever includable (DL-10); **no `NEEDS_REVIEW` cell is includable in `formal` context without an override record** (DL-16); `exploratory` inclusion always tags the result.
- **§6.3 transformation table:** one test per row (CONVERTED, UNIT_INHERITED, METHOD_CONSTANTS, FX_RATE, group expansion, BASELINE_REFERENCE, freight estimate on landed only, image cap, plausibility cap).
- **DL-18 weight-source hierarchy:**
  - reference weight → CONVERTED, citing its source;
  - vendor weight with no reference → CONVERTED;
  - vendor vs reference beyond tolerance → NEEDS_REVIEW (WEIGHT_MISMATCH), reference used;
  - no reference/vendor weight + complete RSC → NEEDS_REVIEW (WEIGHT_ESTIMATED) + METHOD_CONSTANTS, with the constant-set version and the UNVALIDATED labels in the trace; buyer review → ASSUMED;
  - failed weight evidence → UNRESOLVED;
  - partition with a reference weight → CONVERTED (no formula used); partition without → NOT_CONVERTIBLE.
- **DL-18 constants:** activating a new version → audit + global recompute + scenarios stale; a trace from version N stays reproducible after activating N+1 (hash pinned); **renderer test: no UNVALIDATED constant is shown without its "not validated" label** (UI strings, xlsx, memo).
- **DL-1/DL-12 estimation formulas:**
  - RSC hand-calculated weight (5-ply "BC": B then C mapping);
  - medium/flute count mismatch → incomplete;
  - die-cut with a blank → flat formula;
  - die-cut without a blank → NOT_CONVERTIBLE;
  - partition → `ITEM_TYPE_NOT_WEIGHT_COMPUTABLE`;
  - property test: removing any single input never produces a number;
  - the internal-dimension disclosure is present in the trace.
- **DL-8 baseline** (PRD §5.8 acceptance table): same vendor + same spec → ASSUMED; changed spec → BASELINE_SPEC_CHANGED; other vendor only → BASELINE_NOT_FOR_VENDOR; **never** returns another vendor's price (property test over random baseline tables); **never** returns or applies historical freight (property test: the freight output is independent of the baseline row's freight fields); a delivered baseline + this year's silence → freight UNKNOWN + FREIGHT_BASIS_CHANGED caveat.
- **DL-2** freight table. **DL-3/DL-14** eligibility truth table, including per-section roll-ups and V5 (Quality Pass / Commercial Fail, evidenced only by its message-2 submission, DL-23).
- **DL-24/29 line-level applicability (T-FOOD-01):**
  - the primary RFx has no FSC question, and V1's eligibility is unaffected by having no FSC certificate;
  - food-grade is evaluated per vendor but **excluded from vendor roll-ups**;
  - in the line-level variant, the vendor without a declaration loses **only** its 3 food-contact cells as candidates (strict), and its vendor-level Quality stays Pass;
  - a vendor quoting no food-contact line → NOT_APPLICABLE;
  - the FSC-required variant gates only its `requires_fsc` line.
- **DL-26 GST (T-GST-01):** silent + RFx basis → ASSUMED (GST_PER_RFX_BASIS) with an assumption-ledger entry; silent + no RFx basis → UNRESOLVED (GST_UNCLEAR); ambiguous statement → UNRESOLVED; stated rate → backed out, no status change.
- **DL-31 weight status (T-WGT-01):** reference-weight conversion → ASSUMED (REFERENCE_WEIGHT); vendor-stated → CONVERTED; every per-kg cell has `billed_weight_exposure_per_1pct = 0.01 × qty × ₹/box`. `quality` is the only scope labelled "quality questionnaire".
- **DL-15 FX:** USD → INR at the stated rate; the original is preserved; the trace shows the rate, date and source; a rate edit → recompute.
- Slabs: contained / none / overlapping → SLAB_AMBIGUOUS.
- Unit dictionary: agree / disagree / unseen.
- Money: rounding policy fixtures; no float anywhere (a static check on these modules).

**Exit:** 100% pass; coverage ≥ 90% on `normalize/`, `validate/`, `eligibility/`.

### M3 — Ingestion & extraction (2.5 d)
**Build:**
- Parsers: eml; xlsx; **xls (xlrd)**; csv; **docx via OOXML traversal + footnotes**; pdf digital + scanned; image with **pillow-heif**, OpenCV and Tesseract.
- TEXT extraction (incl. `unit_source`, `unit_inherited_from`, slabs, TOOLING terms).
- **OCR path** and **independent vision path** (separate calls, parallel).
- `reconcile.py`. `verify.py`, including the inheritance check.

**Order:** V5 email → V4 photo → V2 PDF → V3 docx → V1 xlsx.

**Tests:**
- Parser locators.
- docx: the footnote is captured, and paragraph/table order is preserved.
- `.xls` and `.heic` fixtures parse.
- Corrupt file → FAILED.
- **Vision independence (B4):** request inspection. The vision call payload contains none of the OCR line strings.
- **Reconciliation fixtures:** agree → EXTRACTED cap; differ → READ_DISAGREEMENT; one-sided → READ_SINGLE_SOURCE; low confidence → LOW_OCR_CONFIDENCE; a path disagreement never yields EVIDENCE_NOT_FOUND.
- **DL-12 inheritance (B5):**
  - On the exact sentence "₹42/kg for the 5-ply, 38 for the 3-ply, rest same as last year, freight extra": 38 → PER_KG, INHERITED_FROM_CONTEXT, citing the "₹42/kg" span.
  - Negative fixtures: the unit is in a different, non-adjacent message → UNKNOWN; another unit token sits in between → UNKNOWN.
- **Live extraction eval (`make eval-extract`, run from EVAL_ROOT over HTTP):** field accuracy; unit_source accuracy; flags on the planted items; **silent errors = 0**.
- **Document facts (SC-02, live):** for every planted certificate/report, the extracted `DocumentFact` fields (type, standard, number, entity, issue/expiry) equal ground truth, each with a verified evidence quote. Fields not printed → `NOT_EXTRACTED` (null), never guessed.
- Prompt hygiene against the banned-literal list.

**Exit:**
- raw price accuracy ≥ 90%;
- every planted photo ambiguity is read correctly by both paths, or is UNRESOLVED;
- silent errors = 0.

### M4 — Matching, Phase A/B, recompute, re-run (1.5 d)
**Build:**
- `match.py`, with group expansion that targets all item types of the ply.
- `phase_a.py` (concurrency 5).
- `phase_b.py` (global lock, canonical order, leave-one-out medians, B checks, resolutions, statuses, roll-ups, review items, snapshot hash, stale marking).
- `recompute.py`.
- **P0 basic re-run** with carry-forward by fingerprint.
- Provisional/final state.

**Tests:**
- **Order-shuffle determinism (B2):** 10 random completion orders → identical snapshot hash.
- **Peer independence:** changing one vendor's Phase B status doesn't change any other vendor's peer median (medians come from Phase A values).
- **Global recompute (VAL-5):** correcting V4 line 7 re-evaluates every vendor's line-7 cell. An accepted cell gets `NEW_WARNING_AFTER_REVIEW` and is not downgraded.
- **Carry-forward:** a re-run with an identical raw fingerprint keeps the resolution; a changed fingerprint → STALE_SOURCE_CHANGED and the item reopens; override behaves the same way.
- Matching eval ≥ 95%. The shuffled V1 matches identically. ALTERNATE on V2's mailers.
- **Group expansion + hierarchy (B5, DL-18):** V5's 3-ply partition → NOT_CONVERTIBLE (ITEM_TYPE_NOT_WEIGHT_COMPUTABLE); 3-ply RSC with reference weight → CONVERTED + ASSUMED (UNIT_INHERITED); the 2 RSC without reference weight → NEEDS_REVIEW (WEIGHT_ESTIMATED); die-cut with no blank → NOT_CONVERTIBLE.
- E2E Phase A + B on the full inbox vs the answer key (values to ₹0.0001, or the expected non-numeric status; expected reasons).
- AI failure injection → FAILED, no partial rows, Phase B waits or is reported.

**Exit:**
- full inbox < 4 min;
- §1.2 targets met;
- silent errors = 0;
- the snapshot hash is stable across runs from stored raw facts.

### M5 — Comparison, provenance, review (3.0 d; slice part a 0.5 + b 2.5; +0.5 in rev. 4 for DL-28 ordering and the DL-32 pack)
**Build:**
- Grid (canonical badges; excluded statuses as chips; basis toggle; baseline column; Provisional banner).
- Vendor panel with Quality/Commercial sections (DL-14); food-grade shown per food-contact line (DL-29).
- **Review queue ordered decision-sensitive first (DL-28)**, with a sensitivity badge and quantified impact on each item.
- **Clarification pack (DL-32):** per-vendor pack preview (template sections by item kind, sensitivity-ordered) → edit → approve → outbox. The DL-20 reference section is included.
- "As quoted" view shows V2's original USD values (DL-15).
- Best-price highlight uses the formal policy (NEEDS_REVIEW shown with a warning, never highlighted, DL-16).
- Settings: FX rate/date/source; constant-set view with validation labels; activate a version (audited).
- Provenance drawer, including **both photo reads side by side**.
- Review queue (blocking first).
- Resolutions and overrides (reason required).
- FX/freight editors. Every action triggers a global recompute.

**Tests:**
- API contracts.
- No numeric rendering for excluded statuses.
- Landed view never shows a number for UNKNOWN freight.
- Resolution → recompute < 2 s → audit event.
- `EligibilityLabel` mapping (Unverified is never "Failed").
- Playwright: V4 cell → both reads + crop → choose a reading → the value updates and peers on the line are re-evaluated.

**Exit:** a timed self-run clears the queue in < 30 min.

### M6 — Co-pilot and distribution (2.0 d; eval and rehearsals in B3) (I10, DL-19)
**Build:**
- **Co-pilot (1.5 d):**
  - structured turns on an append-only conversation;
  - **brief-pack attachments parsed into EvidenceUnits, with patch citations (RFX-9)**;
  - **deterministic item-master import (DL-27):** AI column mapping on header + 3 sample rows → buyer confirms → rows imported by code (no model output contains line values) → completeness and gap list → AI gap questions;
  - JSON-Patch validation (sections, requirement keys, construction completeness, reference weight requires a source);
  - diff/apply;
  - **conformance check (RFX-10)**;
  - **RFx provenance + labelled seeded fallback (RFX-11)**;
  - sandbox RFx (DL-17).
- **Distribution (0.5 d):** outbox, deliver inbox, status board (DIS-2), upload to an existing or new vendor, runbook note (the sandbox receives uploads only).

**Tests:**
- **T-IMP-01 (det, DL-27):** the import of the demo item master equals the file cell-for-cell (30/30 rows, every mapped field). Each line cites its row. The gateway log shows no model output containing line values. The mapping proposals for 3 header-variant fixtures are correct, or flagged low-confidence and left to the buyer, never silently wrong.
- **Co-pilot eval:** ~12 scripted instructions at ≥ 90% (mapping, gap questions incl. GST basis, questionnaire/terms drafting, edits). Invalid patches are rejected and never applied.
- **Sandbox isolation (DL-17):** after a scripted live-drafting session on the sandbox, the canonical spec and the prepared five-vendor inputs/results have an unchanged snapshot hash.
- **Live primary-RFx rehearsal (DL-19, live):** 5 runs of runbook P1–P3 (brief pack + scripted answers) → conforms in **≥ 4 of 5** runs, each within the import/mapping budget (architecture §16). Every line and question patch carries a brief-pack citation.
- **Conformance unit tests:** identical → conforms. One GSM changed / one line deleted / one quality question dropped / response basis changed → exactly that difference is reported.
- **Co-pilot isolation:** request inspection shows the canonical spec content is never sent to the model (PRD AI-17).
- **Delivery gate:** delivering the inbox to a non-conforming RFx → refused (409). After conformance → delivered.
- **Provenance:** the primary RFx shows `origin = COPILOT_LIVE` + transcript; the fallback shows `SEEDED_FALLBACK`.
- Upload of a perturbed-variant file → the same pipeline + global recompute.

**Exit:** J1, J2, J3, J8 demoable.

### M7 — Scenarios, savings, readiness (2.25 d; slice part a 0.25 + b 2.0; +1.25 in rev. 4 for DL-25/28/30/31) (I4, B6)
**Build:**
- `scenario.py` (params per AWD-1; **no cap**; `context` formal/exploratory; default `exclude_needs_review`; **default basis `freight_aware` for formal, with FREIGHT_DEPENDENT flags and break-even, DL-25**).
- `sensitivity.py` (DL-28): per-line re-evaluation for candidates, excluded needs-review values, flip margins (FX, reference weight) and break-even freight.
- Exposure caveats (DL-30/31): V2 FX exposure per 1%; billed-weight exposure per 1%.
- Readiness: freight-dependent lines need an audited acknowledgement; decision-sensitive lines and exposures are listed.
- **NEEDS_REVIEW override (DL-16):** per-scenario override dialog API (warning payload with cells and money at risk; reason required; AuditEvent).
- `savings.py` (PRD §5.9 exactly).
- Readiness check.
- Stale/superseded handling.

**Tests: independent oracle parity.** `EVAL_ROOT/oracle/` reimplements the PRD §5.9/§6 rules directly from the answer key. It shares no code with the app. On 20 parameter combinations (scope, mode, alternates, basis, context/status policy, exclusions), the outputs must match exactly:
- totals;
- per-line awards;
- uncovered lines;
- exclusions (Failed vs Unverified);
- savings vs baseline with the coverage statement (N of M lines, ₹X, Y%);
- the best-single-vendor comparator choice and coverage.

Plus:
- VP question fixture: eligible V1/V2/V5; V3 Unverified and V4 Failed listed separately; the 2 mailers uncovered; including alternates covers them via V2; **V5's 2 WEIGHT_ESTIMATED lines and all OUTLIER cells excluded under the formal default** and listed in the readiness check.
- **DL-16 policy tests:** a formal scenario with `include_needs_review` and no override → rejected; with an override → warning payload + AuditEvent + memo listing; an exploratory result promoted to Award → recomputed under the formal policy and the totals change accordingly.
- Determinism: byte-identical outputs.
- Changing the FX rate marks saved scenarios stale and supersedes acknowledged awards.

**Exit:** full oracle parity.

### M8 — NL analyst (2.0 d; eval sets and tuning in B4) (I2, I8, I9)
**Build:**
- Views (incl. `includable_formal`, `needs_review`, original currency, weight source, eligibility by section) + SQL guard.
- Tools (`query`, `run_scenario`, `get_eligibility`, **`get_evidence`**, `make_chart`, `export`; `fx_sensitivity` is P1).
- **Document and answer views (SC-02):** `v_questionnaire_answers`, `v_document_facts`, `v_certificates` (derived validity by code), `v_evidence_index` (no text). Coverage columns on `v_vendors`.
- Grounding extended to dates, certificate numbers and entity names. Caveat engine adds coverage disclosure and fact source links.
- Steering to `run_scenario`.
- Caveat engine (Failed vs Unverified).
- Grounding check.
- **Label lint.**
- **Append-only regeneration.**
- Show work. SSE.

**Independent analyst correctness tests (new, I8):**
1. **View correctness:** each approved view, **including the document and answer views**, is checked row by row against the oracle's table built from the answer key.
1a. **Document-access guardrails (SC-02):**
   - no view or tool returns full document text (schema test);
   - `get_evidence` refuses refs not cited by any fact, answer or quote row;
   - snippets are ≤ 400 chars and wrapped as untrusted;
   - a planted instruction inside a vendor document ("ignore previous instructions…") has no effect on the answer.
1b. **Document-fact questions (oracle):**
   - "Whose ISO 9001 certificate is valid through the contract period?";
   - "Which certificates are in a different legal entity's name?";
   - "What did V3 say about lead time?";
   - expected answers from the oracle; every fact carries a source link (NLA-12).
1c. **No invention (NLA-13):** "When does V1's FSC certificate expire?" → "not in the data" (V1 has none). Questions about unextracted fields → "not stated". **Target 100%.**
2. **Oracle question set:** about 25 questions (walkthrough, off-script, trap). Expected values are computed by the oracle. Scoring:
   - numeric correctness at displayed precision;
   - the required sections are present;
   - the interpretation is stated where applicable;
   - **analyst silent error** = a wrong number with no stated interpretation or caveat explaining it. **Target 0 on the walkthrough set.**
3. **Tool-route check:** for award, split and savings questions, every narrative number traces to a `run_scenario` result.
4. **Metamorphic tests** (no expected values needed):
   - excluding a vendor never lowers a cheapest-per-line total;
   - including alternates never raises it;
   - inclusive mode never has fewer eligible vendors than strict;
   - raising the USD rate never lowers V2's INR prices;
   - adding an UNRESOLVED cell never changes any total.
5. **Replay determinism:** re-executing the stored tool calls of an answer reproduces identical result tables.
6. **Trap set:**
   - out-of-data questions → declined;
   - an ambiguous question → interpretation stated;
   - "on what grounds did the others fail?" → premise corrected, V3 described as Unverified;
   - landed cost with unknown freight → excluded and disclosed;
  - "include the values that need review" → the answer is labelled "Exploratory — includes N values needing review" and never presented as an award figure (DL-16);
  - "did V5 clear the quality questionnaire?" → yes (Quality section), with the commercial result reported separately (DL-14);
   - "who failed?" under the commercial scope → V5 included only in that scope.
7. **Label lint unit tests:** positive and negative sentences, Unicode vendor names.
8. **Conversation integrity:** a grounding failure triggers regeneration with the earlier turns byte-identical (inspected on the stored history). A permanently failed turn is not appended and the next question succeeds.

**Exit:**
- ≥ 90% numeric correctness on walkthrough + off-script;
- analyst silent errors = 0 on the walkthrough set;
- 100% trap-set behaviour;
- 100% grounding pass after regeneration;
- 0 "failed" labels on Unverified vendors.

### M9 — Memo, exports, audit (0.5 d)
**Build:** memo (grounded and linted rationale; alternates listed when included; savings coverage statements); xlsx with all sheets; analyst table export; audit view.
**Tests:**
- Memo numbers equal the scenario output.
- The memo lists any NEEDS_REVIEW override and its cells (DL-16), shows the constant-set version with "not validated" labels (DL-18), and the FX rate/date (DL-15).
- The xlsx Sources row exists for every numeric cell.
- Eligibility wording in exports and memo (Unverified ≠ Failed).
- The acknowledgement writes an audit event. A superseded marker appears after an FX change.

**Exit:** J7 end to end.

### MT — Testing, evaluation & integration workstream (5.25 d)
Items B1–B7 are as in §2.3. The **test definitions stay in their milestones** (M1–M9 and §3a). MT is the budgeted time to **run, tune, integrate and fix** against them. B7 now contains the unseen-seed perturbation, the DL-13 and final-decision re-checks, the unseen-file drill, the resilience drills, `make demo-warm` + the live re-run check, and the performance pass, all listed below.

### M10 — Demo preparation (2.0 d; C1–C3). The B7 items are listed here for continuity but budgeted in MT.
- **Unseen-seed perturbation:** draw a new seed (recorded in the report), regenerate → extraction, analyst and oracle evals hold, with no code or prompt changes.
- **DL-13 re-check:** the walkthrough script and the dataset touch only P0 FRs (lint + manual pass over the runbook).
- **Final-decision check (FD-1…FD-6):** run the DL-14…DL-18 tests from §5.2 together. The USD vendor scenario is present (DL-15). The sandbox hash is unchanged after the drafting demo (DL-17).
- **Unseen-file drill (DL-4, optional in the demo):** 3 fresh files. Only generic fixes are allowed.
- **Drills:**
  - network loss mid-extraction;
  - a corrupt upload;
  - an FX change that flips a V2 line (NRM-4, P0; the P1 sensitivity tool isn't needed);
  - analyst API failure mid-conversation (then a follow-up question succeeds);
  - re-run with changed output.
- `make demo-warm` (the real pipeline) + a check of the live P0 re-run.
- Performance pass.
- **Recorded walkthrough (D-2)** following the runbook §4 question set (Q1–Q10, including the document-fact question Q7).
- **One-page note (D-3/D-4, SC-06):** source `docs/deliverables/one_page_note.html`, output `one_page_note.pdf`.
  - **Content:** the 10 most important decisions, each with its "why", mapped to DL-1/9/10 (AI reads, code calculates), DL-10/16 (uncertainty and formal award), DL-11 (independent photo reads), VAL-3/DL-10 (per-100 never auto-fixed), DL-1/18 (weight conversion and constants), DL-20 (rest same as last year), DL-2 (freight), DL-3/14 (quality questionnaire, Unverified ≠ Fail), DL-6 (alternates), DL-19 + grounding/label lint/isolation (one honest flow); plus deliberate exclusions (PRD §13 and the P1 list); plus the better-problem hypothesis (brief §11).
  - **Rule:** if any listed decision changes, update the note, regenerate it with headless Chrome print-to-PDF (A4) and re-run **T-NOTE-01**.
- **Demo runbook (`docs/10_demo_runbook.md`, SC-01/SC-04):** pre-flight → **one primary RFx from live co-pilot creation (P1) to export (P11)** → edge-case matrix walk-through → sandbox segment → optional upload → contingencies. Exit requires the runbook §7 evidence checklist to be complete.
- **Runbook-to-test check:** every row of runbook §3 points to a passing T-EDGE test (§3a).

**Exit:** two clean dry runs of the panel-driven demo.

---

## 3a. Named edge-case test suite (SC-03; CLAUDE.md rule 3)
Every `EDGE-*` item in `00_source_of_truth.md` has a named test that asserts **behaviour**, not just successful processing. Tests marked *(det)* run on stored raw facts and are deterministic, gated on every commit. Tests marked *(live)* run real extraction against the fixture and compare to ground truth (`make eval`).

| Test | SOT | Milestone | Assertions (all must hold) |
|---|---|---|---|
| T-EDGE-01 | EDGE-01 | M3, M4 | (live) V1 lines extracted with `sheet!cell` locators. Matches equal ground truth after a row shuffle and the layout-variant fixture. Slab selected = the annual-qty slab. Tooling row is a `DocumentTerm(TOOLING)` and is matched to **no** RFx line. |
| **T-EDGE-02** | **EDGE-02** | M2 (det), M3 (live) | (live) A `DocumentTerm(DISCOUNT_PCT, value 5, scope ALL)` exists, its evidence locator is the **footnote block** on the cited PDF page, and its quote contains "5%". (det) Every in-scope V2 trace has the discount at **step 5** (after unit/qty conversion, before GST and FX). Each V2 unit price equals ground truth to 4 dp (i.e. ×0.95 applied once, never twice). Provenance shows the footnote ref. **Negatives:** the "5-ply only" variant discounts only 5-ply lines; the no-footnote variant applies no discount; the discount never appears on another vendor. |
| **T-EDGE-03** | **EDGE-03** | M3 (live), M4 (det) | (live) V3 yields exactly the 5 planted commercial terms (payment days, freight basis, validity, lead time, escalation condition), each with the correct value and unit and with evidence `para_idx` whose text contains the cited quote. (det) V3's freight basis from prose drives its landed values per PRD §5.4. V3's payment-terms answer drives the Commercial eligibility result. **Negatives:** the conditional term is captured with its condition (or flagged `unclear_scope`), never as unconditional; the removed-term variant yields **no** such term (absent, not invented). |
| T-EDGE-04 | EDGE-04, EDGE-06 | M3, M5, B2 | (live) **Primary: the genuine phone photo (DL-21)**, scored against the per-value human-readability annotations (`clear`/`difficult`/`human_unreadable`, capture kit §6). **Additional: the synthetic warps.** Independent reads. Reconciliation outcomes match ground truth per planted ambiguity. A wrong value shown as EXTRACTED = failure. Image values capped at EXTRACTED. Playwright resolve path. The photo manifest proves camera EXIF and no editing tag. |
| T-EDGE-05 | EDGE-05 | M3, M4 | (live) The V5 email produces per-line values for every RFx line whose ply is 3/5/7. Components as below. |
| T-EDGE-05a | EDGE-05a | M4 | (det) 5-ply lines with a reference weight = 42 × weight (CONVERTED, item-master citation). Without one → NEEDS_REVIEW (WEIGHT_ESTIMATED). Partitions → NOT_CONVERTIBLE. |
| T-EDGE-05b | EDGE-05b | M3 | (live) "38" → PER_KG, INHERITED_FROM_CONTEXT, both spans cited → ASSUMED (UNIT_INHERITED). Negative fixtures → UNKNOWN. |
| T-EDGE-05c | EDGE-05c | M2, M4 | Superseded by **T-EDGE-05c-A** and **T-EDGE-05c-B** (DL-20) below. |
| T-EDGE-05d | EDGE-05d | M2 | (det) Freight UNKNOWN. Landed not calculable. The delivered baseline is not carried forward. |
| **T-EDGE-07** | **EDGE-07** | M4 (det), M7 (det), M8 (live) | (det) V3 has exactly the 3 ground-truth line numbers as MISSING, with no value, never filled by any path (property: changing other vendors' prices on those lines never changes any V3 figure). V3's single-vendor total is over 27 lines and labelled "27/30". In `run_scenario` and comparator output, the coverage statement names V3's missing lines. (live, analyst) For Q1 "cheapest overall", Q3 "who didn't quote everything" and Q5 "VP split", the code-generated exclusions/caveats contain "V3: 27/30" **and** the three line numbers. Q3's narrative names V3 and the count 3 (grounded). An answer that ranks V3 without the coverage disclosure fails. |
| T-EDGE-08 | EDGE-08 | M1, M2, M5, M7 | (det) Every V2 price is in USD in the artefact. INR = USD × rate (4 dp). Original preserved. Rate/date/source in the trace. A rate edit → recompute, scenarios stale, awards superseded. |
| **T-EDGE-09** | **EDGE-09** | M2 (det), M3 (live), M4 (det), M5 (UI) | (det) "₹480 per 100 nos" → 4.8000 (CONVERTED); "Rs 4,800/1000 pcs" → 4.8000; "₹4.80 each" → 4.8000. (live) V4's header-labelled rows → `unit_class=PER_100`, `unit_source=STATED`. (det, Phase B) V4's 2 unlabelled rows with ~100× the peer median → **UNRESOLVED (UNIT_SUSPECT)** with the suggestion "per 100 → ₹x/box", **excluded** from every total (scenario total = oracle total without them). Buyer accepts the suggestion → VERIFIED at the suggested value, and the line's peer statuses are recomputed. **Cross-vendor comparability:** on the ≥ 3 overlapping lines, V4's normalised per-box value is within ground-truth tolerance of V1/V5's per-box values, and the grid ranks them on the same basis. **Negative:** the high-but-genuine per-box fixture (~1.5× median) is **not** flagged UNIT_SUSPECT (at most OUTLIER/NEEDS_REVIEW). |

| **T-EDGE-05c-A** | EDGE-05c, reading A (prices) | M2 (det), M4 (det) | (det) Before confirmation, every V5 7-ply cell is UNRESOLVED: REFERENCE_AMBIGUOUS where V5 has a same-spec row (candidate = that row, cited), BASELINE_SPEC_CHANGED / BASELINE_NOT_FOR_VENDOR otherwise. Every scenario/analyst total excludes them (equals the oracle without them). Property: **no code path applies a candidate without an active REFERENCE_CONFIRMATION**, and no candidate ever comes from another vendor. After "prices": only the same-spec cells become ASSUMED (BASELINE_REFERENCE) and totals change by exactly qty × candidate. After "neither": unchanged. |
| **T-EDGE-05c-B** | EDGE-05c, reading B (terms) | M2 (det) | (det) Unstated V5 term types (from ground truth) appear as unresolved term candidates taken from V5's own `BaselineTerm`. Before confirmation they affect **no** calculation and **no** eligibility result (Commercial results equal the oracle with the terms absent). **Freight is never a candidate:** V5 freight stays UNKNOWN in every state. After "terms": each candidate becomes `DocumentTerm(CONFIRMED_HISTORICAL)` with status ASSUMED and an audit record. After "prices" only: terms remain unresolved. |
| **T-CLAR-01** | EDGE-05c (DL-20 clarification) | M5 (det) | The generated request contains the vendor's phrase, **both** readings, every reading-A line with its candidate (or "no candidate: reason"), every reading-B term with its candidate, and two direct questions. Byte-identical for identical inputs (template, no AI call; the gateway log shows no call). Not in the outbox before buyer approval. After approval: one outbox message to V5. |
| **T-OUT-01** | FN-14 (charts, SC-09) | M8 (det), B5 | For each chart the analyst eval produces, the bound `data.values` equal the referenced result rows (same count; Decimal-text equality per field). The x/y/series fields exist in the result. A spec with inline data or value-creating transforms is rejected. Vendor and line labels match the result's vendor names and line numbers. |
| **T-OUT-02** | FN-15 (analyst exports, SC-09) | M8/M9 (det), B5 | Exported xlsx and csv, re-read: same row count; every value equals the result row (Decimal text); vendor name **and** id, line numbers, unit/currency labels and status/flag columns present and correct; Exclusions/Caveats included (incl. awaiting vendors and unresolved references). |
| **T-OUT-03** | FN-15, FN-06 (comparison export, SC-09) | M9 (det), B5 | Comparison xlsx: each cell equals the grid's value and status for the same basis. Excluded/awaiting cells are exported as status text, never numbers. Every numeric cell has a Sources row. Vendor columns are in the same order with the same names as the grid. |
| **T-ARR-01** | EX-02 (staggered arrival, SC-10) | M4 (det), B5 | After each of the **6 deliveries** in runbook order (V5 quote, V5 questionnaire submission, V1, V3, V4, V2; DL-23), the comparison snapshot equals the oracle snapshot for that subset of responded vendors. Awaiting vendors have **no** NormalizedQuote rows (property), are never 0 or MISSING, and appear in `awaiting_response`. |
| **T-ARR-02** | EX-02 (order independence) | M4 (det) | 3 different arrival orders → identical final snapshot hash, equal to the all-at-once snapshot. |
| **T-ARR-03** | EX-02 (answers and award) | M7/M8 (det + live), B5 | With V2 awaiting: the VP-split scenario excludes V2 and lists "Awaiting response: V2". The best-single-vendor comparator ignores V2. Eligibility shows "Not assessed — awaiting response" (never Unverified/Fail). The award readiness check lists V2 and requires an acknowledgement. Live analyst answers include the awaiting exclusion (code-generated). |
| **T-DOC-01** | FN-10 (documents, SC-11) | M5 (det) | `GET /vendors/{id}/documents` lists every attached document per vendor with type and facts. `GET /documents/{id}/file` returns bytes whose SHA-256 equals the stored hash, with the correct content type. `GET /documents/{id}/view?evidence_ref=` returns the viewer with that evidence highlighted. Unknown or foreign ids → 404. |
| **T-DOC-02** | FN-10 (UI, SC-11) | M5 (Playwright) | From the comparison workspace, each of the 4 entry points (vendor panel, questionnaire-answer row, document-fact row, provenance drawer) opens the right document at the cited page/region. "Download original" yields the stored file. |
| **T-NOTE-01** | DEL-03/04 (SC-06) | M10 (C3) | The note PDF has exactly **1** page (page-object count = 1 and `/Count 1`). The text contains a "What I decided" and a "What I deliberately left out" section. Every decision referenced in the footer exists in PRD §0.1. Re-run whenever the note is regenerated. *(Pre-build run passed on 2026-11-04.)* |

| **T-FRT-01** | DL-25 (P0-1) | M7 (det), B5 | On the VP split (oracle): every line where V5 (unknown freight) wins on unit price against a K candidate is FREIGHT_DEPENDENT, with break-even = best_K − best_U to 4 dp. Lines where a delivered or stated-freight landed cost ≤ every UNKNOWN unit price go to that K vendor with `ROBUST`. A line with K empty → FREIGHT_UNKNOWN_ALL. Savings on dependent lines are marked lower bounds. |
| **T-FRT-02** | DL-25 | M7 (det) | The readiness check lists every FREIGHT_DEPENDENT line with its break-even. Acknowledging writes an AuditEvent and is required to proceed. In the V5 freight-estimate variant, the estimate (ESTIMATED) removes the flag, and the winner recomputes on landed. |
| **T-FRT-03** | DL-25 | M8 (live), B5 | The VP question answer contains (code-generated) the freight-dependent lines and break-evens. The grounding check passes on those numbers. |
| **T-GST-01** | DL-26 (P0-2) | M2 (det) | Silent + RFx basis → ASSUMED (GST_PER_RFX_BASIS) with a ledger entry. Silent + no basis → UNRESOLVED (GST_UNCLEAR). Ambiguous → UNRESOLVED. Stated → backed out. V5 cells (demo) → ASSUMED. |
| **T-IMP-01** | DL-27 (P0-3) | M6 (det) | See M6: exact import, no model-generated line values, header variants. |
| **T-SENS-01** | DL-28 (P1-5) | M7 (det), B5 | For every line (oracle): `sensitive` is correct. Planted cases: a V4 READ_DISAGREEMENT whose other reading would win the line; a V5 REFERENCE_AMBIGUOUS candidate that would win if confirmed; an excluded NEEDS_REVIEW cell that would win if included; an FX flip margin on a V2-won line. Impacts equal the oracle (₹ to whole rupees, margins to 0.1%). A line with no uncertain input → not sensitive. |
| **T-SENS-02** | DL-28 | M5 (UI/API) | The review queue lists decision-sensitive items first, by impact. Badges show the impact. The readiness check lists sensitive lines. |
| **T-FOOD-01** | DL-29 (P1-9) | M2 (det) | See M2: line-level gating, vendor roll-up unaffected, FSC absent from the primary RFx, FSC-required variant gates only its line. |
| **T-FX-01** | DL-30 (P1-10) | M7 (det) | V2 FX exposure = 0.01 × Σ INR value of V2 cells used, to whole rupees, in scenario output, readiness and memo. V2's terms show "invoiced in INR at the rate on invoice date". The USD originals are still shown (EDGE-08 preserved). |
| **T-WGT-01** | DL-31 (P1-11) | M2 (det), M7 (det) | Reference-weight conversions are ASSUMED (REFERENCE_WEIGHT). Billed-weight exposure per 1% = 0.01 × Σ (qty × ₹/box) over per-kg lines used. |
| **T-PACK-01** | DL-32 (P1-6) | M5 (det), B5 | For each vendor, the pack contains exactly the important vendor-resolvable items from ground truth (blocking unit/read/GST/conflict/slab, freight on FREIGHT_DEPENDENT or sensitive lines, evidence for Unverified quality questions, the reference section, uncovered lines the vendor didn't quote), ordered by sensitivity rank. Byte-identical for identical inputs. No AI call. Not in the outbox before approval. Advisory-only items (e.g. OUTLIER on a non-sensitive line) are excluded. |
| **T-SLICE-01** | P0-4 | S (det + live) | The day-6.5 vertical slice runs end to end on the primary RFx (import → send → V5 ×2 + V1 → extraction → grid → VP question → draft memo) in one scripted run, with the expected statuses for the slice subset. |

**Gate:** the M10 exit requires every T-EDGE, T-CLAR, T-OUT, T-ARR, T-DOC, T-FRT, T-GST, T-IMP, T-SENS, T-FOOD, T-FX, T-WGT, T-PACK, T-SLICE and T-NOTE test to pass on the demo dataset **and** (where data-dependent) on the unseen-seed variant.

## 4. Testing strategy

### 4.1 Layers
| Layer | What | Where | Gate |
|---|---|---|---|
| Unit / golden / property | status table, normalisation, baseline DL-8, weight matrix, eligibility, money, Phase B, resolutions, scenario, savings, SQL guard, grounding, label lint, **conformance** | `backend/tests` | every commit |
| **Named edge-case suite (§3a)** | T-EDGE-01…09 (det parts every commit; live parts in `make eval`) | both | every commit / M3, M4, M8, M10 |
| **Document access (SC-02)** | views, `get_evidence` refusal, snippet cap, injection, no invention | both | M8, M10 |
| Static | storage guard usage, no truth references, no floats in money modules, prompt hygiene | `backend/tests` + EVAL_ROOT list | every commit |
| Determinism | order-shuffle snapshot, scenario byte-identity, replay of tool calls | `backend/tests` | every commit |
| Contract / E2E | API shapes; Playwright smoke | `backend/tests`, `frontend` | M5, M9, M10 |
| Extraction / matching eval | accuracy, unit_source, flags, silent errors | EVAL_ROOT over HTTP | M3, M4, M10 |
| **Oracle parity** | scenarios, savings, eligibility exclusions | EVAL_ROOT | M7, M8, M10 |
| **Analyst correctness** | view tests, oracle Q-set, tool-route, metamorphic, trap set, analyst silent errors | EVAL_ROOT | M8, M10 |
| Co-pilot eval | patch correctness, completeness questions | EVAL_ROOT | M6, M10 |
| Isolation | guard, startup refusal, AST scan, manual probe | both | M0, M1, M10 |
| Resilience | AI failures, corrupt files, recompute, conversation integrity | both | M4, M8, M10 |

### 4.2 Independence rule
- The oracle in `EVAL_ROOT/oracle/` is written directly from the PRD rules and the answer key. It imports nothing from the app.
- Eval tests talk to the app only over HTTP. The app never sees `EVAL_ROOT`.

### 4.3 Live-model tests
These are marked `@live`, run via `make eval`, and the reports are saved with model, prompt version, seed and date.

---

## 5. Traceability

### 5.1 P0 FR → milestone owner (I10)
| FR | Owner | FR | Owner |
|---|---|---|---|
| RFX-1/2/3/4/5/6/8/9/10/11 | M6 (schema in M0; canonical spec in M1) | CMP-1/2/3/4/5/6/7/8 | M5 |
| DIS-1/2/3 | M6 | ELG-1/2/3/4/5 | M2 (rules), M5 (UI) |
| EXT-1…10, 13, 14 | M3 | ELG-6 | M5 (labels), M8 (lint), M9 (memo) |
| EXT-11 (basic re-run) | M4 | NLA-1…5, 7, 9, 10, 11, 12, 13 | M8 |
| MAT-1…5 | M4 | AWD-1/2/3/7 | M7 |
| NRM-1…8, 10…13 | M2 (rules), M4 (integration) | AWD-4/5 | M9 |
| NRM-9 (separation) | M3 (detect) + M2 | EXP-1/2/3 | M9 |
| VAL-1/2/4/6 | M2 | AUD-1/2 | M5 (write), M9 (view) |
| VAL-3/5 | M4 | NF-9 isolation | M0, M1 |
| **REV-1/2/3/4** (review queue, sensitivity sorting, source view, actions incl. Confirm reference) | **M5** (implements and tests the review queue; dataset validation itself is M1) | **J9 (P0): deterministic clarification pack (DL-32) incl. the reference section (DL-20), approval → outbox** | **M5** (implementation + T-PACK-01/T-CLAR-01 det), **B5** (suite) |
| AWD-1/2/3 freight-aware selection, break-even, sensitivity, exposures (DL-25/28/30/31) | M7 | NRM-6 GST silence (DL-26); ELG line-level gating (DL-29) | M2 |
| RFX-9 deterministic import + AI mapping (DL-27) | M6 | Vertical slice (P0-4) | S |
| Linking several submissions to one Response (DL-23) | M3 (ingestion) + M4 (recompute) | Question applicability / NOT_APPLICABLE (DL-24) | M2 (rules), M5 (panel display) |
| AI-1…5, 14, 15, 16 (extraction behaviour) | M3 | AI-6, 7, 12 (analyst loop, grounding, label lint) | M8 |
| AI-8, 17 (co-pilot) | M6 | AI-9, 10, 13 (call log, failure handling, append-only store) | M0 (gateway), M8 (analyst use) |
| AI-11 (ground truth unreachable) | M0, M1 | NF-1…4 (latency budgets) | M3, M4, M8 (build); B7 (performance pass) |
| NF-5 (determinism) | M2, M4 | NF-6, NF-7 (local data; one-command setup + `make doctor`) | M0 |
| NF-8 (demo resilience: stored results + re-run) | M4 (re-run), M10 (warm run) | DL-21/22 external inputs | M1-final |

**Every P0 FR, AI requirement and NF requirement in the PRD now has an owner.** P1 items (RFX-7, REV-5, EXT-11b, NLA-6/8, AWD-6, NRM-9 amortisation, fx_sensitivity, **J9b: AI-drafted clarification emails for generic review items**) have no owner until all P0 exits are met.

### 5.2 Locked decisions → tests
| Decision | Validating tests (milestone) |
|---|---|
| DL-1 | weight matrix + removal property test (M2); group expansion matrix (M4) |
| DL-2 | freight table (M2); landed-view rendering (M5); landed-basis scenario (M7) |
| DL-3 | eligibility truth table (M2); label component (M5); label lint + trap set (M8); memo wording (M9) |
| DL-19 | canonical consistency (M1); conformance unit tests, live primary-RFx rehearsal ≥ 4/5, co-pilot isolation, delivery gate, provenance (M6); runbook P1–P11 dry run (M10) |
| DL-20 | T-EDGE-05c-A, T-EDGE-05c-B, T-CLAR-01 (M2, M4, M5) |
| DL-21 | T-EDGE-04 on the real photo + manifest/EXIF check (M1-final, B2) |
| DL-22 | M1-final exit: `11_dataset_realism_review.md` signed off by a procurement-literate reviewer (manual gate, not automatable) |
| DL-23 | V5 fidelity lint (M1); T-ARR-01 with the separate submission (M4/B5); eligibility truth table V5 evidence (M2) |
| DL-24 | Applicability truth table (M2); panel text (M5). *Amended by DL-29: see T-FOOD-01.* |
| DL-25 | T-FRT-01/02/03 |
| DL-26 | T-GST-01 |
| DL-27 | T-IMP-01; B3 rehearsals |
| DL-28 | T-SENS-01/02 |
| DL-29 | T-FOOD-01 |
| DL-30 | T-FX-01; EDGE-08 tests unchanged |
| DL-31 | T-WGT-01 |
| DL-32 | T-PACK-01 (+ T-CLAR-01 for the reference section) |
| DL-4 | upload via the same pipeline (M6); unseen-file drill (M10) |
| DL-5/DL-8 | baseline acceptance table + never-other-vendor property (M2); E2E V5 "rest" lines (M4) |
| DL-6 | ALTERNATE detection (M4); include-alternates scenario (M7); memo listing (M9) |
| DL-7 | audit on every resolution (M5); carry-forward/stale (M4) |
| DL-9 | order-shuffle determinism; global recompute (M4) |
| DL-10 | status-table inclusion property (M2); excluded-status rendering (M5); metamorphic "UNRESOLVED never changes totals" (M8) |
| DL-11 | vision request inspection; reconciliation fixtures (M3) |
| DL-12 | inheritance positive/negative fixtures (M3); group + matrix (M4) |
| DL-13 | dataset dependency lint (M1); runbook re-check (M10) |
| DL-14 | section roll-ups + "quality questionnaire" label scope (M2); vendor panel sections (M5); trap "did V5 clear…" (M8) |
| DL-15 | USD artefact assertion (M1); FX conversion + original preserved (M2); As-quoted USD view (M5); FX drill (M10) |
| DL-16 | status × context inclusion property (M2); best-price highlight (M5); override rejected/allowed + audit + promotion recompute (M7); exploratory label (M8); memo listing (M9) |
| DL-8 (freight, FD-4) | baseline never returns freight; delivered-baseline + silence → UNKNOWN (M2) |
| DL-17 | sandbox snapshot-hash test (M1, M6); runbook (M10) |
| DL-18 | weight-source hierarchy; constant versioning + hash pinning; "not validated" renderer test (M2); V5 E2E (M4); memo constants (M9) |

### 5.3 Assignment requirement → milestones
| Requirement | Milestones |
|---|---|
| A-01/02 | M6 |
| A-03 | M6 |
| A-04/05 | M3, M4 |
| A-06/07 | M2, M4, M5 |
| A-08 | M2, M5 |
| A-09/10/11 | M7, M8 |
| A-12 | M7, M9 |
| A-13/14 | M1 |
| A-15 | M3, M8, M10 |
| A-16/17 | M1–M5 |
| A-18 | M2, M4, M5, M8, M9 |
| A-19/23/24 | M10 |
| A-21/22 | M10 |

---

## 6. Risks & mitigations
| Risk | L | I | Mitigation |
|---|---|---|---|
| Photo OCR too poor → everything single-source | Med | High | Tune warp severity. A real-photo option. UNRESOLVED is honest; the review queue shows both reads. |
| Vision path disagrees often on a clean photo | Med | Med | Normalise digits before comparing. Measure the disagreement rate in M3. |
| Silent extraction error | Med | V.High | Evidence + inheritance verification, dictionary, Phase B checks, silent-error gate |
| Analyst SQL logic wrong | Med | High | `run_scenario` steering, view tests, oracle Q-set, metamorphic tests, analyst silent-error gate |
| Unverified described as failed live | Low–Med | High | Label component + runtime lint + correction note + trap tests |
| Live demo latency | Med | Med | Pre-warmed real results, parallel paths, streaming |
| Ground-truth leakage | Low | High | External EVAL_ROOT, guard, AST test, HTTP-only evals, unseen seed |
| Scope creep | Med | Med | DL-13 lint. P1 has no owner until P0 exits. |
| Effort overrun beyond 29.0 d (an estimate for one builder, not a deadline) | Med | Med | P1 is outside the schedule. O1/O2 slack, if taken. B6 drawn down and tracked. Overrun is reported, not absorbed by cutting B1/B2/B4/B5/B6/C1 or any P0/SOT item. |
| **External inputs late** (owner's phone photo; procurement reviewer availability) | Med | High | The print card and review pack are handed over at the end of M1b (day ~8.25). M2b–M4b continue on the synthetic photo. **M1-final must close before B2 (day ~13.5)**. If it slips, B2 waits; it is never run on the synthetic photo as primary evidence. |
| Vertical slice slips past day 8 | Med | Med | The slice uses only text formats (xlsx, eml) and two vendors. If it slips, cut slice scope (e.g. a draft memo without full readiness) rather than testing or demo time. Report the slip. |
| API outage during demo | Low | High | Stored results keep the comparison, review, scenario and award flows working. Recorded walkthrough as backup. |

## 7. Definition of done
- All P0 FRs meet their AC.
- PRD §1.2 metrics met on the demo set **and** on the unseen-seed variant.
- Every DL (DL-1…DL-32) has at least one passing test or gate (§5.2).
- The vertical slice (T-SLICE-01) passed by ~day 6.5, and the day-10/15/20 checkpoints in §2.8 were met or their slippage reported.
- DL-13 lint passes.
- Walkthrough recorded. One-pager written. Two clean dry runs.
