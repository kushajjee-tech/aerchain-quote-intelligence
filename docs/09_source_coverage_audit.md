# 09 — Source-to-Documentation Coverage Audit
**Date:** 2026-11-04 · **Canonical reference:** `docs/00_source_of_truth.md` (66 items, read directly from `docs/assignment.pdf`)
**Audited:** `01_product_brief.md` v1.3 · `02_PRD.md` v1.2 · `03_architecture.md` v1.2 · `04_implementation_plan.md` v1.2 · `05_prebuild_review.md` · `06_fix_log.md` · `08_final_product_decisions.md`
**Scope rule:** findings only. **No product decision or specification was changed by this audit.** Every recommended change needs owner approval before it is applied.

> **Independence caveat.** This audit was produced by the same AI that wrote documents 01–08. The catalogue was built from the PDF, not from those documents, to reduce bias, but that doesn't make the review independent. The owner should spot-check `00_source_of_truth.md` against the PDF (two pages, about 15 minutes) before relying on this report.

---

## 1. Verdict

**No assignment requirement has been removed.**
- **2 high-severity issues** need attention: a requirement that is inconsistently represented, and a missing per-edge-case demonstration strategy.
- **Several requirements are weakly evidenced or partially tested.**
- **The project should not be declared ready to build** until findings SC-01 to SC-04 are resolved or explicitly accepted by the owner.

| Status | Count | Meaning |
|---|---|---|
| ✅ Covered | 36 | Represented accurately, with a fixture/test and a plausible demo path |
| 🟡 Partial | 18 | Represented, but a test, fixture or demo strategy is missing or only implicit |
| 🟠 Weakened | 5 | Represented in a way that reduces the strength of the source text or its demo evidence |
| 🔴 Inconsistent | 2 | Documents disagree with each other, or with the source (plus SC-13, a cross-cutting traceability inconsistency) |
| ⚠️ Interpretation risk | 1 | The source is ambiguous and the docs commit to one reading without disclosing it |
| — Not applicable | 4 | Permissions/informational items needing no behaviour (EX-06, LIM-02, INFO-01, PERM-04) |
| **Total** | **66** | |

(PERM-01/02/03/05/06 and LIM-01 are counted as Covered: the choices are made and stated consistently.)

---

## 2. Findings

| # | Sev. | SOT IDs | Finding | Classification | Evidence | Recommended action (needs approval) |
|---|---|---|---|---|---|---|
| **SC-01** | **High** | EDGE-01…09, EVAL-01, EVAL-02 | **No per-edge-case demonstration strategy.** Every named edge case has a dataset fixture, but no document says *how each one will be shown* in the live demo or the recording. The runbook (Plan M10) is generic: reset → warm → main path → sandbox → optional upload → fallbacks. | Missing | Plan §3 M10 "Demo runbook". No per-edge demo steps in Brief §8, PRD §11 or Plan. | Add an edge-case demo matrix to the runbook: for each EDGE-*, the screen, the click path, and what the buyer sees. Draft in §4 below. |
| **SC-02** | **High** | FN-11 | **"Natural language, over the whole comparison" is narrowed in the architecture.** PRD NLA-1 includes "document facts". But the analyst's approved views (Arch §11.2) expose no questionnaire **answer text** and no **attached-document facts** (certificate type, expiry, entity). Questions such as "whose ISO certificate expires first?" or "what did V3 say about lead time?" can't be answered. | Inconsistent (PRD ↔ Arch) / weakened capability | PRD §4.10 NLA-1. Arch §11.2 view list (`v_eligibility` has state/reason only). Plan M8 view list. | Add read-only views for questionnaire answers (incl. text) and document facts, and add document/answer questions to the analyst eval. This is a gap in implementing an existing P0 FR, not a new feature. |
| **SC-03** | Med-High | EDGE-02, EDGE-03, EDGE-07, EDGE-09 | **Several named edge cases have no explicit test in the plan.** They rely on the generic "E2E vs answer key" or "extraction eval":<br>• EDGE-02: footnote discount **applied** (Plan v1.1 dropped the explicit "discount order and scope" test);<br>• EDGE-03: prose commercial terms with sentence evidence;<br>• EDGE-07: missing lines **disclosed in analyst answers** (PRD NLA-4 AC exists, no named test);<br>• EDGE-09: per-100 conversion + `UNIT_SUSPECT` (zero mentions in the plan; PRD VAL-3 AC only). | Partial | Plan grep: "per 100 / UNIT_SUSPECT" = 0, "discount" = 1 (build only), "prose" = 1. | Add named tests per edge case (draft in §4) to Plan M2/M3/M4/M8. |
| **SC-04** | Medium | REQ-03, FN-01, FN-02 | **"One flow, end to end" is weakened in the demo evidence.** DL-17 puts live drafting on a sandbox RFx with no prepared responses, while the prepared five-vendor flow runs on a seeded RFx that the panel never sees being drafted. No single RFx is shown going from conversation to award. | Weakened (demo evidence, not the product capability) | PRD J1 step 4, RFX-8. Plan M10 runbook. | Options that keep DL-17 unchanged: (a) on the sandbox, run draft → send → upload one vendor file → comparison → question (all P0 per DL-4); and/or (b) store and show the co-pilot transcript that produced the seeded RFx. Owner to choose. |
| **SC-05** | Medium | EDGE-05c | **"rest same as last year" is ambiguous in the source.** It may mean the remaining lines or the remaining terms (payment, delivery…). All docs commit to "remaining lines" (PRD EXT-9) without disclosing that reading to the buyer. | Interpretation risk | PRD EXT-9 AC, E-08. Brief E-08. | Keep the reading (a product decision), but show it as a stated interpretation on the affected cells and in answers ("interpreted as remaining line items"), with any unmatched terms flagged. Owner approval needed. |
| **SC-06** | Medium | DEL-03, DEL-04 | **The one-page note is inconsistently specified and at risk of overrunning.** Plan M10 lists "decisions (DL-1…13, D1–D15)", which is stale (current: DL-1…18, D1–D19), plus left-outs, eval numbers, limitations and the better problem. That likely exceeds **one page**, and no length check exists. | Inconsistent + weakening risk | Plan §3 M10 bullet "One-page note (D-3)". | Fix the stale references. Define the note as a selection of the top decisions, not all of them. Add a one-page length check to the M10 exit. |
| **SC-07** | Medium | REQ-05 | **Dataset realism is validated only by self-review.** "A dataset a procurement person would nod at" is checked by a domain checklist that the same builder/AI applies. That is exactly the process weakness behind this audit. | Weakened evidence | Plan M1 exit "domain checklist passes". | Add a human procurement-literate review of the dataset, ideally a packaging buyer, to the M1 exit. |
| **SC-08** | Medium | EDGE-04, EDGE-06 | **"Taken at an angle, on a phone": the primary fixture is a synthetic warp.** A real phone photo is optional. | Weakened fidelity | Plan M1 "A real phone photo can replace it". | Make a real phone photo of a printed rate card the primary V4 fixture. Keep the synthetic version for perturbation variants. |
| SC-09 | Low | FN-14, FN-15 | Charts and analyst exports have acceptance criteria (PRD NLA-2, EXP-3) but no named tests in the plan. | Partial | Plan M8/M9 test lists | Add a chart data-binding test and an analyst-export round-trip test. |
| SC-10 | Low | EX-02 | Responses arrive "over the next nine days". Phase B triggers when no *received* response is still processing, but the docs don't say what happens with a **vendor who hasn't responded**, or with a late response after Phase B. A late response is covered by the global recompute (VAL-5); the non-responder case isn't stated. No staggered-arrival test. | Partial | Arch §5.3. PRD VAL-5. | State that non-responding vendors don't block Phase B (shown as "Awaiting response"). Add a staggered-arrival test. |
| SC-11 | Low | FN-10 | No explicit test that questionnaire answers and attached documents are reachable **from the comparison view**. | Partial | Plan M5 tests | Add a UI/contract test. |
| SC-12 | Low | DEL-01, EVAL-06 | "A live demo **we'll drive** with you": dry runs are done by the builder. No dry run is driven by someone unfamiliar with the script. | Partial | Plan M10 exit | Add one dry run driven by an uninvolved person, using unscripted questions. |
| SC-13 | Low | all | **Two requirement-ID systems.** The brief's A-01…A-25 groups source items together (e.g. A-05 = five response shapes; A-16 = four ugly edges). PRD/Plan traceability cites A-IDs, not the finer SOT IDs. Sub-items such as EDGE-05a–d and FN-12–15 are not individually traced. | Inconsistent representation (traceability) | Brief §2, §10. Plan §5.3. | When those docs are next edited (with approval), cite SOT IDs in the traceability tables. The mapping is in §5 below. |
| SC-14 | Info | FN-08, EX-04 | Interpretations consistent with the source, recorded so they stay visible:<br>• "same units" leaves some cells Not convertible, which are disclosed (consistent with EVAL-02);<br>• "cheapest per line" defaults to the ex-GST unit price, with freight separate (DL-2), and the basis is stated in every answer;<br>• "cleared the quality questionnaire" = the Quality section (DL-14). | Covered (interpretation disclosed) | PRD NLA-4, DL-2, DL-14 | None. Keep the "state the interpretation" requirement as non-negotiable. |

**No requirement was removed.** Removed features (vendor cap, FX sensitivity tool, clarification emails) are not in the source. Removing them weakens nothing in the catalogue.

---

## 3. Full coverage table

Doc references: B = brief, P = PRD, A = architecture, L = plan.

| SOT ID | Represented in | Fixture | Test (Plan) | Demo evidence planned | Status |
|---|---|---|---|---|---|
| REQ-01 | B §1, P §1, J1–J7 | Full dataset | E2E (L M9/M10) | Main path | ✅ |
| REQ-02 | P G1/G3, §1.2 metrics | — | Timed self-run (L M5 exit) | Main path | ✅ |
| REQ-03 | P J1–J7 | Seeded + sandbox | E2E | Split across seeded and sandbox RFx | 🟠 SC-04 |
| REQ-04 | P §11, L M1 | 5 vendors, 30 lines, Q, docs | M1 assertions | Grid | ✅ |
| REQ-05 | B §3.4, L M1 | Dataset | Self-checklist only | — | 🟡 SC-07 |
| FN-01 | P RFX-1, DL-17 | Sandbox | M6 co-pilot eval | Sandbox drafting | 🟠 SC-04 |
| FN-02 | P RFX-1/4/5 | — | M6 eval | Sandbox drafting | 🟠 SC-04 |
| FN-03 | P DIS-1 | Outbox | M6 | Outbox view | ✅ |
| FN-04 | P FN EXT-1, RFX-7 (P1, optional) | 5 non-template responses | M3 | Ingestion | ✅ |
| FN-05 | P EXT-1/2 | 5 formats | M3 + perturbation (M10) | Ingestion | ✅ |
| FN-06 | P CMP-1 | — | M5 contract | Grid | ✅ |
| FN-07 | P MAT-1 | Shuffled V1 | M4 matching eval | Grid | ✅ |
| FN-08 | P NRM-1…3, §5.2 | V4, V5 | M2 | Grid + trace | ✅ (SC-14) |
| FN-09 | P NRM-4, DL-15 | V2 USD | M1/M2/M5 | As-quoted view | ✅ |
| FN-10 | P CMP-5 | Certs, answers | — | Vendor panel | 🟡 SC-11 |
| FN-11 | P NLA-1 vs A §11.2 | — | M8 eval (prices/eligibility only) | Analyst | 🔴 SC-02 |
| FN-12 | P NLA-2 | — | M8 | Analyst | ✅ |
| FN-13 | P NLA-2 | — | M8 | Analyst | ✅ |
| FN-14 | P NLA-2 AC | — | none named | Analyst | 🟡 SC-09 |
| FN-15 | P EXP-1/3 | — | M9 (xlsx only) | Export | 🟡 SC-09 |
| FN-16 | P AWD-1…7 | — | M7, M9 | Award | ✅ |
| EX-01 | P §2 | — | — | — | ✅ |
| EX-02 | P J3, DIS-2 | — | none | Status board | 🟡 SC-10 |
| EX-03 | P G1 | — | Timed run | Main path | ✅ |
| EX-04 | P J6, E-09, AWD | Full | M7 oracle VP fixture | Analyst | ✅ |
| EX-05 | P NF-3 | — | Latency | Analyst | ✅ |
| EX-06 | — | — | — | — | — |
| EDGE-01 | P E-07, §11 V1 | V1 xlsx | M3 parser, M4 shuffled match | none specified | 🟡 SC-01 |
| EDGE-02 | P E-05, §11 V2 | V2 PDF | generic only | none specified | 🟡 SC-01, SC-03 |
| EDGE-03 | P E-06, §11 V3 | V3 docx | parser only | none specified | 🟡 SC-01, SC-03 |
| EDGE-04 | P E-01, DL-11 | V4 (synthetic) | M3 reconcile, vision independence | M5 Playwright path (not in runbook) | 🟠 SC-08, SC-01 |
| EDGE-05 | P E-08, §11 V5 | V5 exact sentence | M3, M4 | none specified | 🟡 SC-01 |
| EDGE-05a | P EXT-8, §5.2 | V5 | M4 group + hierarchy | none specified | 🟡 SC-01 |
| EDGE-05b | P EXT-5 AC, DL-12 | V5 | M3 inheritance tests | none specified | 🟡 SC-01 |
| EDGE-05c | P EXT-9, §5.8, DL-8 | V5 baseline rows | M2 baseline table, M4 E2E | none specified | ⚠️ SC-05, SC-01 |
| EDGE-05d | P NRM-5, §5.4 | V5 | M2 freight | none specified | 🟡 SC-01 |
| EDGE-06 | P E-01, EVAL via §6 | V4 | M3, M5 | M5 Playwright path | 🟠 SC-08, SC-01 |
| EDGE-07 | P E-02, MAT-4 | V3 27/30 | M4 E2E (generic) | none specified | 🟡 SC-01, SC-03 |
| EDGE-08 | P E-03, DL-15 | V2 USD | M1 assertion, M2, M5, M10 drill | FX drill (not a demo step) | 🟡 SC-01 |
| EDGE-09 | P E-04, VAL-3 | V4 per 100 | none named | none specified | 🟡 SC-01, SC-03 |
| AI-01 | P §8, A §7.1 | — | M0 call log | Live re-run | ✅ |
| AI-02 | P EXT-2, EXT-11 | Perturbed | M10 perturbation | Live re-run / upload | ✅ |
| AI-03 | P §8 | — | M8 off-script | Analyst | ✅ |
| AI-04 | P AI-5, NLA AC | Perturbed | Prompt hygiene, M8 perturbed | — | ✅ |
| AI-05 | P NLA-3 | — | Grounding, view tests | Show work | ✅ |
| AI-06 | P AI-8 | — | M6 eval | Sandbox | ✅ |
| DEL-01 | B §8, L M10 | — | Dry runs (self-driven) | — | 🟡 SC-12 |
| DEL-02 | B §8.2, L M10 | — | — | Recording | ✅ |
| DEL-03 | B D-3, L M10 | — | no length check | — | 🔴 SC-06 |
| DEL-04 | B D-3 | — | — | — | ✅ |
| DEL-05 | B §11, D-4 | — | — | — | ✅ |
| EVAL-01 | B §3, P §9 | All EDGE | — | — | 🟡 SC-01 |
| EVAL-02 | P §6, DL-10/16 | — | M2, M5 | Badges | ✅ |
| EVAL-03 | P §6, T-reqs, ₹4 cr dataset | — | Silent-error gates | Provenance drawer | ✅ |
| EVAL-04 | B §9, P §14, 08 | — | — | One-pager | ✅ |
| EVAL-05 | B §11 | — | — | — | ✅ |
| EVAL-06 | P §1.2 off-script | — | M8 off-script set | — | 🟡 SC-12 |
| PERM-01…06 | B, P, A (choices stated) | — | — | — | ✅ (PERM-04 —) |
| LIM-01 | P AI reqs | — | — | — | ✅ |
| LIM-02 | L header ("timeline blank") | — | — | — | — |
| INFO-01 | — | — | — | — | — |

Inconsistent (🔴, 2): FN-11, DEL-03. SC-13 (the traceability ID mismatch) cuts across all items and isn't counted per item.

---

## 4. Named-edge-case matrix (fixture / test / demo)

This is a draft for SC-01 and SC-03. It is **not yet adopted**: it needs approval before it goes into the plan and runbook.

| SOT ID | Dataset fixture (exists) | Required named test (✔ exists / ✘ to add) | Demo strategy (proposed) |
|---|---|---|---|
| EDGE-01 Excel ignores template | V1 own-layout xlsx | ✔ M3 parser locators; ✔ M4 shuffled-row matching | Open V1 in the inbox → show the original sheet → the same values aligned in the grid |
| EDGE-02 PDF footnote discount | V2 letterhead PDF | ✘ "footnote discount extracted, scoped and applied" (EXT-6/NRM-7) | Provenance drawer on a V2 cell → the trace step "−5% footnote discount", with the footnote highlighted |
| EDGE-03 Word prose commercials | V3 docx | ✘ "each commercial term extracted with sentence evidence" | V3 vendor panel → terms → click a term → the sentence highlighted |
| EDGE-04 / 06 angled phone photo | V4 photo (make it a real phone photo, SC-08) | ✔ M3 reconciliation + vision independence; ✔ M5 Playwright | Review queue → V4 READ_DISAGREEMENT item → both reads + crop → resolve |
| EDGE-05 terse email | V5 exact sentence | ✔ M3 DL-12; ✔ M4 group/hierarchy | V5 column → one cell per component (05a–d) |
| EDGE-05a ₹42/kg 5-ply | V5 | ✔ M4 | 5-ply cell trace: ₹/kg × reference weight |
| EDGE-05b "38" | V5 | ✔ M3 inheritance | 3-ply cell: "unit inferred from '₹42/kg'" badge |
| EDGE-05c rest same as last year | V5 + baseline rows | ✔ M2 baseline table; ✘ interpretation-disclosure test (SC-05) | 7-ply cells: ASSUMED from V5's own last-year price; UNRESOLVED where not available |
| EDGE-05d freight extra | V5 | ✔ M2 freight | Landed toggle → V5 "freight unknown" |
| EDGE-07 27 of 30 | V3 | ✘ "missing lines disclosed in analyst answers and the scenario" | Coverage 27/30 chip → ask "who didn't quote everything?" |
| EDGE-08 USD | V2 | ✔ M1/M2/M5; M10 drill | As-quoted toggle shows USD → edit the FX rate → a ranking flips |
| EDGE-09 per box vs per 100 | V4 | ✘ "per-100 converted; unlabelled → UNIT_SUSPECT, excluded until resolved" | V4 cell "Looks like per 100 — confirm?" → accept → value and peers update |

---

## 5. Legacy ID mapping (brief A-IDs → SOT IDs)

| Brief | SOT |
|---|---|
| A-01 | FN-01, AI-06 |
| A-02 | FN-02 |
| A-03 | FN-03, PERM-02 |
| A-04 | FN-04 |
| A-05 | FN-05, EDGE-01…05 (incl. 05a–d) |
| A-06 | FN-06 |
| A-07 | FN-07, FN-08, FN-09 |
| A-08 | FN-10 |
| A-09 | FN-11 |
| A-10 | FN-12…15 |
| A-11 | AI-05 |
| A-12 | FN-16 |
| A-13 | REQ-04 |
| A-14 | REQ-05 |
| A-15 | AI-01…04, PERM-05, LIM-01 |
| A-16 | EDGE-06…09 |
| A-17 | EVAL-02 |
| A-18 | EVAL-03 |
| A-19 | EVAL-04 |
| A-20 | EX-04 |
| A-21 | DEL-01, EVAL-06 |
| A-22 | DEL-02, PERM-06 |
| A-23 | DEL-03, DEL-04 |
| A-24 | DEL-05, EVAL-05 |
| A-25 | PERM-01, PERM-03, PERM-04 |

SOT items with **no** brief A-ID: REQ-01, REQ-02, REQ-03, EX-01, EX-02, EX-03, EX-05, EVAL-01, LIM-02. Of these, REQ-03 (SC-04) and EX-02 (SC-10) carry open findings.

---

## 6. Readiness statement
Per the root `CLAUDE.md` rule, this audit **does not** declare the project ready to build. That requires:
1. SC-01 to SC-04 resolved, or explicitly accepted by the owner as known gaps;
2. owner approval of any spec changes proposed above;
3. a re-run of this source-to-deliverable coverage audit after those changes.

---

## 7. Resolution status (updated 2026-11-04, after the owner approved SC-01…SC-04)
| Finding | Status | Where | Note |
|---|---|---|---|
| SC-01 | **Resolved in spec** | `10_demo_runbook.md` §3; Plan M1/M10 | Edge matrix complete for EDGE-01…09 |
| SC-02 | **Resolved in spec** | PRD NLA-11…13, AI-16; Arch §11.1–11.5 | Views + capped cited snippets; no full text |
| SC-03 | **Resolved in spec** | Plan §3a T-EDGE-02/03/07/09 (+ all other EDGE) | Behavioural assertions + negatives |
| SC-04 | **Resolved in spec** | DL-19; PRD RFX-9…11; Runbook §2 | One RFx P1→P11; sandbox preserved |
| SC-05…SC-11 | **Resolved in spec (2026-11-04)** | See §8 | |
| SC-12 | **Resolved** | FD-7 rev. 2, C1 | Unscripted dry run is in the approved schedule |
| SC-13 | **Deferred** (owner decision) | — | The existing SOT mapping (§5) is retained |

"Resolved in spec" means not yet implemented or verified. Per root `CLAUDE.md` rule 4, a full re-run of this coverage audit is required before any "ready to build" declaration. **No such declaration is made here.**

---

## 8. Resolution status for SC-05…SC-13 (2026-11-04)
| Finding | Status | Resolution | Where | Validating tests / gates |
|---|---|---|---|---|
| SC-05 | **Resolved in spec** | DL-20: both readings kept; UNRESOLVED (REFERENCE_AMBIGUOUS); candidates shown; template clarification request; applied only after an audited confirmation; freight never a candidate | PRD §0.1, J9, EXT-9, NRM-8, REV-4, §5.8, §6.3, §7, E-33; Arch §5.2, §8 step 9, §13; Runbook EDGE-05c | T-EDGE-05c-A, T-EDGE-05c-B, T-CLAR-01 |
| SC-06 | **Resolved** | Stale references corrected (Plan M10). Top-10 decisions defined. **PDF generated and validated as exactly one page** | `docs/deliverables/one_page_note.{html,pdf}`; Plan M10, C3 | T-NOTE-01 (passed pre-build; re-run at C3) |
| SC-07 | **Resolved in process; review pending** | DL-22: external human review with a checklist (pricing, specs, vendor behaviour, terms, questionnaire), feedback and corrections logs, sign-off. AI self-review excluded. | `11_dataset_realism_review.md`; PRD §11; Plan M1/M1-final | M1-final gate (manual) |
| SC-08 | **Resolved in process; photo pending** | DL-21: genuine phone photo is the primary fixture. Print card spec, capture protocol, EXIF/authenticity checks, readability annotations. Synthetic image kept for tests only. | `12_phone_photo_capture_kit.md`; PRD §11; Plan M1/M1-final; Runbook EDGE-04 | T-EDGE-04 (real photo), manifest check |
| SC-09 | **Resolved in spec** | Chart data binding and export fidelity requirements + tests | PRD NLA-2/EXP-1 AC; Arch §11.1, §13 | T-OUT-01, T-OUT-02, T-OUT-03 |
| SC-10 | **Resolved in spec** | "Awaiting response" vendor state: no quote rows, never zero or MISSING, excluded and listed, award acknowledgement, valid at every arrival state | PRD J3, DIS-2, CMP AC, AWD-3, §7, E-34; Arch §5.3, ADR-18; Runbook P5 | T-ARR-01, T-ARR-02, T-ARR-03 |
| SC-11 | **Resolved in spec** | Documents openable from 4 entry points + document API | PRD CMP-5; Arch §5.2 | T-DOC-01, T-DOC-02 |
| SC-12 | **Resolved** | Covered by FD-7 rev. 2 (C1, protected) | Plan §2.4 | Runbook §7 checklist |
| SC-13 | **Deferred** | Existing SOT mapping retained (§5) | — | — |

### 8.1 Updated source-to-requirement traceability (affected SOT items only)
| SOT ID | Previous status | New status | Fixture | Test | Demo evidence |
|---|---|---|---|---|---|
| REQ-05 | 🟡 Partial (SC-07) | 🟢 Covered in spec; **pending external review** | Full dataset | M1-final realism gate | — |
| FN-10 | 🟡 Partial (SC-11) | ✅ Covered | V1–V5 attachments | T-DOC-01/02 | Runbook P8 (4 entry points) |
| FN-14 | 🟡 Partial (SC-09) | ✅ Covered | — | T-OUT-01 | Runbook Q2 + Show work |
| FN-15 | 🟡 Partial (SC-09) | ✅ Covered | — | T-OUT-02/03 | Runbook Q10 + P11 |
| EX-02 | 🟡 Partial (SC-10) | ✅ Covered | Arrival subsets | T-ARR-01/02/03 | Runbook P5 (Q5 with V2 awaiting) |
| EDGE-04 | 🟠 Weakened (SC-08) | 🟢 Covered in spec; **pending real photo** | Real phone photo (primary) + synthetic | T-EDGE-04 | Runbook EDGE-04 row |
| EDGE-05c | ⚠️ Interpretation risk (SC-05) | ✅ Covered | V5 + baseline prices + baseline terms | T-EDGE-05c-A/B, T-CLAR-01 | Runbook EDGE-05c row |
| EDGE-06 | 🟠 Weakened (SC-08) | 🟢 Covered in spec; **pending real photo** | As EDGE-04 | T-EDGE-04 | As EDGE-04 |
| DEL-01 / EVAL-06 | 🟡 Partial (SC-12) | ✅ Covered | — | C1 unscripted run | Runbook §7 |
| DEL-03 | 🔴 Inconsistent (SC-06) | ✅ Covered | — | T-NOTE-01 | `one_page_note.pdf` |

Statuses for SC-01…SC-04 items are in §7. **Per root `CLAUDE.md` rule 4, a full coverage audit re-run is still required before any "ready to build" or "ready to submit" declaration.** Two items depend on external human inputs (REQ-05 review, EDGE-04/06 photo).

---

## 9. Implementation coverage audit (2026-11-05)

**Audited:** the code and tests as built (backend `app/`, 200 backend tests, 8 eval tests in `EVAL_ROOT`, frontend `src/`), the generated dataset in `app_data/`, and `10_demo_runbook.md`, against all 66 items of `00_source_of_truth.md`. The PDF was not re-read: no document disagreement was found that needed it (CLAUDE.md rule 5).
**Scope rule:** findings only. No requirement, priority or test was changed by this audit.
**Independence caveat:** written by the same AI that built the code. Statuses rest on named tests that can be re-run (`make test`, `make eval-m1a`), not on self-assessment, but the owner should spot-check the 🔴 and ⛔ items.

### 9.1 Verdict

**Not ready to submit.** No requirement has been weakened or removed. The deterministic core is built and tested. The open items fall into three groups:
1. **Blocked on external inputs:**
   - the API key, needed for every live AI loop and every eval gate;
   - the real phone photo and the external realism review, needed for M1b, the remaining 3 vendors and their edge-case fixtures;
   - Tesseract, needed for the photo path (M3b).
2. **Two build gaps that can be fixed now:** the co-pilot does not draft the RFx *scope* (FN-02), and analyst *charts* do not exist (FN-14).
3. **Deliverables not yet started:** M10 dry runs, the recorded walkthrough and the one-page note.

| Status | Count | Meaning |
|---|---|---|
| ✅ Built and tested | 23 | Code + named test(s) pass; demo path exists |
| 🟡 Partial | 25 | Built and unit/flow-tested with a mocked model, but a live run, a fixture, a named test or a UI path is still missing |
| 🔴 Gap | 2 | A required capability is missing from the build (FN-02 scope, FN-14 charts) |
| ⛔ Blocked / not started | 10 | Depends on external inputs (M1b gates, API key, Tesseract) or on M10 |
| ○ Optional, not done | 2 | DEL-05, EVAL-05 |
| — Not applicable | 4 | EX-06, PERM-04, LIM-02, INFO-01 |
| **Total** | **66** | |

### 9.2 Findings

| # | Sev. | SOT IDs | Finding | Blocked on | Recommended action |
|---|---|---|---|---|---|
| **IA-01** | **High** | REQ-04, EDGE-02, EDGE-03, EDGE-04, EDGE-06, EDGE-07, EDGE-08, EDGE-09 | **The dataset has 2 of 5 vendors** (V1 xlsx, V5 email + questionnaire). V2 (letterhead PDF, USD, footnote discount, mailers ALTERNATE), V3 (docx prose terms, 27/30) and V4 (phone photo, per-100) are not generated, so these edge cases have **no fixture**. Their engine rules are built and unit-tested on synthetic cells (§9.4). | M1b gates: real phone photo (DL-21) + external realism review (DL-22). The owner instruction is not to start M1b before them. | Provide the photo and reviewer; then M1b → M3b → B2. |
| **IA-02** | **High** | AI-01, AI-02, AI-03, AI-06, FN-01, FN-05, FN-11, EX-04, EVAL-03, EVAL-06 | **No AI loop has run against the live model.** Every gateway call is real code (`claude-opus-5-5`, structured outputs, append-only conversations, call log), but every test uses a mocked transport. The extraction accuracy, silent-error, co-pilot (≥ 4/5 conformance), analyst and perturbation evals (B2–B4) have not run. | `ANTHROPIC_API_KEY` | Set the key; run the slice live first, then the eval gates. |
| **IA-03** | **High** | FN-02 | **The co-pilot drafts lines, questionnaire and terms, but not the RFx scope.** `Rfx` has no scope field; the canonical spec has one (`scope`). FN-02 names four parts: scope, line items, questionnaire, terms. | — (fixable now) | Add `Rfx.scope`; draft it with a citation in the gap/terms step; include it in the header and the seeded fallback. |
| **IA-04** | **High** | FN-14 | **Analyst charts are not built.** No chart rendering; no data-binding test (T-OUT-01). | — (fixable now) | Render charts in the Analyst screen from tool-result rows only, plus the binding test (chart data = result rows). |
| IA-05 | Medium | FN-13, FN-10 | **Tables and answers-beside-numbers are only partly shown.** (a) Analyst tool-result tables appear only as raw JSON under "Show work" and as exports, not as a rendered table block. (b) Questionnaire answers and documents are on the Vendors screen, not reachable from the comparison grid. No contract test for either. | — (fixable now) | Render result tables in the answer; add a vendor-header link from the grid to the eligibility panel and documents; add the T-DOC test. |
| IA-06 | Medium | FN-07, EDGE-01 | **No shuffled-rows test.** Matching is by item code / exact dims / AI proposal (never by row order), but the MAT-1 AC "shuffling the rows of the V1 sheet produces identical matches" has no test, and EDGE-01's shuffled-layout variant does not exist. | — (deterministic part fixable now; the extraction part needs the key) | Add a row-shuffle test on the V1 workbook through matching and Phase A. |
| IA-07 | Medium | EDGE-04, EDGE-06, EDGE-09, FN-05 | **The image path is not built:** perspective correction, OCR + vision dual read, READ_DISAGREEMENT. Images and scanned PDFs are parsed as `deferred` (shown, never treated as empty). | Tesseract; real photo | M3b after the gates. |
| IA-08 | Medium | DEL-01…04, EVAL-06 | **Deliverables not started:** dry runs (including the unscripted one), the recorded walkthrough and the one-page note. | M1b + live runs first | M10. |
| IA-09 | Low | REQ-02, EX-05 | No timed end-to-end or EX-04 latency test (the minutes-not-a-day evidence). | API key | Add timing to the live slice and B4. |
| IA-10 | Low | all EDGE | **Test names differ from the runbook's T-IDs** (T-EDGE-05a, T-CLAR-01, …). The mapping is in §9.4; nothing is missing because of it. | — | Keep §9.4 as the mapping, or rename tests at M10. |
| IA-11 | Low | FN-16, EVAL-03 | **PRD wording awaiting owner decision:** PRD §5.4 and architecture §11.3 say savings on freight-dependent lines are "lower bounds". The spend there is the lower bound, so savings are an upper bound. The code and memo state it that way; the PRD is unedited. | Owner | Approve the wording fix. |

### 9.3 Coverage table (implementation)

| SOT ID | Status | Evidence (code → tests) | Open |
|---|---|---|---|
| REQ-01 | 🟡 | Co-pilot → responses → analyst connected: `test_slice_t_slice_01` | Live run (IA-02) |
| REQ-02 | 🟡 | No retyping; what-if via `run_scenario` | Timed test (IA-09) |
| REQ-03 | ✅ | One RFx draft → send → process → scenario → acknowledged memo: `test_vertical_slice`, `test_seeded_fallback_is_labelled_conforming_and_flows` | — |
| REQ-04 | ⛔ | 30 lines, questionnaire, attachments ✅; **2 of 5 vendors** | IA-01 |
| REQ-05 | ⛔ | Generator + domain constants | External review (IA-01) |
| FN-01 | 🟡 | Mapping, gaps, questionnaire via gateway; `test_rfx_m6a`, `test_eligibility_m6b` | Live co-pilot eval (IA-02) |
| FN-02 | 🔴 | Lines ✅ questionnaire ✅ terms ✅ (`test_upload_rules_and_header`) | **Scope missing (IA-03)** |
| FN-03 | ✅ | Outbox message per vendor: `test_full_flow_conformance_send_deliver` | — |
| FN-04 | ✅ | No template required; eml/xlsx/docx/pdf parsers: `test_parsers` | — |
| FN-05 | 🟡 | eml, xlsx, docx, text PDF ✅; image/scanned deferred | IA-02, IA-07 |
| FN-06 | ✅ | One grid, all vendors incl. awaiting: `test_comparison_m5a` | — |
| FN-07 | 🟡 | Code/dims/AI matching, one-to-one, ALTERNATE: `test_matching_m4b` | Shuffle test (IA-06) |
| FN-08 | ✅ | per-100/1000/dozen/kg, NOT_CONVERTIBLE, UNIT_SUSPECT: `test_normalize_m2a`, `test_resolutions_m2b` | — |
| FN-09 | 🟡 | FX conversion, original kept, rate disclosed: `test_fx_rate_set_renormalises…`, `test_fx_conversion_preserves_original` | USD vendor fixture (IA-01) |
| FN-10 | 🟡 | Eligibility panel with provenance: `test_vertical_slice` (M6b block) | Reachable from grid (IA-05) |
| FN-11 | 🟡 | `v_answers`, `v_doc_facts`, scenario tool: `test_analyst_m8b` | Live analyst eval (IA-02) |
| FN-12 | 🟡 | Narrative + grounding: `test_analyst_m8a/m8b` | Live (IA-02) |
| FN-13 | 🟡 | Tables in results + export | Rendered table (IA-05) |
| FN-14 | 🔴 | — | **Charts (IA-04)** |
| FN-15 | ✅ | xlsx/csv/md/html round trips: `test_exports_m9b` | — |
| FN-16 | ✅ | Readiness + acknowledgement + memo with sources, assumptions, exclusions: `test_scenario_m7b`, `test_exports_m9b` | — |
| EX-01 | ✅ | Buyer-centred screens | — |
| EX-02 | 🟡 | Awaiting columns, provisional set, per-vendor processing: `test_comparison_m5a`, `test_failure_injection_rerun_and_carry_forward` | Staggered-arrival test with 5 vendors (IA-01) |
| EX-03 | ✅ | Zero manual entry in the slice | — |
| EX-04 | 🟡 | Quality-scope strict scenario + 20-combination oracle: `test_scenario_m7b` | Live analyst (IA-02) |
| EX-05 | 🟡 | — | IA-09 |
| EX-06 | — | | |
| EDGE-01…09 | see §9.4 | | |
| AI-01 | 🟡 | Real gateway, call log: `test_gateway` | IA-02 |
| AI-02 | 🟡 | Evidence-verified extraction: `test_verify`, `test_extract_stage` | Perturbation eval (IA-02) |
| AI-03 | 🟡 | Bounded tool loop, grounding, lint | Off-script eval (IA-02) |
| AI-04 | 🟡 | No dataset literals in app code/prompts: `test_prompt_hygiene` (eval) | Perturbed-dataset analyst eval (IA-02) |
| AI-05 | ✅ | Numbers only from tool results; drawer to source: `test_analyst_m8a/m8b`, `test_review_m5b` | — |
| AI-06 | 🟡 | Co-pilot calls logged (`copilot`, `copilot_mapping`) | Live (IA-02) |
| DEL-01…04 | ⛔ | — | IA-08 |
| DEL-05 | ○ | | |
| EVAL-01 | 🟡 | 5 of 13 edge items fully covered (§9.4) | IA-01, IA-07 |
| EVAL-02 | ✅ | Statuses, chips, no number for excluded cells, review queue, banners: `test_comparison_m5a`, `test_exports_m9b`, `test_review_m5b` | — |
| EVAL-03 | 🟡 | Provenance drawer, audit log, grounding, sticky resolutions, readiness ack | Silent-error metric (IA-02) |
| EVAL-04 | ✅ | DL-1…32 decision log | Note (IA-08) |
| EVAL-05 | ○ | | |
| EVAL-06 | 🟡 | Seeded fallback; graceful "model unavailable" | Dry runs (IA-08) |
| PERM-01/02/03/05/06, LIM-01 | ✅ | Corrugated; simulated outbox; choices recorded | — |
| PERM-04, LIM-02, INFO-01 | — | | |

### 9.4 Named edge cases: fixture / test / demonstration (CLAUDE.md rule 3)

A gap in any of the three columns is a defect; each one is listed with what closes it.

| SOT ID | Fixture | Test (as built) | Demo strategy | Status |
|---|---|---|---|---|
| EDGE-01 | ✅ V1 own-layout xlsx with slabs, set price, notes | ✅ mocked read through the pipeline (`test_vertical_slice`); slab selection (`test_slab_selection`); 🟡 shuffled-rows variant missing | ✅ runbook row | 🟡 (IA-06; live accuracy IA-02) |
| EDGE-02 | ⛔ V2 letterhead PDF not generated | 🟡 engine: discount once, in scope (`test_discounts_once_and_in_scope`); PDF text parser (`test_parsers`) | ✅ runbook row | ⛔ fixture (IA-01) |
| EDGE-03 | ⛔ V3 docx not generated | 🟡 docx parser (`test_docx_paragraphs_and_tables`); prose-term extraction untested | ✅ runbook row | ⛔ fixture (IA-01) |
| EDGE-04 | ⛔ real photo pending | ⛔ OCR/vision path not built | ✅ runbook row | ⛔ (IA-01, IA-07) |
| EDGE-05 | ✅ exact sentence in `01_V5_quote.eml` | ✅ `test_vertical_slice`, `test_review_m5b` | ✅ | ✅ (live IA-02) |
| EDGE-05a | ✅ | ✅ group expansion + reference weight ASSUMED + billed-weight caveat (`test_reference_weight_is_assumed…`, slice line 7) | ✅ | ✅ |
| EDGE-05b | ✅ | ✅ unit inherited, both spans cited (`test_provenance_drawer_cites_the_sentence`) | ✅ | ✅ |
| EDGE-05c | ✅ + baseline prices/terms | ✅ both readings, nothing applied before confirmation, freight never carried, pack section (`test_reference_confirmation_*`, `test_clarification_pack_is_deterministic_and_complete`, `test_reference_confirmation_terms_marks_reading_b`) | ✅ | ✅ |
| EDGE-05d | ✅ | ✅ freight UNKNOWN, landed not calculable, freight-aware break-even (`test_freight_bases`, `test_freight_aware_selection_and_break_even`) | ✅ | ✅ |
| EDGE-06 | ⛔ as EDGE-04 | 🟡 uncertainty display generic (statuses, review queue); dual-read display not built | ✅ runbook row | ⛔ (IA-07) |
| EDGE-07 | ⛔ V3 27/30 not generated | ✅ MISSING never filled; coverage disclosed in answers (exercised on V1's real 28/30: `test_vertical_slice`, `test_sql_caveats_flag_excluded_values_and_coverage`) | ✅ runbook row | 🟡 fixture (IA-01) |
| EDGE-08 | ⛔ V2 USD not generated | ✅ conversion, original kept, rate + source disclosed, rate edit recomputes, exposure per 1% (`test_fx_rate_set_renormalises…`, `test_exposures`) | ✅ runbook row | 🟡 fixture (IA-01) |
| EDGE-09 | ⛔ V4 per-100 not generated | ✅ per-100 conversion, UNIT_SUSPECT withheld + suggestion + accept recomputes (`test_qty_units`, `test_accept_unit_suspect_suggestion_records_chosen_unit`) | ✅ runbook row | 🟡 fixture (IA-01) |

**Fully covered (fixture + test + demo): 5 of 13** (EDGE-05, 05a–d). **Engine ready, fixture missing: 4** (EDGE-07, 08, 09; EDGE-02 partly). **Not buildable yet: 3** (EDGE-03 extraction, EDGE-04, EDGE-06).

### 9.5 Readiness statement

Per CLAUDE.md rule 4: **not ready to submit.** The following must close first:
- IA-01 and IA-02, which need the owner's inputs;
- IA-03 and IA-04, which can be fixed now;
- IA-05 and IA-06, which can be fixed now;
- IA-07 and IA-08, which follow the gates.

Re-run this audit after M1b and the first live eval round.

### 9.6 Resolution status for IA-03…IA-06 (2026-11-05, owner-approved fixes)

| # | SOT IDs | Fix | Tests | New status |
|---|---|---|---|---|
| IA-03 | FN-02 | `Rfx.scope` added. The co-pilot drafts it from the buyer's words in the open-fields step, and it is applied only if its quote appears in the source. The seeded fallback carries the canonical scope; the RFx header and Co-pilot screen show it. | `test_scope_is_drafted_from_the_buyers_words_fn_02`; slice flow | FN-02 🔴 → ✅ |
| IA-04 | FN-14 | `make_chart` tool + binder (`analysis/charts.py`). The spec names columns only; the data is injected from the referenced result. Inline data, unknown fields and non-chart types are rejected. Rows without a number are listed, never drawn as zero. SVG rendering in the Analyst screen. | `test_charts_tables.py` (binder, rejection, data = result rows, error reported to the model) | FN-14 🔴 → 🟡 (live analyst use pending, IA-02) |
| IA-05 | FN-13, FN-10 | Every query / `run_scenario` result is returned as a table, rendered in the answer with per-table xlsx/csv export. Comparison vendor columns carry the Quality/Commercial result and the attached documents (type, validity, evidence ref). | `test_analyst_chart_equals_result_rows`, `test_comparison_carries_answers_and_documents_fn_10` | FN-10 🟡 → ✅; FN-13 🟡 (live pending) |
| IA-06 | FN-07, EDGE-01 | Row-shuffle test on V1's actual workbook through parsing, matching and Phase A (3 seeds). | `test_shuffle_m4b.py` | FN-07 🟡 → ✅; EDGE-01 still 🟡 (live extraction accuracy, IA-02) |

**Updated counts:**

| Status | Count |
|---|---|
| ✅ Built and tested | 26 |
| 🟡 Partial | 24 |
| 🔴 Gap | 0 |
| ⛔ Blocked / not started | 10 |
| ○ Optional | 2 |
| — Not applicable | 4 |
| **Total** | **66** |

Chart rendering was checked by type-check and the binding tests. It was **not visually checked in the browser**: the demo server has no API key, so no live answer produces a chart.

**Readiness:** still **not ready to submit**. Open findings: IA-01 and IA-02 (need the owner's inputs), IA-07 and IA-08 (follow the gates), and IA-09…IA-11 (low).
