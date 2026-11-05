# Fix Log — Pre-Build Review Resolutions
**Date:** 2026-11-04 · **Review:** `docs/05_prebuild_review.md` · **Result:** all 6 blockers and all 10 important findings resolved in the spec. The seven follow-up product decisions are locked (§6). No application code, no dataset generated, no new features.

**Document versions after this pass:**
| Doc | Version | Nature of change |
|---|---|---|
| `01_product_brief.md` | v1.2 | PRD-authority header. DL-8…DL-13 added. Superseded sections marked and corrected. Dataset and walkthrough updated. |
| `02_PRD.md` | v1.1 | Rewritten in place: new locked decisions, canonical status model (§6), savings rules, baseline rules, dataset, priorities |
| `03_architecture.md` | v1.1 | Rewritten in place: two-phase processing, independent vision path, isolation, retries, parsers, money |
| `04_implementation_plan.md` | v1.1 | Rewritten in place: re-budgeted milestones, new tests, FR→milestone and DL→test tables |

**Abbreviations:** Brief = 01, PRD = 02, Arch = 03, Plan = 04. Tests are referenced as *milestone: test name* from Plan §3.

---

## 1. Blockers

### B1 — "Same as last year" could fill in another vendor's price
| | |
|---|---|
| **Finding** | NRM-8 resolved against any baseline row for the line, and `BaselinePrice.vendor_id` was optional. V5 could have inherited the incumbent's price. |
| **Resolution** | New locked decision **DL-8**. `BaselinePrice.vendor_id` is now required, and rows carry a `spec_signature`. Resolution needs the same vendor + same line + matching signature → `ASSUMED (BASELINE_REFERENCE)`. Same vendor with a different spec → `UNRESOLVED (BASELINE_SPEC_CHANGED)`. Other vendor only, or no row → `UNRESOLVED (BASELINE_NOT_FOR_VENDOR)`. Freight basis comes from this year's terms; a basis change from last year adds the flag `FREIGHT_BASIS_CHANGED` and a caveat. The dataset plants all three outcomes on V5's 7-ply lines. |
| **Docs changed** | PRD §0.1 (DL-8), NRM-8, §5.8 (new acceptance table), §6.2 reason codes, §7 `BaselinePrice`, §9 E-08/E-26/E-27, §11 V5 + baseline. Arch §8 step 9. Plan M1, M2, M4, §5.2. Brief DL-8, E-08, PD-11, open questions. |
| **Validating tests** | M2: *baseline acceptance table* (4 cases); M2: *never-other-vendor property test* over random baseline tables; M2: *FREIGHT_BASIS_CHANGED flag*; M4: *E2E V5 "rest" lines vs answer key*. |

### B2 — Peer-dependent statuses depended on processing order
| | |
|---|---|
| **Finding** | Peer and outlier checks ran inside concurrent per-response jobs. Recompute touched only the edited cell. Accepted cells could be silently downgraded. |
| **Resolution** | New locked decision **DL-9**: **Phase A** (per response, no cross-vendor reads) and **Phase B** (global, single-threaded, canonical order, after all responses are Processed/Failed). Peer medians are leave-one-out and computed from **Phase A** values, so they are order-independent and non-circular. Any change triggers a **global recompute** (re-normalise affected cells + full Phase B; < 2 s for 150 cells). Human resolutions are **sticky**: recompute can add `NEW_WARNING_AFTER_REVIEW` but never downgrades them. The comparison shows "Provisional" until Phase B completes; analyst and award are disabled until then. |
| **Docs changed** | PRD §0.1 (DL-9), J3, J4, DIS-2, VAL-2/3/5, CMP-8, §5.6, §6.5, §7 `ProcessingSet`, `Resolution`, E-29. Arch §2, §5.3, §9, §16, ADR-5. Plan M4, §5.2. Brief DL-9, E-04, E-21, §7.4. |
| **Validating tests** | M4: *order-shuffle determinism* (10 random completion orders → identical snapshot hash); M4: *peer independence*; M4: *global recompute VAL-5* (correct V4 line 7 → all line-7 cells re-evaluated; accepted cell not downgraded); M5: *resolution → recompute < 2 s*. |

### B3 — Status and inclusion under-specified for derived and unresolved cells
| | |
|---|---|
| **Finding** | It wasn't defined whether FX, weight and group-derived cells are ASSUMED. NEEDS_REVIEW cells with no number, or with a suspect number, were "included with warning". |
| **Resolution** | New locked decision **DL-10** with **one canonical model (PRD §6)**: 7 value statuses + independent flags + a separate eligibility vocabulary. `NEEDS_INFO` is replaced by **`UNRESOLVED`**, which absorbs every *blocking* reason (unit unknown/suspect, read disagreement, evidence not found, conflicts, GST unclear, slab ambiguous, baseline issues…). **UNRESOLVED, NOT_CONVERTIBLE and MISSING are never included in calculations.** `NEEDS_REVIEW` is now *advisory only* (outlier, arithmetic, weight mismatch) and is included with a warning by default. §6.3 is a complete transformation → status table (stated-unit conversion = flag only; inherited unit, computed weight, FX, baseline reference = ASSUMED; group expansion = flag only). §6.4 gives the auto-VERIFIED conditions. Inclusion is decided by one function, `status.includable()`. |
| **Docs changed** | PRD §0.1 (DL-10), §6 (new), VAL-1/3, REV-1, CMP-3, AWD-1 `status_policy`, §7 reason codes. Arch §9 (status table as data), §11.2 `includable_default`, §11.4. Plan M2, M5, M8. Brief §7.2 (replaced), F-CMP-2, A-17, PD-4, E-04. |
| **Validating tests** | M2: *status table inclusion* (every status × policy); M2: *property test: UNRESOLVED/NOT_CONVERTIBLE/MISSING never includable*; M2: *one test per §6.3 transformation row*; M5: *no numeric rendering for excluded statuses*; M8: *metamorphic: adding an UNRESOLVED cell never changes any total*. |

### B4 — The image dual read was not independent
| | |
|---|---|
| **Finding** | One call saw both the image and the OCR text, so a misread could be confirmed rather than caught. `value_as_stated` was ambiguous, and disagreements could surface as `EVIDENCE_NOT_FOUND`. |
| **Resolution** | New locked decision **DL-11**. Two **separate, parallel** calls from the same corrected image. **Path O:** OCR units → text-only structuring (no image). **Path V:** image only (no OCR text or boxes). Deterministic reconciliation pairs rows by matched RFx line, then by row order and band. Outcomes: agree → EXTRACTED cap with OCR evidence; differ → `UNRESOLVED (READ_DISAGREEMENT)`; one-sided → `UNRESOLVED (READ_SINGLE_SOURCE)`; low OCR confidence → `UNRESOLVED (LOW_OCR_CONFIDENCE)`. `value_as_stated` = OCR reading; `image_read_value` = vision reading. A path disagreement **never** yields `EVIDENCE_NOT_FOUND`. The vision call is budgeted (parallel, < 60 s). |
| **Docs changed** | PRD §0.1 (DL-11), EXT-7 + AC, AI-14, §6.3, §7 `ExtractionRun.path`, `RawLineQuote`, E-01, NF-1. Arch §6.2 (rewritten), §7.2 `VisionExtraction`, §16, ADR-4. Plan M3. Brief DL-11, E-01. |
| **Validating tests** | M3: *vision independence request inspection* (no OCR strings in the vision payload); M3: *reconciliation fixtures* (agree / differ / one-sided / low-confidence / never EVIDENCE_NOT_FOUND); M5: *Playwright: both reads side by side, choose → recompute*. |

### B5 — The flagship email edge contradicted the extraction rules
| | |
|---|---|
| **Finding** | "38" has no unit, so the rules said UNKNOWN while E-08 promised a ₹/kg chain. Group expansion hit item types with no defined weight formula. |
| **Resolution** | New locked decision **DL-12**. `unit_source` ∈ {STATED, INHERITED_FROM_CONTEXT, NONE}. On the exact assignment sentence, "38" inherits ₹/kg from "₹42/kg", **cites both spans**, and is `ASSUMED (UNIT_INHERITED)`. A deterministic guard accepts inheritance only within the same or an adjacent unit of the same message with no intervening unit token; otherwise it is UNKNOWN. Group expansion targets every RFx line of the matching ply. Whether it converts is decided by the **item-type support matrix** (PRD §5.2): RSC → RSC blank formula; DIE_CUT/PAD → flat-blank formula only with `blank_size_mm`; PARTITION → never computed (vendor weight only). Box formulas are never applied to incompatible items. |
| **Docs changed** | PRD §0.1 (DL-12), EXT-5 + AC, EXT-8 AC, NRM-3, §5.1, §5.2 (matrix), §6.3, §7 `RawLineQuote`, E-08, E-22, §11 V5. Arch §7.2, §7.3 (inheritance check), §7.5, §8 step 3. Plan M3, M4. Brief DL-12, E-08. |
| **Validating tests** | M3: *DL-12 inheritance on the exact sentence* (38 → PER_KG, INHERITED, cites "₹42/kg"); M3: *negative inheritance fixtures* (non-adjacent message; intervening unit token); M4: *group expansion + matrix* (3-ply partition → NOT_CONVERTIBLE; 3-ply RSC → ASSUMED; die-cut without blank → NOT_CONVERTIBLE). |

### B6 — P0 paths depended on P1 features
| | |
|---|---|
| **Finding** | Slabs (NRM-10), tooling (NRM-9), live re-run (EXT-11) were P1 but planted in the dataset or needed for demo resilience. The cap was P0 in AWD-1 and P1 in AWD-6, and walkthrough Q9 depended on it. |
| **Resolution** | New locked decision **DL-13**: the dataset and demo depend only on P0. **Promoted to P0:** slab capture + selection (EXT-14, NRM-10); tooling detection + separation (EXT-13, NRM-9 part); basic re-run with carry-forward (EXT-11). **Kept P1 and removed from the demo:** vendor cap (AWD-6; removed from AWD-1; walkthrough Q9 replaced with an uncovered-lines/alternates question); FX sensitivity tool (the demo uses the P0 rate edit instead); tooling amortisation; re-run history browser (EXT-11b). Added an automated dataset dependency lint. |
| **Docs changed** | PRD §0 priorities, §0.1 (DL-13), EXT-11/11b/13/14, NRM-9/10, AWD-1/6, §11, §12. Arch §11.1 tool priorities. Plan §1, M1 (dependency lint), M7, M10, §5.1. Brief DL-13, F-NRM-5, F-AWD-1, §8.2 Q9, E-03. |
| **Validating tests** | M1: *DL-13 dependency lint* (every planted behaviour → P0 FR, else the build fails); M3: *V1 tooling as DocumentTerm, never a line*; M2: *slab contained/none/overlap*; M4: *re-run carry-forward*; M10: *runbook DL-13 re-check*. |

---

## 2. Important improvements

### I1 — Brief out of date vs PRD
| | |
|---|---|
| **Resolution** | Brief v1.2 has an **"Authority: PRD wins"** header. Superseded sections are marked and corrected: §7.2 (six-state table replaced), F-CMP-2, §10 A-17, E-16 (now Unverified), F-NRM-6 (tolerances; "Alternate"), §7.4 (paper-cost check dropped), F-NRM-4 → P0, F-AWD-5 → P0, F-AWD-1 (cap is P1). |
| **Docs changed** | Brief header, §5 F-rows, §6 E-rows, §7.2–7.4, §10. PRD header (authority line). |
| **Validating tests** | Documentation consistency is checked manually in this pass (grep for stale terms: `Needs info`, `six`, `vendor_cap`, `NEEDS_REVIEW (UNIT…)` — none remain outside superseded notes). Behaviour is covered by the B3 tests. |

### I2 — "Quality questionnaire" scope; Unverified ≠ Fail at runtime
| | |
|---|---|
| **Resolution** | `Question.section ∈ {QUALITY, COMMERCIAL}` is required. Roll-ups are per section and for all mandatory questions. Scenario param `eligibility_scope` (default `quality`). The analyst always states the scope. Dataset: V5 is Quality Pass / Commercial Fail, which shows the distinction. **Runtime label lint** (AI-12): fail-family words near a non-FAIL vendor → regenerate once by appending feedback → a code-generated correction note. A single `EligibilityLabel` UI component. Walkthrough Q4 is reworded, and the old wording is kept as a trap question. |
| **Docs changed** | PRD RFX-4, J1, CMP-5, ELG-2/3/6, §5.7, §7 `Question`, AI-12, E-28, §11. Arch §4, §10, §11.6. Plan M2, M5, M8, M9. Brief F-RFX-4, E-09, §8.2 Q4. |
| **Validating tests** | M2: *section roll-ups incl. V5*; M5: *EligibilityLabel mapping*; M8: *label lint unit tests*; M8: *trap set* ("on what grounds did the others fail?" → premise corrected; "who failed?" scoped); M9: *memo/export wording*; §1.2 metric *Unverified described as failed = 0*. |

### I3 — Headline VP answer was trivial; hardest edges were absent
| | |
|---|---|
| **Resolution** | New eligibility mix (quality, strict): **V1, V2, V5 Pass** (3 eligible), V3 Unverified, V4 Fail. **V2 quotes entirely in USD** (the assignment's "the one who quoted in USD"). The 2 printed die-cut mailers are uncovered like-for-like (V1 didn't quote them, V2 quoted alternates, V5's are not convertible), which exercises "uncovered" and DL-6. An FX rate change flips at least one V2 line. |
| **Docs changed** | PRD §11 (dataset + headline behaviour), E-03, E-09. Plan M1 (eligibility mix assertion), M7 (VP fixture), M10 drill. Brief §8.1. |
| **Validating tests** | M1: *eligibility mix assertion* (≥ 3 Pass, ≥ 1 Fail, ≥ 1 Unverified, ≥ 1 uncovered line); M7: *VP question fixture*; M10: *FX-flip drill*. |

### I4 — Savings comparators undefined
| | |
|---|---|
| **Resolution** | PRD §5.9 defines: scenario spend over awarded lines; **savings vs last year** only on lines with a comparable awarded baseline, always reported as "N of M lines, ₹X (Y%) of spend", with the uncovered lines listed; **best single vendor** = the eligible vendor with the largest coverage of awarded lines (ties: lowest total, then vendor id), compared on its covered lines only; single-vendor totals never extrapolated. Rounding per §5.10. The oracle implements the same definitions independently. |
| **Docs changed** | PRD AWD-2, NLA-4 AC, §5.9, §5.10. Arch §11.3 `savings.py`. Plan M7. Brief E-09. |
| **Validating tests** | M7: *oracle parity on 20 parameter combinations* incl. coverage statements and comparator choice; M9: *memo numbers equal scenario output*. |

### I5 — Weight method gaps
| | |
|---|---|
| **Resolution** | Flute→medium mapping in layer order. Completeness validation (ply/flute/medium counts). Die-cut and pad use the flat-blank formula only with a blank size. Partitions are never computed. Internal-dimension under-estimation is disclosed in the trace. |
| **Docs changed** | PRD RFX-3 AC, §5.2. Arch §8 step 3. Plan M2. |
| **Validating tests** | M2: *RSC hand-calculated BC weight*, *count-mismatch → incomplete*, *die-cut with/without blank*, *partition*, *single-input-removal property test*, *trace disclosure present*. |

### I6 — Where determinism starts
| | |
|---|---|
| **Resolution** | NF-5 restated. Determinism starts from stored raw facts; analyst answers are reproducible for the same tool calls. Re-run carry-forward by raw fingerprint (same → keep; changed → `STALE_SOURCE_CHANGED`, item reopens). FX change: scenarios marked **stale** (recompute on open), acknowledged awards marked **superseded**, which resolves the "recomputed vs stale" contradiction. Decimal money and a rounding policy (PRD §5.10). |
| **Docs changed** | PRD NRM-4 AC, NRM-13, §5.10, §6.5, AWD-7, AI-15, NF-5. Arch principle 4, §5.4, §7.1, ADR-11. Plan M2, M4, M7, M8. Brief §7.3. |
| **Validating tests** | M2: *money rounding fixtures + no-float static check*; M4: *carry-forward same/changed fingerprint*; M7: *FX change → stale/superseded*; M7: *byte-identical scenario output*; M8: *replay determinism of stored tool calls*. |

### I7 — Ground-truth isolation was a convention
| | |
|---|---|
| **Resolution** | Answer keys, truth specs, generator, oracle and the banned-literal list move to an **external `EVAL_ROOT`** outside the repo. The app reads and writes only `DATA_ROOT`, through `storage.safe_path`. The app refuses to start if `EVAL_ROOT` is set or the roots overlap. An AST static test bans file I/O outside `storage/` and any truth references. Eval tests talk to the app only over HTTP. The perturbation seed is drawn at M10 and recorded. |
| **Docs changed** | PRD AI-11, NF-9, §11. Arch principle 7, §5.1, §7.1 (banned list), §14, ADR-12. Plan M0, M1, M10, §4.2. |
| **Validating tests** | M0: *guard refuses outside paths incl. symlinks*; M0: *startup refusal*; M0: *AST static scan*; M1: *manual probe*; M10: *unseen-seed perturbation*. |

### I8 — Silent-error blind spots
| | |
|---|---|
| **Resolution** | (a) No plausibility reference → cap EXTRACTED + `PLAUSIBILITY_UNCHECKED` (VAL-6). (b) New **analyst silent error** metric (target 0 on the walkthrough set). (c) Award, split and savings questions **must** use `run_scenario` (NLA-10), checked in the eval. (d) New **independent analyst correctness tests**: view correctness vs oracle, oracle question set, tool-route check, metamorphic properties, replay determinism. |
| **Docs changed** | PRD §1.2, VAL-6, §6.3, §6.4, NLA-10. Arch §9, §11.1. Plan M8 (seven test groups), §4.1. Brief §7.6. |
| **Validating tests** | M2: *plausibility cap*; M8: *view correctness*, *oracle Q-set*, *tool-route check*, *metamorphic tests*, *replay determinism*, *analyst silent error = 0*. |

### I9 — Stack practicality gaps
| | |
|---|---|
| **Resolution** | Explicit effort on every route. **Append-only conversations**: exact `response.content` (incl. thinking) stored and passed back; transport retries resend an identical body; regeneration appends a feedback message (mid-conversation system message) after the rejected answer; a permanently failed turn is not appended. python-docx + direct OOXML traversal (order + `footnotes.xml`). `xlrd` for .xls, `pillow-heif` for .heic. `make doctor` + optional Dockerfile for Tesseract. Unit dictionary "unseen = no opinion" (`UNIT_DICT_UNSEEN`, blocks auto-verify). |
| **Docs changed** | PRD AI-13, §5.1, NF-7, EXT-1. Arch §3, §6.1, §7.1, §7.4. Plan M0, M3, M8. Brief E-20. |
| **Validating tests** | M0: *append-only store rejects edits*; M0: *transport retry byte-identical body*; M3: *.xls/.heic fixtures*, *docx footnote + order*; M2: *dictionary agree/disagree/unseen*; M8: *conversation integrity* (regeneration leaves earlier turns byte-identical; a failed turn is not appended; the next question succeeds). |

### I10 — Plan coverage and effort balance
| | |
|---|---|
| **Resolution** | Co-pilot gets 1.5 d of its own plus an eval (~12 scripted instructions, ≥ 90%). Demo coherence: the main flow uses the seeded RFx; live drafting happens on a **sandbox RFx** that receives uploads only. **FR→milestone owner table** added. Generator perturbation scope reduced (values, names, row order + one layout change per format). M1 re-budgeted to 2.0 d. Total estimate goes from ~12 to ~15 build days. |
| **Docs changed** | PRD J1, RFX-8 + co-pilot eval AC, §7 `Rfx.kind`. Arch §4, §12. Plan §2, M1, M6, §5.1. |
| **Validating tests** | M6: *co-pilot eval*, *sandbox isolation*; M1: *perturbation scope per format*; Plan §7: *all P0 FRs meet AC*, checked against the §5.1 owner table. |

---

## 3. Audit criteria table — final state

| # | Criterion | Before | After | Resolved by |
|---|---|---|---|---|
| 1 | Every assignment requirement covered | ⚠️ | ✅ | I3 (USD vendor), I10 (co-pilot depth) |
| 2 | PRD ↔ architecture consistent | ⚠️ | ✅ | B2, B3, B6, I1, I6 |
| 3 | Acceptance criteria testable | ⚠️ | ✅ | B3, B4, I2, I6, I8 |
| 4 | Stack practical | ✅ with fixes | ✅ | I9 |
| 5 | Extraction pipeline feasible | ⚠️ | ✅ | B4, B5, I9 |
| 6 | Conversions never use invented inputs | ❌ | ✅ | B1, B5, I5 |
| 7 | Eligibility consistent | ⚠️ | ✅ | I1, I2, I3 |
| 8 | Calculations deterministic | ❌ | ✅ | B2, I6 |
| 9 | Ground truth unreachable | ⚠️ | ✅ | I7 |
| 10 | Plan covers all P0 | ⚠️ | ✅ | B6, I10 |

"Verified as sound" items in the review (the AI/code split, DL-2 freight, DL-3 roll-up, evidence verification, the SQL sandbox, the oracle, status precedence) were **kept unchanged**. Precedence was extended with `UNRESOLVED` in place of `NEEDS_INFO`.

---

## 4. User instructions → resolution map

| Instruction | Where resolved |
|---|---|
| 1. Baseline: same vendor + matching spec only | B1 / DL-8 |
| 2. Deterministic processing; peer checks after all responses; global recompute | B2 / DL-9 |
| 3. One canonical status model; defined behaviour for missing, assumed, extracted, converted, unverified and review-required; unresolved never in calculations | B3 + I1 / DL-10 (PRD §6.1–6.5) |
| 4. Independent photo extraction; disagreements → human review | B4 / DL-11 |
| 5. Exact email example; inherited unit recorded as an inference; weight conversion only for supported items | B5 + I5 / DL-12 |
| 6. Dataset and demo depend only on implemented, tested P0 | B6 / DL-13 |
| Quality vs commercial questions | I2 |
| Analyst never says Unverified = Failed | I2 (label lint, component, trap tests) |
| Meaningful VP split, ≥ 3 eligible vendors | I3 |
| Savings definitions (missing baselines, partial coverage) | I4 |
| Ground truth inaccessible to the running app | I7 |
| Independent tests for analyst calculations | I8 |
| Claude API retries without invalidating previous turns | I9 (AI-13, Arch §7.1) |

---

## 5. Defaults applied that still needed a product decision — **all closed in §6**
These were decided provisionally so the build wasn't blocked. Each was then confirmed or changed by the owner in `08_final_product_decisions.md` (see §6.1).

1. **"Quality questionnaire" = Quality section only** (PRD §5.7, ELG-3). The alternative is all mandatory questions, which would exclude V5 from the VP's answer.
2. **V2 quotes entirely in USD** (PRD §11). The alternative is a single USD line at another vendor. This changes which vendor's ranking FX can flip.
3. **NEEDS_REVIEW (advisory) included with a warning by default** in scenarios. The alternative is excluding it by default, which is more conservative and gives fewer covered lines.
4. **"Same as last year" when last year was delivered and this year is "freight extra":** we take last year's unit price, set freight to UNKNOWN, and add a caveat. The alternative is treating the cell as UNRESOLVED until the vendor clarifies.
5. **Sandbox RFx for live co-pilot drafting** in the demo (PRD J1/RFX-8).
6. **Method constants** (take-up factors, 35 mm joint allowance, GSM −5% / dims ±2 mm tolerances, 20× unit-suspect and [0.5×, 2×] outlier thresholds, OCR confidence 80) need a domain sign-off from a packaging engineer before M2 golden values are fixed.
7. **Effort is now ~15 + 2 days** (up from 12 + 2). Confirm it fits the demo date, or agree to drop all P1 (already allowed by DL-13).

---

## 6. Final product decisions pass (2026-11-04)
**Input:** the owner's final decisions, checked against `assignment.pdf`. Recorded in `docs/08_final_product_decisions.md`.
**Versions after this pass:** Brief v1.3 · PRD v1.2 · Architecture v1.2 · Plan v1.2.

### 6.1 How each §5 default was closed
| §5 item | Final decision | Outcome vs default |
|---|---|---|
| 1. Quality scope | FD-1 → **DL-14** | **Confirmed.** `all_mandatory` stays an explicit opt-in, labelled "quality and commercial requirements". |
| 2. V2 in USD | FD-2 → **DL-15** | **Confirmed.** Original USD preserved. Stated, editable rate and date. |
| 3. NEEDS_REVIEW in scenarios | FD-3 → **DL-16** | **Changed.** It was "included with warning by default". It is now **excluded from formal award calculations by default**, with an audited per-scenario buyer override. Exploratory analysis may include it on request, with a label. |
| 4. Same-as-last-year freight | FD-4 → **DL-8 amended** | **Confirmed and tightened.** Historical freight is never carried forward; the baseline supplies the unit price only. |
| 5. Sandbox RFx | FD-5 → **DL-17** | **Confirmed.** The prepared five-vendor dataset is guaranteed unchanged (snapshot hash test). |
| 6. Method constants | FD-6 → **DL-18** | **Changed.** Constants are now versioned with a validation status and labelled "not validated". New weight-source hierarchy: SKU reference weight → vendor weight → estimate (**NEEDS_REVIEW**, was ASSUMED) → NOT_CONVERTIBLE/UNRESOLVED. |
| 7. Timeline | FD-7 | **Confirmed** as an estimate, not a commitment. P1 is dropped first. |

### 6.2 Changes by decision
| Decision | Docs changed (sections) | Validating tests |
|---|---|---|
| **DL-14** Quality only | Brief DL-14, F-RFX-4. PRD §0.1, ELG-3 + AC, §14 D16. Arch §10. Plan M2, M5, M8, §5.2. | M2 *section roll-up + label scope*; M5 *vendor panel sections*; M8 trap *"did V5 clear the quality questionnaire?"* |
| **DL-15** V2 USD | Brief DL-15, E-03. PRD §0.1, NRM-4 AC, §5.3, E-03, §11 V2. Arch §8 step 7, §11.2, §14. Plan M1, M2, M5, §5.2. | M1 *USD artefact assertion* (the build fails if the USD vendor is missing); M2 *FX conversion, original preserved*; M5 *As-quoted USD view*; M10 *FX drill* |
| **DL-16** NEEDS_REVIEW | Brief DL-16, §7.2, E-21. PRD §0.1, J6, J7, CMP-1, NLA-4 AC, AWD-1/3 + AC, §6.2, §7 `Scenario`, E-21, §11 headline, §14 D18. Arch principle 5, §4 Award, §5.2 API, §9 `includable(context…)`, §11.1/11.2/11.3, §13, ADR-13. Plan M2, M5, M7, M8, M9, §5.2. | M2 *status × context × policy × override property*; M5 *best-price highlight*; M7 *override rejected/allowed + AuditEvent + promotion recompute*; M8 *exploratory label*; M9 *memo lists override* |
| **DL-8** freight (FD-4) | Brief DL-8, E-08. PRD §0.1, NRM-5 AC, §5.4, §5.8, E-08. Arch §8 steps 8–9. Plan M1, M2, §5.2. | M2 *baseline never returns freight* (property); M2 *delivered baseline + silence → UNKNOWN + caveat* |
| **DL-17** Sandbox | Brief DL-17. PRD §0.1, J1, RFX-8 AC. Arch §4. Plan M1, M6, §5.2. | M1/M6 *sandbox snapshot-hash unchanged*; M10 *runbook* |
| **DL-18** Constants & weight | Brief DL-1 note, DL-18, F-NRM-2, E-08, §7.2, §8.1 V5. PRD §0.1 (DL-1/12 amended), RFX-3 + AC, NRM-3 + AC, §5.2 (hierarchy), §5.11 (new), §6.2/6.3, §7 `RfxLine`, `NormalizedQuote`, `ConstantSet`, E-08/22/23/30, §11 RFx + V5, §14 D19. Arch §4, §5.1, §5.2, §7.5, §8 step 3, §14, ADR-14. Plan M1, M2, M4, M5, M6, M9, §5.2. | M2 *weight-source hierarchy (6 cases)*; M2 *constant activation → audit + recompute; version hash pinning*; M2 *renderer: no UNVALIDATED constant without its label*; M4 *V5 E2E (2 WEIGHT_ESTIMATED lines)*; M9 *memo shows constant version + labels* |
| **FD-7** Timeline | Brief §8 note, decision table. PRD §12.5. Plan header, §6 risks, §7. | — (planning policy; checked in M10 DL-13 re-check) |

### 6.3 Consistency confirmation
Checks run after the edits:
1. **Decision presence matrix.** Number of references per document:

   | Decision | Brief | PRD | Arch | Plan |
   |---|---|---|---|---|
   | DL-8 | 5 | 13 | 3 | 6 |
   | DL-14 | 3 | 6 | 1 | 5 |
   | DL-15 | 2 | 7 | 4 | 7 |
   | DL-16 | 3 | 16 | 6 | 7 |
   | DL-17 | 1 | 4 | 1 | 5 |
   | DL-18 | 4 | 15 | 5 | 9 |

   FD-7 appears in the Brief, PRD §12.5 and the Plan. It isn't an architecture concern.
2. **Stale-term scan:** none of these remain in the four core docs:
   - `include_needs_review_with_warning`
   - "included with warning" applied to formal awards
   - `ASSUMED (METHOD_CONSTANTS)` as the status of an estimated weight
   - "vendor weight preferred" as the first weight source
   - `method_constants.yaml`
   - `includable_default`
3. **Assignment preservation:**
   - the USD vendor (V2) is present and protected by a build-failing assertion;
   - the exact email sentence is still planted on V5;
   - the angled photo, 27/30 vendor and per-box vs per-100 cases are unchanged;
   - the VP split still has 3 eligible vendors.
4. **No new features:**
   - the formal/exploratory context and the override are parameters on existing scenario and award features;
   - constant versioning is a config file plus version *selection*, with no authoring UI;
   - the reference weight is a field on the existing RFx line.

---

## 7. Source-coverage audit fixes SC-01…SC-04 (2026-11-04)
**Input:** `docs/09_source_coverage_audit.md`, items approved by the owner. **Canonical reference:** `docs/00_source_of_truth.md`.
**Versions after this pass:** Brief v1.4 · PRD v1.3 · Architecture v1.3 · Plan v1.3 · new `docs/10_demo_runbook.md` v1.0 · `08` addendum (DL-19).
**Locked decisions:** DL-1…DL-18 unchanged. DL-19 added (approved SC-04). DL-17 preserved, with a clarifying note.

### SC-01 — Per-edge-case demonstration strategy (High)
| | |
|---|---|
| **Finding** | Named edge cases had fixtures but no demo strategy. The runbook was generic. |
| **Resolution** | New `docs/10_demo_runbook.md`: an honesty statement; pre-flight; a primary flow P1–P11; an **edge-case matrix** covering EDGE-01…09, including 05a–d and 04/06. Each row gives the dataset fixture, workflow step, expected system behaviour, visible UI evidence, demo action/question and the named test. Also: analyst question set Q1–Q10 tagged to SOT IDs, sandbox and upload segments, contingencies, and an evidence checklist. |
| **Docs changed** | New `10_demo_runbook.md`. Plan M10 (runbook bullet, runbook-to-test check, exit). Brief §8.2 note. PRD header link. |
| **Validating tests** | Plan M1 *edge-fixture presence lint* (fails if any EDGE-* lacks a fixture). Plan M10 *runbook-to-test check* (every runbook §3 row → a passing T-EDGE test). Runbook §7 evidence checklist as the M10 exit. |

### SC-02 — Analyst access to document facts and questionnaire answers (High)
| | |
|---|---|
| **Finding** | PRD NLA-1 promised document facts, but the architecture's views exposed none. "Over the whole comparison" (SOT FN-11) was narrowed. |
| **Resolution** | New read-only views: `v_questionnaire_answers` (incl. verbatim answer text), `v_document_facts`, `v_certificates` (validity and entity match computed by code), `v_evidence_index` (no text). New tool `get_evidence` returns one capped, untrusted-wrapped snippet, and only for refs cited by fact, answer or quote rows. **No full-text access.** NLA-11 (access), NLA-12 (every non-numeric fact source-linked; grounding extended to dates, certificate numbers and entity names), NLA-13 (no invention: absent → "not in the data"), AI-16 (vendor content is data). `DocumentFact` entity. The dataset prints extractable certificate facts, with planted expired / entity-mismatch / absent cases. |
| **Docs changed** | PRD NLA-1, NLA-11…13 + AC, AI-16, §1.2 metrics, §7 (`DocumentFact`, `QuestionAnswer` note), E-32, §11, §12.1, D21. Arch §11.1 (`get_evidence`), §11.2 (views + guardrails), §11.4 (fact provenance), §11.5 (grounding extended), ADR-16. Plan M1, M3 (document-fact extraction test), M8 (views, tests 1a–1c), §4.1, §5.1. Runbook Q7. |
| **Validating tests** | M3 *document facts vs ground truth*; M8 *view correctness incl. document views*; M8 1a *guardrails* (no full-text schema test, `get_evidence` refusal, 400-char cap, injection fixture); M8 1b *document-fact oracle questions*; M8 1c *no invention = 100%*; NLA-12 *extended grounding*. |

### SC-03 — Explicit behavioural tests for four named edges (Med-High)
| | |
|---|---|
| **Finding** | Footnote discounts, Word-paragraph terms, 27/30 disclosure in answers, and per-box vs per-100 had no explicit tests. |
| **Resolution** | New **Plan §3a named edge-case suite** (T-EDGE-01…09). The four requested tests assert behaviour:<br>• **T-EDGE-02:** footnote term with footnote locator; applied at step 5 exactly once; values to 4 dp; scope and absence negatives.<br>• **T-EDGE-03:** 5 prose terms with values and paragraph evidence; freight drives landed; payment drives commercial eligibility; conditional and absent-term negatives.<br>• **T-EDGE-07:** exact 3 missing lines never filled (property); 27-line totals labelled; coverage + line numbers in code-generated exclusions for Q1, Q3, Q5; narrative grounded.<br>• **T-EDGE-09:** per-100 / per-1000 / each conversions; header-labelled PER_100 STATED; unlabelled → UNIT_SUSPECT excluded from totals; acceptance recomputes peers; cross-vendor comparability on ≥ 3 overlapping lines; high-but-genuine price not flagged.<br>Fixtures and negative variants added to PRD §11 / Plan M1. |
| **Docs changed** | Plan §3a (new), M1 (fixtures), §4.1. PRD §11 (V2/V3/V4 fixture detail, negative fixtures, ground-truth scope), NLA-4 coverage AC. Arch §11.2 (`coverage_count`, `missing_line_nos`), §11.4 (coverage disclosure). |
| **Validating tests** | T-EDGE-02, T-EDGE-03, T-EDGE-07, T-EDGE-09 (plus T-EDGE-01/04/05/05a–d/08 for completeness). Gate: all pass on the demo set **and** the unseen-seed variant (M10). |

### SC-04 — One continuous flow with a genuine co-pilot (Medium)
| | |
|---|---|
| **Finding** | The prepared five-vendor flow ran on a seeded RFx the panel never saw being drafted, so "one flow, end to end" was weakened in the demo. |
| **Resolution** | **DL-19.** The primary RFx is drafted live by the co-pilot from a **buyer brief pack** (item master, quality checklist, commercial policy) plus the buyer's conversational answers to its clarifying questions (RFX-9: patches cite brief-pack rows). A deterministic **conformance check** (RFX-10) against the **canonical RFx spec**, which every vendor response was authored against, gates delivery. The co-pilot never sees the canonical spec (AI-17), so the check is genuine. The RFx records `origin = COPILOT_LIVE`, its transcript and its conformance result (RFX-11). The canonical spec loads only as a visibly labelled **seeded fallback**. The **sandbox (DL-17) is preserved** for free-form drafting. Runbook P1–P11 runs on one RFx. |
| **Docs changed** | PRD §0.1 (DL-19 + DL-17 note), J1, J2, RFX-8…11 + AC, AI-17, §1.2, §7 (`Rfx`, `CanonicalRfxSpec`, `Question.requirement_key`), E-31, §11 (brief pack, canonical spec), §12.1, D20. Arch §4, §5.1, §5.2, §12, §16, ADR-15. Plan M1 (canonical-first authoring, consistency test), M6 (co-pilot 2.0 d + tests), M10, §5.1, §5.2. Brief DL-19 row. `08` addendum. Runbook §0, §2, §6. |
| **Validating tests** | M1 *canonical consistency*; M6 *live primary-RFx rehearsal ≥ 4/5 within budget*, *conformance unit tests* (4 negatives), *co-pilot isolation (spec never sent)*, *delivery gate 409*, *provenance labels*; M10 *runbook P1–P11 dry run without fallback*. |

### 7.1 Source-of-truth check (CLAUDE.md rule 1–2)
- **SOT items strengthened:** REQ-03, FN-01, FN-02 (SC-04); FN-10, FN-11, AI-03 (SC-02); EDGE-01…09, EVAL-01 (SC-01/03).
- **No SOT item weakened. No locked decision changed.**
- **Effort:** milestone estimates now total ~16.5 days, against the FD-7 estimate of 15 (Plan header). This is flagged for an owner decision; it is not silently absorbed.
- **Not in scope of this pass (still open in `09`):** SC-05 ("rest" lines vs terms), SC-06 (one-page note: stale DL/D references in Plan M10 and no length check), SC-07 (human dataset review), SC-08 (real phone photo), SC-09 (chart/export tests), SC-10 (non-responding vendor), SC-11 (documents reachable from comparison), SC-12 (unscripted dry run), SC-13 (SOT IDs in traceability tables).

---

## 8. Bottom-up effort review (2026-11-04)
**Input:** the owner approved revising FD-7 from 15 to 16.5 build days, subject to a bottom-up review.
**Versions after this pass:** Plan v1.4 · PRD §12.5 · Brief (timeline notes) · `08` FD-7 revision history. No product decision or SOT item changed.

| | |
|---|---|
| **What was done** | Each milestone was re-estimated from its task content and dependencies. Effort is now split into **A. P0 essential implementation (16.0 d)**, **B. testing, evaluation & integration (5.25 d, new workstream MT: B1–B7)**, **C. demo preparation (2.0 d)** and **D. P1 enhancements (3.25 d, unscheduled)**. A day-by-day sequential schedule with gates was added. |
| **Result** | **23.25 days of P0 work**, against the approved 18.5 (16.5 + 2). |
| **Visibility** | The approved +1.5 d is shown as its own line. The further +4.75 d is itemised in Plan §2.6: M5 UI +0.5; oracle harness +0.75; extraction tuning +1.0; document-fact eval set +0.25; T-EDGE live suite +0.5; integration/debugging +1.0; unscripted dry run, rehearsal fixes and one-page editing +0.75. Moves between categories (M6/M8 evals → B3/B4; M10 regression → B7) net to zero. **Nothing was compressed to offset the increase.** |
| **Preserved** | Every P0 FR. All named edge cases (T-EDGE-01…09 in B5). Real extraction and reasoning (B2, B4). All trust functions. Ground-truth isolation. |
| **Trade-offs offered (owner decision)** | §2.7: P1 deferral (already the plan, saves 0 from P0); O1–O3 (≤ 1.0 d total, no SOT impact, O3 not recommended); X1–X4 listed as **weakening** SOT items (FN-05, AI-02/04, DEL-01/EVAL-06, EVAL-03) and not recommended. |
| **Also corrected** | The M8 heading said 2.0 d while the table said 2.5 d (now consistently 2.0 + B4). "M2 in parallel with M3" is not possible for one builder, so the schedule is now sequential. |
| **Open** | FD-7 rev. 2 (accept 23.25 d or choose trade-offs). Audit findings SC-05…SC-13 unchanged. |

---

## 9. FD-7 revision 2 approved (2026-11-04)
| | |
|---|---|
| **Decision** | The owner approved **23.25 days** (16.0 P0 implementation + 5.25 testing, evaluation & integration + 2.0 demo preparation) as FD-7 rev. 2. |
| **Conditions recorded** | (1) An estimate of effort for one builder, not a calendar deadline or contract. (2) All P0 assignment requirements preserved. (3) Extraction tuning (B2), integration testing (B6), independent evaluation (B1, B4, B5) and unscripted demo preparation (C1) are **protected, not reducible**. (4) O3 and X1–X4 **rejected**. (5) O1/O2 optional efficiency improvements, only with no loss of functionality: O1 keeps the AuditEvent, recompute and stale-marking; O2 keeps automatic status updates. Savings become slack. (6) P1 (3.25 d) outside the committed schedule. |
| **Docs changed** | `08` FD-7 (current statement, revision table rev. 2 = approved). Plan v1.5 (header, protected allocations, §2.7 decisions, O/X rows, §6 risk row). PRD §12.5 + D22 + §15 note. Brief timeline notes (×2). |
| **Validation** | No stale "rev. 1 approved / rev. 2 pending" wording remains in 01–04 or 08 (grep). §2 arithmetic: A 16.0 + B 5.25 + C 2.0 = 23.25. P1 3.25 is not in any schedule row. |
| **Unchanged** | All locked decisions DL-1…DL-19. The source of truth. Audit findings SC-05…SC-13 (reviewed separately, not implemented). |

---

## 10. Source-coverage audit SC-05…SC-13 (2026-11-04)
**Owner decisions applied as instructed.** Locked decisions DL-1…DL-19 preserved. DL-20…DL-22 added. FD-7 rev. 2 conditions preserved, rev. 3 records +2.5 d. The source of truth is unchanged.
**Versions after this pass:** Brief v1.5 · PRD v1.4 · Architecture v1.4 · Plan v1.6 · Runbook v1.1 · `08` (FD-7 rev. 3, DL-20…22 addendum) · `09` §8 · new `11_dataset_realism_review.md`, `12_phone_photo_capture_kit.md`, `deliverables/one_page_note.{html,pdf}`.

| Finding | Owner decision | Resolution | Docs changed | Validating tests / gates | Effort |
|---|---|---|---|---|---|
| **SC-05** "rest same as last year" | Don't assume. Keep both readings, flag them unresolved, generate a clarification request, never apply without confirmation, test both readings. | **DL-20.** Reading A (prices) and reading B (terms) candidates (same vendor, same spec, never freight). All UNRESOLVED (REFERENCE_AMBIGUOUS). Template clarification request (no AI) → buyer approval → outbox. `REFERENCE_CONFIRMATION` resolution (prices/terms/both/neither), audited. New `BaselineTerm`, `ClarificationRequest`. | PRD §0.1, J9, EXT-9, NRM-8, REV-4, AWD-3, §5.8, §6.2/6.3, §7, E-08/26/33, §11, §12, D23, metrics. Arch §4, §5.2, §8 step 9, §13, ADR-17. Plan M1, M2, M5, §3a, §5.2. Runbook EDGE-05c. Brief DL-20, E-08. | T-EDGE-05c-A, T-EDGE-05c-B, T-CLAR-01 | 0.75 |
| **SC-06** one-page note | Fix outdated references, define top decisions, generate the final PDF, validate one page | Plan M10 references corrected (DL-1…22, mapping of 10 decisions). Note written and rendered (headless Chrome, A4). **Validated: 1 page** (page objects = 1, `/Count 1`), visually checked. | `deliverables/one_page_note.{html,pdf}`; Plan M10, C3, §3a | T-NOTE-01 (passed 2026-11-04; re-run at C3) | 0 |
| **SC-07** dataset realism | Actual review by a procurement-literate person. Checklist. Record feedback and corrections. No AI self-review as validation. | **DL-22.** Review kit with reviewer eligibility, materials (no ground truth), 30-item checklist across pricing, specs, vendor behaviour, terms, questionnaire/documents, feedback log, corrections log, sign-off. M1-final gate. | `11_dataset_realism_review.md`; PRD §0.1, §11, D24; Plan M1/M1-final, §5.2, §6 | M1-final manual gate | 0.5 |
| **SC-08** real phone photo | Genuine phone photo as the primary fixture; synthetic for extra tests; no AI substitute; prepare the card and instructions | **DL-21.** Capture kit: print-card design, printing, 9-point capture protocol, registration with hash/EXIF/skew checks (AI or edited images rejected), per-value readability annotations, expected statuses. | `12_phone_photo_capture_kit.md`; PRD §0.1, §11; Plan M1/M1-final, T-EDGE-04, §6; Runbook EDGE-04, §6, §7 | T-EDGE-04 (real photo primary), manifest check | 0.25 |
| **SC-09** charts and exports | Tests that chart values match results and exports preserve values and vendor information | Chart binder rejects inline or derived data. Exports written from stored rows with vendor name+id, lines, units, statuses. | PRD NLA-2 AC, EXP-1; Arch §11.1, §13; Plan §3a; Runbook Q2, Q10 | T-OUT-01, T-OUT-02, T-OUT-03 | 0.25 |
| **SC-10** awaiting response | Support absent responses; "Awaiting response"; never zero; works with staggered arrivals | `Invitation.status = AWAITING_RESPONSE`. No quote rows (property). Excluded and listed everywhere. Eligibility "Not assessed". Award acknowledgement. Arrival-subset oracle snapshots. | PRD J3, DIS-2 + AC, CMP AC, AWD-3, §7, §11, E-34, D25, metrics; Arch §4, §5.2, §5.3, §13, ADR-18; Plan M1, M4, §3a; Runbook P5, §7 | T-ARR-01, T-ARR-02, T-ARR-03 | 0.5 |
| **SC-11** attached documents | UI/API tests that documents open directly from the comparison | Document API (list, metadata, original bytes, viewer with highlight). 4 entry points. | PRD CMP-5 + AC; Arch §5.2; Plan M5, §3a; Runbook P8, §7 | T-DOC-01, T-DOC-02 | 0.25 |
| **SC-12** unscripted dry run | Mark resolved | Covered by FD-7 rev. 2 C1 (protected) | `09` §7–8; Runbook §7 | Runbook checklist | 0 |
| **SC-13** SOT IDs in traceability | Defer | Existing mapping (`09` §5) retained | `09` §7–8 | — | 0 |

**Effort:** FD-7 rev. 3 = **25.75 d** (17.75 + 6.0 + 2.0), up from 23.25 by +2.5. That is +1.15 more than the indicative +1.35 given at review, because of the owner's scope decisions (SC-05 +0.5, SC-07 +0.25, SC-10 +0.25, SC-11 +0.15). Shown in Plan §2.6, nothing compressed. Protected allocations unchanged (B5 grows to 1.25).

**External human inputs now on the critical path (before B2, day ~10.5):** (1) the owner's genuine phone photo (DL-21); (2) the procurement-literate reviewer's sign-off and the correction cycle (DL-22).

---

## 11. Final source-coverage audit resolutions (2026-11-04)
| # | Finding | Resolution | Files | Tests / gates |
|---|---|---|---|---|
| 1 | V5's questionnaire evidence had no source while its email must "just say" one sentence | **DL-23.** The email body is unchanged. A separate V5 submission (questionnaire + ISO + BCT + food-grade declaration; payment terms "No") is linked to V5's single Response. Multi-message linking reuses the J8 "existing vendor" path. | PRD, Arch, Plan, Runbook, 08 | M1 V5 fidelity lint (byte-identical body, no attachments); M2 eligibility truth table; T-ARR-01 (6 deliveries) |
| 2 | V1 lacked FSC while the FSC question's applicability was undefined | **DL-24.** Food-grade and FSC are separate questions, each with line-flag applicability. No `requires_fsc` line, so FSC is NOT_APPLICABLE for all vendors and V1 stays Pass, with "not provided — not required" shown. Quality section is now 6 questions. | PRD, Arch, Plan, `11` (checklist Q1), 08 | M2 applicability truth table + `requires_fsc` negative variant; M5 panel text |
| 3 | Reference-weight count said 22, but the rule gives 21 | Corrected to **21 (16 RSC, 3 die-cut, 2 pads)** | PRD §11, Plan M1 | M1 dataset lints |
| 4 | REV-1–4 unowned; J9 listed as P1 despite its P0 part | REV-1–4 → **M5**. **J9 is P0** → M5 (implementation) + B5 (T-CLAR-01). The generic AI-draft extension is renamed **J9b (P1)**. Owners added for AI-1…17 and NF-1…8, so the plan has **no unowned P0 work**. | Plan §2.5, §5.1, §5.2; 08 | Plan §5.1 coverage statement |

**Estimate:** unchanged at **25.75 d** (FD-7 rev. 3). (1) uses the already-specified J8 add-to-existing-vendor path, and V5's questionnaire evidence was already required for its Pass. (2) is a rule-table extension inside the budgeted M2 eligibility work. (3) and (4) are documentation only.

---

## 12. Principal PM review adoptions (2026-11-04)
**Owner-approved:** P0-1…P0-4 (must fix), P1-5, P1-6, P1-9, P1-10, P1-11 (brought in before dataset generation). **Deferred:** all other P1/P2 recommendations. **No new review document was created.** The source of truth is unchanged. No SOT item is weakened: EDGE-08 (USD) is preserved under DL-30, and FN-01/AI-06 (real co-pilot) are preserved under DL-27.

| Item | Decision | Main changes | Tests | Effort |
|---|---|---|---|---|
| P0-1 | DL-25 freight-aware award + break-even + readiness acknowledgement | PRD §0.1, §5.4, AWD-1/2/3 + AC, NLA-4, §7 Scenario, E-35; Arch §11.3, §11.4, ADR-19; Plan M7, §3a; Runbook P10 | T-FRT-01/02/03 | +0.75 |
| P0-2 | DL-26 GST silence → RFx basis as ASSUMED; no basis/ambiguous → UNRESOLVED | PRD NRM-6 + AC, §6.3, E-36, §11 (RFx GST basis; V5 silent); Arch §8 step 6 | T-GST-01 | +0.25 |
| P0-3 | DL-27 deterministic item-master import; AI mapping, gaps, questionnaire/terms, edits | PRD J1, RFX-9 + AC; Arch §12, §16, ADR-21; Plan M6, B3; Runbook P1 | T-IMP-01; B3 rehearsals | 0 (+0.25 −0.25); B3 −0.25 cut |
| P0-4 | Vertical slice by day ~6.5; checkpoints at days 10/~15/~20; testing and demo time preserved | Plan header, §1, §2 (a/b split, S), §2.8, risks, DoD | T-SLICE-01 | +0.5 |
| P1-5 | DL-28 decision sensitivity | PRD §0.1, REV-2, AWD-2/3 + AC, E-37, §11; Arch §11.3, §11.4, ADR-20; Plan M5, M7, §3a; Runbook P7, Q6 | T-SENS-01/02 | +1.0 |
| P1-9 | DL-29 line-level food-grade; FSC question removed; FSC variant as a fixture only (amends DL-24) | PRD §5.7, ELG AC, §7, §11; Arch §10; Plan M1, M2; `11` checklist | T-FOOD-01 | +0.25 |
| P1-10 | DL-30 V2 domestic, USD-linked, invoiced in INR; FX exposure disclosed (frames DL-15) | PRD §0.1, §5.3, §11; Arch §8 step 7, §11.4; Plan M1, M7; Runbook EDGE-08; `11` P5 | T-FX-01 | +0.25 (with P1-11) |
| P1-11 | DL-31 reference weight → ASSUMED; billed-weight caveat (amends DL-18) | PRD §5.2, §6.3, NRM-3 AC; Arch §8 step 3, §11.4; Plan M2, M7; Runbook EDGE-05a | T-WGT-01 | (in P1-10 line) |
| P1-6 | DL-32 deterministic, buyer-approved clarification pack; J9 = P0 via the pack; J9b stays P1 | PRD J9, REV-4, §7 ClarificationPack; Arch §13; Plan M5, §2.5, §3a, §5.1; Runbook P7 | T-PACK-01 | +0.5 |

**Estimate:** FD-7 rev. 4 = **29.0 d** (20.5 + 6.5 + 2.0), up from 25.75 by +3.5 for the additions and −0.25 for the B3 cut. Itemised in Plan §2.6; nothing compressed. Protected allocations kept, and B5 grows to 2.0.
**Also updated:** the one-page note (decisions 5, 7, 8, 9, 10 revised) was regenerated and re-validated as **1 page** (T-NOTE-01). Brief DL summary row and timeline notes. `08` FD-7 rev. 4 + DL-25…32 addendum.
