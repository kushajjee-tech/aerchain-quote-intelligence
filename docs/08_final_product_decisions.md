# Final Product Decisions
**Date:** 2026-11-04 · **Status:** Locked · **Checked against:** `docs/assignment.pdf` (both pages)
**Applies to:** `01_product_brief.md` v1.3 · `02_PRD.md` v1.2 · `03_architecture.md` v1.2 · `04_implementation_plan.md` v1.2 · logged in `06_fix_log.md` §6
*(There is no `07_*` document. This file follows the existing numbering at the user's request.)*

These seven decisions close every open product question from the pre-build review (`06_fix_log.md` §5). They override any earlier text that conflicts with them. Each one is a product decision **[R]** made within the assignment's "total liberty" (A-25). None of them removes an assignment requirement.

---

## FD-1 — Quality questionnaire = Quality section only → **DL-14**
**Decision.** Only the **Quality** section decides whether a vendor has "cleared the quality questionnaire". **Commercial** questions are evaluated and shown separately, and are never described as part of the quality questionnaire.

**Assignment link.** VP question: *"…only among vendors who cleared the quality questionnaire"* (A-20).

**Consequences.**
- Scenario `eligibility_scope` defaults to `quality`.
- `all_mandatory` (Quality + Commercial) is an explicit opt-in. It is labelled "quality and commercial requirements" and never "quality questionnaire".
- V5 (Quality Pass, Commercial Fail) is eligible for the VP's split. The answer notes V5's commercial result separately.

| Where | Reflected in |
|---|---|
| Brief | DL-14 row, F-RFX-4, E-09 |
| PRD | §0.1 DL-14, RFX-4, CMP-5, ELG-2/3 + AC, §5.7, §11 |
| Architecture | §10, §11.2 `v_vendors`, §11.6 |
| Plan | M2 roll-up tests, M8 trap set |

## FD-2 — V2 quotes its entire response in USD → **DL-15**
**Decision.** V2's whole response (every line, freight, document terms) is in **USD**. Original USD values are preserved. Conversion to INR uses a **stated, editable FX rate with its as-of date and source**. Each conversion step is visible in the trace. Converted cells are `ASSUMED (FX_RATE)` with the `FX` flag. Editing the rate triggers a global recompute, marks saved scenarios stale and supersedes acknowledged awards.

**Assignment link.** *"The one who quoted in USD"* (A-16). This scenario must never be removed.

| Where | Reflected in |
|---|---|
| Brief | DL-15 row, E-03, §8.1 V2 |
| PRD | §0.1 DL-15, NRM-4 + AC, §5.3, §6.3, E-03, §11 V2 |
| Architecture | §8 step 7, §11.2 `v_quotes` (original currency/price) |
| Plan | M1 dataset, M2 FX tests, M7 stale/superseded, M10 FX drill |

## FD-3 — Needs Review values are excluded from formal award calculations by default → **DL-16**
**Decision.**
- **Formal award calculations** (Award screen scenarios, readiness check, award memo, award export) **exclude** `NEEDS_REVIEW` values by default, along with UNRESOLVED, NOT_CONVERTIBLE and MISSING, which are always excluded.
- The buyer can **explicitly override** this per scenario. The override:
  - shows a warning listing the affected cells and the money at risk;
  - writes an audit record;
  - is listed in the memo and the readiness check.
- Resolving the individual review items (Accept / Correct) is the normal way to bring values in.
- **Exploratory analysis** (the comparison grid, analyst questions) can include Needs Review values **on request**, labelled **"Exploratory — includes N values needing review"** with caveats. Exploratory results are never presented as award figures. Turning one into an award recomputes it under the formal policy.
- The analyst's default for `run_scenario` matches the formal policy, so the VP's answer and the award agree unless someone explicitly asks otherwise.

**Assignment link.** *"Trust. Would a buyer with ₹4 crore on the line act on what's on your screen?"* (A-18); *"defensible award decision"* (A-12).

| Where | Reflected in |
|---|---|
| Brief | DL-16 row, §7.2 table, E-21 |
| PRD | §0.1 DL-16, J6/J7, CMP-1, NLA-4/10 AC, AWD-1/3 + AC, §6.2, §11 headline |
| Architecture | §9 `status.includable(cell, context)`, §11.1/11.3, §13 |
| Plan | M2 status-table tests, M7 policy/override tests, M8 exploratory-label tests |

## FD-4 — Historical pricing and freight → **DL-8 (amended)**
**Decision.**
- "Same as last year" uses **only the same vendor's** historical price for the **same line and matching specification**. Another vendor's historical price is **never** substituted.
- Historical **freight terms are never carried forward**. Freight always comes from **this year's** response. If this year's response says nothing about freight, or says "freight extra" with no amount, freight is **UNKNOWN** and landed cost is not calculated.
- If last year's basis differed (e.g. delivered), that is shown as a caveat only (`FREIGHT_BASIS_CHANGED`). It is never used as a value.

**Assignment link.** The email example *"rest same as last year, freight extra"* (A-05 narrative).

| Where | Reflected in |
|---|---|
| Brief | DL-8 row, E-08, PD-11 |
| PRD | §0.1 DL-8, NRM-5/8, §5.4, §5.8, E-08/26/27 |
| Architecture | §8 steps 8–9 |
| Plan | M2 baseline + freight tests |

## FD-5 — Live RFx drafting on a separate sandbox → **DL-17**
**Decision.** Live co-pilot demonstrations use a separate **sandbox RFx**. The seeded RFx and the **prepared five-vendor dataset are never changed** by live drafting. The sandbox can receive uploads only.

**Assignment link.** *"A buyer talks an RFx into existence"* (A-01); *"live demo we'll drive with you"* (A-21).

| Where | Reflected in |
|---|---|
| Brief | DL-17 row |
| PRD | §0.1 DL-17, J1, RFX-8 + AC, §7 `Rfx.kind` |
| Architecture | §4 (RFx switcher), §12 |
| Plan | M6 sandbox isolation test, M10 runbook |

## FD-6 — Engineering constants and ₹/kg → ₹/box conversion → **DL-18** (amends DL-1, DL-12)
**Decision.**
1. **Constants are configurable and versioned.** This covers flute take-up factors, joint allowance, spec tolerances and check thresholds.
   - They live in a versioned constant set. Every constant records `value`, `unit`, `validation_status` ∈ {UNVALIDATED, VALIDATED}, `source` and `validated_by/at`.
   - Every trace records the constant-set version used.
   - **Unvalidated constants are labelled "approximate engineering constant — not validated"** in the UI, traces, exports and memo. They are never described as industry facts.
   - Changing the active set is audited and triggers a global recompute.
2. **Weight source hierarchy for ₹/kg → ₹/box** (each source, and each calculation step, is recorded):
   | Priority | Weight source | Status effect | Formal award use |
   |---|---|---|---|
   | 1 | **Documented SKU reference unit weight** (RFx line field with its source document, e.g. the buyer's item master or spec sheet) | flag `CONVERTED`, no status change | Yes |
   | 2 | **Vendor-stated unit weight** in the response, used when the SKU has no reference weight. When both exist, the reference weight is used and the vendor weight is a cross-check: a difference > tolerance → `NEEDS_REVIEW (WEIGHT_MISMATCH)`. | flag `CONVERTED` | Yes (unless mismatch) |
   | 3 | **Estimated weight from approximate engineering constants.** Supported item types with complete construction only: RSC, or die-cut/pad with a blank size. | **`NEEDS_REVIEW (WEIGHT_ESTIMATED)`** + assumption `METHOD_CONSTANTS`. After buyer review → `ASSUMED`. | **Not without buyer review** (FD-3) |
   | 4 | No reliable weight: unsupported item type, incomplete construction, or no reference/vendor weight and no estimate possible | `NOT_CONVERTIBLE` | No |
   | — | Weight evidence present but unreadable or conflicting within the response | `UNRESOLVED` | No |
3. Weight formulas are never applied to incompatible products (partitions, unknown types).

**Assignment link.** *"₹42/kg for the 5-ply, 38 for the 3-ply"*; *"same units"* (A-07); *"Don't fake the extraction, don't fake the reasoning"* (A-15).

| Where | Reflected in |
|---|---|
| Brief | DL-18 row, DL-1/DL-12 notes, E-08 |
| PRD | §0.1 DL-18, RFX-3, NRM-3 + AC, §5.2 (rewritten), §6.2/6.3, §7 (`RfxLine.reference_unit_weight`, `ConstantSet`), E-08/22/23, §11 |
| Architecture | §8 step 3, §14 config versioning |
| Plan | M1 reference weights, M2 hierarchy + constants tests, M4 V5 E2E |

## FD-7 — Implementation timeline
**Decision.**
- **Current (rev. 4): 29.0 days of estimated effort for one builder.** That is 20.5 P0 essential implementation + 6.5 testing, evaluation & integration + 2.0 demo preparation: rev. 3 (25.75) + 3.5 for the approved PM-review changes − 0.25 scope cut (Plan §2.6). Re-sequenced around a vertical slice at day ~6.5, with checkpoints at days 10, ~15 and ~20. **It is not a calendar deadline or a contractual commitment.**
- **Committed scope:** every P0 requirement. Not reducible: extraction tuning (B2), integration and debugging (B6), independent evaluation (B1, B4, B5), unscripted demo preparation (C1).
- **Rejected trade-offs:** O3, X1, X2, X3, X4.
- **Optional efficiency improvements:** O1 and O2, allowed only if functionality is unchanged:
  - O1: constant-set activation via the config file must still write an `AuditEvent`, trigger the global recompute and mark scenarios stale;
  - O2: the status board must still update without a manual refresh (polling is acceptable).
  - Any saving is taken as slack, not as a reduced commitment.
- **P1 (3.25 d):** outside the committed schedule. Started only after all P0 exits.
- All P0 requirements take priority. If time is short, **P1 features are dropped first**, then P2 (already out of the demo).
- P0 items on the "never cut" list (PRD §12.4) are not traded for time.

| Where | Reflected in |
|---|---|
| Brief | §8 (deliverables note) |
| PRD | §12.5 |
| Plan | header, §2 (bottom-up §2.1–2.8), §6 risk row, §7 |

### FD-7 revision history
| Rev. | Date | Figure | Status |
|---|---|---|---|
| 0 | 2026-11-04 | 15 build + 2 demo = 17 d | Superseded |
| 1 | 2026-11-04 | **16.5 build + 2 demo = 18.5 d** (+1.5 for audit fixes SC-01…SC-04, kept visible) | **Approved by the owner, subject to a bottom-up review** |
| 4 | 2026-11-04 | **20.5 + 6.5 + 2.0 = 29.0 d**: +3.5 for the PM-review changes (P0-1 0.75, P0-2 0.25, P0-3 0, P0-4 0.5, P1-5 1.0, P1-9 0.25, P1-10/11 0.25, P1-6 0.5), −0.25 B3 cut enabled by the deterministic import | **Approved changes recorded.** Protected allocations kept or increased (B5 → 2.0). |
| 3 | 2026-11-04 | **17.75 + 6.0 + 2.0 = 25.75 d** (+2.5 for SC-05…SC-11: SC-05 0.75, SC-07 0.5, SC-08 0.25, SC-09 0.25, SC-10 0.5, SC-11 0.25; SC-06 0). That is +1.15 above the indicative +1.35, because of the owner's scope decisions, shown in Plan v1.6 header. | **Recorded with the owner's approval of SC-05…SC-11.** All rev. 2 conditions carry over. |
| 2 | 2026-11-04 | **16.0 essential implementation + 5.25 testing & integration + 2.0 demo prep = 23.25 d** (+4.75 vs rev. 1, itemised in Plan v1.4 §2.6). P1 (3.25 d) outside the committed schedule. | **Approved by the owner**, with conditions: an estimate for one builder (not a deadline or contract); all P0 preserved; B1/B2/B4/B5/B6/C1 not reduced; O3 and X1–X4 rejected; O1/O2 optional only without loss of functionality |

The policy is unchanged across revisions:
- it is an estimate, not a contractual commitment;
- P0 comes first;
- P1 is dropped first;
- no source-of-truth requirement, named edge case, real AI loop or trust function is traded for time;
- increases are shown, never compressed elsewhere.

---

## Consistency confirmation
Each decision was checked against the four core documents after the edits. The **Where** tables above list the sections. The checks are recorded in `06_fix_log.md` §6.3:
- a grep for stale terms;
- a check that each DL ID appears in the brief, PRD, architecture and plan where it applies;
- a check that no text describes Needs Review values as included in formal award totals by default.

---

## Addendum — post-audit decision DL-19 (approved 2026-11-04, audit SC-04)
- **Decision:** the primary demo RFx is created live by the co-pilot from a buyer brief pack. A conformance check against the canonical RFx spec gates delivery of the prepared vendor responses. That one RFx flows continuously to the award.
- **FD-5 / DL-17 preserved:** the sandbox stays the place for free-form drafting, and the canonical spec and prepared dataset are never changed.
- **Where:**
  - Brief: DL-19 row;
  - PRD: §0.1, J1, J2, RFX-8…11, AI-17, §7, §11;
  - Architecture: §4, §5.1, §5.2, §12, ADR-15;
  - Plan: M1, M6, M10, §5.2;
  - Runbook: §2.

---

## Addendum — decisions DL-20…DL-22 (approved 2026-11-04, audit SC-05, SC-07, SC-08)
| ID | Decision | Where |
|---|---|---|
| **DL-20** | "Rest same as last year" is never resolved by assumption. Both readings (remaining **prices** / remaining **terms**) are kept as UNRESOLVED (REFERENCE_AMBIGUOUS) with historical candidates shown. A template clarification request is generated. Nothing is applied without an audited buyer confirmation. DL-8 limits still apply (same vendor and spec, never freight). | PRD §0.1, J9, EXT-9, NRM-8, REV-4, §5.8; Arch §8, §13; Plan T-EDGE-05c-A/B, T-CLAR-01; Runbook EDGE-05c |
| **DL-21** | The primary photo fixture is a genuine phone photograph of a printed rate card taken at an angle. The synthetic image is for additional tests only. AI-generated or edited images are never substituted. | `12_phone_photo_capture_kit.md`; PRD §11; Plan M1-final, T-EDGE-04 |
| **DL-22** | Dataset realism is validated by a procurement-literate human (`11_dataset_realism_review.md`). AI self-review is not external validation. | PRD §11; Plan M1-final |

SC-12 is resolved by FD-7 rev. 2 (C1). SC-13 is deferred by the owner, and the existing source-of-truth mapping is retained.

---

## Addendum — final-audit resolutions DL-23, DL-24 (approved 2026-11-04)
| ID | Decision | Where |
|---|---|---|
| **DL-23** | V5's quote email is exactly the assignment's one sentence and is never altered. V5's questionnaire answers and certificates arrive as a separate submission linked to V5's single Response. They evidence its Quality Pass and Commercial Fail. | PRD §0.1, J3, §7 `Response.submissions`, §11 V5; Arch §5.3; Plan M1 (fidelity lint), T-ARR-01; Runbook P5, EDGE-05 |
| **DL-24** | Food-grade compliance and FSC certification are separate Quality questions with per-line applicability. FSC is non-mandatory unless a line requires it (none does in this RFx). A question whose applicability isn't met is NOT_APPLICABLE: shown openly, excluded from roll-ups. Vendor eligibility stays Pass / Fail / Unverified. | PRD §0.1, ELG-1 + AC, §5.7, §7, §11; Arch §10; Plan M1, M2 |

Also resolved: the reference-weight count is **21** (16 RSC, 3 die-cut, 2 pads). REV-1–4 and J9 (P0) are owned by M5 (+ B5 for T-CLAR-01). The generic AI-drafted clarification is renamed **J9b** and stays P1. FD-7 rev. 3 (25.75 d) is unchanged.

---

## Addendum — Principal PM review adoptions DL-25…DL-32 (approved 2026-11-04)
| ID | Decision | Source |
|---|---|---|
| **DL-25** | Formal award comparison is **freight-aware**: landed cost where calculable; an UNKNOWN-freight candidate is compared on unit price as a lower bound; if it wins only that way, the line is FREIGHT_DEPENDENT with **break-even freight**. The readiness check needs an audited acknowledgement. The grid default stays unit price. | P0-1 |
| **DL-26** | **GST when the vendor is silent:** the RFx-defined tax basis is applied as a disclosed assumption (ASSUMED). No RFx basis, or an ambiguous statement → UNRESOLVED. | P0-2 |
| **DL-27** | **The item master is imported deterministically.** The AI proposes the column mapping (buyer confirms), finds gaps and asks about them, drafts the questionnaire and terms, and applies conversational edits. The AI never transcribes line values. | P0-3 |
| **DL-28** | **Decision sensitivity:** deterministic per-line analysis of whether an uncertain value could change the winner, with quantified impact. Drives queue order, the readiness check and the clarification pack. | P1-5 |
| **DL-29** | **Food-grade eligibility is line-level** (gates food-contact cells only). The FSC question is removed from the primary RFx; an FSC-required variant is a test fixture only. Amends DL-24. | P1-9 |
| **DL-30** | **V2 is a domestic supplier** quoting USD-linked prices invoiced in INR. It still quotes entirely in USD (DL-15 / EDGE-08 preserved). FX exposure is disclosed per 1% move. | P1-10 |
| **DL-31** | **Reference-weight conversions are ASSUMED**, and every per-kg line carries a billed-weight caveat per 1% weight variance. Amends DL-18. | P1-11 |
| **DL-32** | **A deterministic, buyer-approved clarification pack** per vendor covers the important vendor-resolvable items, sensitivity-ordered. No AI drafting, no reply parsing, no vendor platform. J9 is P0 through this pack; J9b (AI free-text drafts) stays P1. | P1-6 |

**Re-sequencing (P0-4):** vertical slice by day ~6.5; checkpoints at days 10, ~15 and ~20; testing and demo preparation durations preserved. **Deferred:** all other PM-review P1/P2 recommendations.
