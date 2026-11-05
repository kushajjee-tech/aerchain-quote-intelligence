# Pre-Build Review — Final Audit
**Reviewer role:** Independent Principal PM + Staff Architect · **Date:** 2026-11-04
**Inputs reviewed in full:** `assignment.pdf`, `01_product_brief.md` (v1.1), `02_PRD.md` (v1.0), `03_architecture.md` (v1.0), `04_implementation_plan.md` (v1.0)
**Scope:** genuine blockers and important improvements only. No rewrites, no code.

---

## Verdict

**Not ready to build yet. About half a day of spec fixes is needed first.** The overall design is strong: AI reads and code calculates, every value has evidence, the three eligibility states are well thought through, and the anti-hardcoding gates are good. But **6 blockers** are either contradictions between documents or rules that are left undefined. Each one would force the builder to guess mid-build, and on a ₹4 cr trust demo a guess is a silent error waiting to happen. All six can be fixed in the spec. None needs an architecture change.

| # | Audit criterion | Result | Findings |
|---|---|---|---|
| 1 | Every assignment requirement covered | ⚠️ Mostly | I3 (USD vendor fidelity), I10 (co-pilot depth for A-01) |
| 2 | PRD ↔ architecture consistency | ⚠️ | B2, B3, B6, I1, I6 |
| 3 | Acceptance criteria testable | ⚠️ | B3, B4, I2, I6, I8 |
| 4 | Stack practical | ✅ with fixes | I9 |
| 5 | Extraction pipeline feasible | ⚠️ | B4, B5, I9 |
| 6 | Unit/weight conversions never use invented inputs | ❌ | **B1**, B5, I5 |
| 7 | Eligibility consistent everywhere | ⚠️ | I1, I2, I3 |
| 8 | Calculations deterministic and reproducible | ❌ | **B2**, I6 |
| 9 | Ground truth unreachable by the app | ⚠️ | I7 |
| 10 | Plan covers all P0 | ⚠️ | B6, I10 |

---

## Blockers (fix in the spec before M0)

### B1 — "Same as last year" can fill in another vendor's price (breaks DL-1/DL-5 "never invent")
- **Where:** PRD NRM-8 AC ("if a baseline exists for the line, the value = baseline price"), PRD §5.8 and §7 `BaselinePrice.vendor_id (opt)`.
- **Problem:** the baseline is keyed by line, and vendor is optional. When V5 writes "rest same as last year", the rule as written uses *whatever* baseline row exists for that line, which may be last year's incumbent (a different vendor). That gives V5 a price it never quoted. It is exactly the fabrication §5.8 says is forbidden ("never fills in a missing quote unless the vendor explicitly referred to last year"). The vendor referred to *its own* last-year price, not to the line's price in general.
- **Required decision:** NRM-8 resolves only against a baseline row where `vendor_id == quoting vendor`. A row with no vendor, or a row for another vendor, gives `NEEDS_INFO` (reason: "baseline exists but not for this vendor"). Also decide how freight basis is handled when last year was delivered and this year is "freight extra". The dataset (PRD §11) must make sure V5 actually has its own last-year rows for some lines and not for others.

### B2 — Peer-dependent statuses depend on processing order, so results are not reproducible
- **Where:** Arch §9 (`UNIT_SUSPECT`, `OUTLIER` use the peer median), Arch §2/§3 (5 responses run concurrently), Arch §5.3 (recompute "for the affected line × vendor cells"), PRD NF-5 (100% determinism).
- **Problem:** validation runs per response inside each concurrent job. The peer median for a line depends on which other responses have finished at that moment. Two runs of `make demo-warm` can give different statuses. In the same way, correcting V4's cell changes the peer median for every other vendor on that line, but recompute only touches the edited cell. A related gap: nothing says what happens to a cell the buyer already accepted (`VERIFIED`) if a later peer recompute makes it look like an `OUTLIER`.
- **Required decision:** (a) peer and baseline checks run as a **line-level pass after ingestion**, over all responses ready at that point, and are recomputed for the **whole line** whenever any cell on it changes. (b) A human resolution is sticky. Recompute can add a new warning to it but never silently undoes an accept or override. (c) Put a test in M4: shuffle the order in which responses finish, and require identical statuses.

### B3 — Value status and inclusion are under-specified for derived and unresolved cells, so the scenario engine can't be golden-tested
- **Where:** PRD §6.1, §5.6, VAL-3 AC, AWD-1 `status_policy`, Arch §8 step 2.
- Three open questions:
  1. **Derived values.** Is a cell `ASSUMED` or `VERIFIED` when it is FX-converted, weight-converted using method constants (the ledger has `METHOD_CONSTANT`/`WEIGHT_SOURCE` types), or expanded from a group price? §6.1 lists FX under `ASSUMED`, but weight constants and group expansion are not mentioned. This decides how many cells are "assumed" in every caveat line (NLA-4 AC).
  2. **NEEDS_REVIEW with no number.** `UNIT_UNKNOWN` stops conversion (Arch §8 step 2), so there is no `unit_price_inr_ex_gst`. But §6.1 says `NEEDS_REVIEW` is "included with warning", and you can't include a null.
  3. **NEEDS_REVIEW with a suspect number.** VAL-3 AC says a `UNIT_SUSPECT` value "stays unresolved until the buyer acts". §6.1 and open question 2 say it is included with a warning. Including ₹480 as ₹480/box changes medians, averages and "most expensive" answers.
- **Required decision:** one rule table, *status × has numeric value → included / excluded / warning*, plus an explicit list of which transformations produce `ASSUMED`. Suggested: `UNIT_SUSPECT` and `UNIT_UNKNOWN` are treated like `NEEDS_INFO` (excluded and listed) until resolved. Only `NEEDS_REVIEW` for other reasons is "included with warning".

### B4 — The image "dual read" is not independent, and its evidence contract is ambiguous
- **Where:** PRD EXT-7 ("an independent vision read"), Arch §6.2 (one extraction call receives *both* the image and the OCR lines, and returns both the cited OCR value and `image_read_value`), PRD EXT-4 AC ("for text sources").
- **Problem:** a model that sees the OCR text when it reads the image will tend to repeat the OCR reading. That is the very "3 vs 8" error the dual read is supposed to catch (E-01, the first ugly edge the assignment names). On top of that, it isn't defined which reading goes into `value_as_stated`. If the model writes its vision reading there, EXT-4 evidence verification fails against the OCR text (`EVIDENCE_NOT_FOUND`) instead of reporting `READ_DISAGREEMENT`.
- **Required decision:** make the vision read a **separate call that receives no OCR text**, with values matched back to OCR lines by position or row. Define `value_as_stated` = the OCR-parsed reading and `image_read_value` = the vision reading, and send mismatches to `READ_DISAGREEMENT`, never `EVIDENCE_NOT_FOUND`. Budget the extra call in Arch §16.

### B5 — The flagship email edge (E-08) contradicts the extraction rules
- **Where:** brief E-08 / PRD E-08 (expects the chain "₹38/kg × 0.42 kg = ₹15.96/box"), PRD EXT-5 and §5.1 (no unit → `UNKNOWN`; AI and dictionary disagree → `UNKNOWN`), EXT-8 AC ("applies to every RFx line with ply=3").
- Two conflicts:
  1. The assignment's wording is "₹42/kg for the 5-ply, **38** for the 3-ply". The "38" has no unit, so under EXT-5 it is `UNKNOWN`, goes to review, and the chain the brief promises never appears. Either inheriting a unit from the same sentence is allowed (with evidence and a disclosed status), or the expected demo behaviour is review. The docs say both.
  2. "Every line with ply=3" covers die-cut, partition and pad lines if they are 3-ply. §5.2 only defines a weight formula for RSC. It says die-cut needs a blank size, but gives no formula for it (see I5). Partitions and pads are not covered at all. So group expansion hits lines whose conversion is undefined.
- **Required decision:** write a rule for elliptical units (suggested: inherit from the same sentence or clause, cite both evidence spans, set status `ASSUMED` with the reason "unit inherited from context"). Also state the item types that group expansion covers, and the expected status for each non-RSC item type.

### B6 — Priority contradictions leave P0 paths depending on P1 features
- **Where:** PRD §12, §11, NF-8, AWD-1 vs AWD-6.
  - **Tiered pricing:** NRM-10 is P1, but V1 is *planted* with slabs (PRD §11, plan M1), and slab selection is step 1 of the P0 normalisation chain (§5.5). If P1 is cut, V1 can't be normalised.
  - **Tooling:** NRM-9 is P1, but V1 has a tooling row. Without at least "detect and keep separately", that row can be matched as a line item or folded into a unit price.
  - **Live re-run:** NF-8 and D10 (P0 demo resilience) need "re-run extraction live", but EXT-11 is P1.
  - **Vendor cap:** AWD-1 (P0) includes `vendor share cap`, AWD-6 marks it P1, and M7 builds it as a gate. Walkthrough Q9 depends on it.
- **Required decision:** promote slab selection, tooling detection and separation, and a basic re-run to P0, or remove them from the P0 dataset. Pick one priority for the cap.

---

## Important improvements

### I1 — The brief's body is out of date compared with the PRD (status count and more)
The v1.1 note in brief §7.2 says the PRD moves from six states to seven, but the brief's body still says six:
- §7.2 table: 6 states, including 🔴 *Non-compliant* as a value state. The PRD makes it an independent `ALTERNATE` flag.
- F-CMP-2: lists the same six.
- §10 A-17: "**Six** cell states".

The brief's body also contradicts the PRD in other places:
| Brief | PRD |
|---|---|
| E-16 expired or wrong-entity cert → "flag on vendor panel" | §5.7 → **Unverified** |
| F-NRM-6 any spec difference → non-compliant | MAT-3 tolerance (GSM −5%, dims ±2 mm) |
| §7.4 plausibility vs "box weight × paper cost" | No paper-cost data. Check dropped. |
| F-NRM-4 freight P1; F-AWD-5 audit P1 | NRM-5 P0; AUD-1 P0 (DL-2/DL-7) |
| F-AWD-1 cap P0 | AWD-6 P1 |

**Fix:** add a single line at the top of the brief making the PRD authoritative wherever they disagree, and mark §7.2, F-CMP-2, E-16, F-NRM-6 and §10 A-17 as superseded. The builder and the panel will read the brief first.

### I2 — Eligibility: what "quality questionnaire" means, and Unverified ≠ Fail at runtime
- **Scope:** the VP asks about the *quality* questionnaire. PRD §11's questionnaire mixes quality items (ISO, BCT/ECT, FSC) with commercial ones (GST registration, payment terms acceptance, lead time). ELG-2 rolls up *every mandatory question*. If V5's "No" is on payment terms, the analyst would say V5 "failed the quality questionnaire", which is not true. `Question` has no category or section field. **Fix:** add `Question.section` and decide whether "cleared the quality questionnaire" means the quality section or all mandatory questions. State it as the analyst's stated interpretation (NLA-6).
- **Walkthrough wording:** brief §8.2 Q4, "on what grounds did the **others fail**?", asks the model to break T7 in the recorded demo. Keep it as a trap question, but the expected answer must correct the premise.
- **Enforcement:** ELG AC says Unverified must never be called "Fail" in analyst text, but the only enforcement is the eval (Arch §10). An off-script live question can still produce "V4 failed". **Fix:** add a runtime lint next to the grounding check. Flag fail/failed/rejected/disqualified within N tokens of a vendor whose state ≠ FAIL, and regenerate once.

### I3 — The demo dataset makes the headline VP answer trivial and leaves out the hardest edges
Under the planned eligibility states (V1 Pass, V2 Pass, V3 Unverified, V4 Unverified, V5 Fail), strict mode leaves **only V1 and V2**. So:
- the VP's split question is a two-vendor comparison;
- "lines with no eligible quote" is never exercised, since V1 probably quotes all 30;
- the photo vendor, the 27/30 vendor and the USD line are all absent from the headline answer.

Separately, the assignment says "**the one who quoted in USD**" (a vendor), but the plan has one USD line, at the vendor that fails eligibility. **Fix:** give at least 3 vendors Pass, and make one Pass vendor partial so that uncovered lines appear. Consider having a whole vendor quote in USD, so that FX sensitivity can actually change a ranking (plan M10 drill "FX flips a ranking").

### I4 — Savings comparators are undefined, and they are the headline numbers
AWD-2 and NLA-4 report "savings vs best single vendor" and "vs baseline", with no rule for:
- **Best single vendor when coverage differs.** V3 covers 27/30. Is it compared on common lines only, only among full-coverage vendors, or by total with the gaps listed?
- **Baseline gaps.** The baseline covers about 25/30 lines (deliberately). Savings must be computed over lines that have a baseline and say "computed on N of M lines, ₹X of spend".

**Fix:** define both rules in AWD-2, and add them to the test oracle (`tests/oracle.py`) so the oracle and the engine can't disagree on meaning.

### I5 — The weight method has gaps that allow quiet inference
- **Flute ↔ medium mapping:** `RfxLine.layers` has role and GSM, but says nothing about which medium gets which flute. For a 5-ply "BC", take-up B 1.35 vs C 1.45 depends on the order. Define it: mediums in layer order map to the characters of `flute_profile` in order. Also validate `count(mediums) == len(flute_profile)` and that ply = liners + mediums, otherwise the construction is not `construction_complete`.
- **Die-cut with a blank size:** §5.2 rule 2 allows only RSC, while the same section and RFX-3 say a die-cut with an RFx blank size is convertible. Give the formula (blank area × grammage) or say it is not convertible.
- **Partitions and pads:** say outright that they need a vendor weight (or give a formula), so they never become convertible by accident.
- **Internal vs external dimensions:** the formula uses internal dimensions. Disclose in the trace that this slightly understates weight.

### I6 — Where determinism starts is not stated
- AI extraction is not repeatable (and Opus 5.5 doesn't accept sampling parameters, so it can't be pinned with `temperature=0`). NF-5 and brief §7.3 ("same question … same numbers") overclaim. **Write it down:** everything from *stored* raw facts onward is deterministic. Analyst answers are deterministic *for the same tool calls*, not for the same question.
- **Re-running extraction** (the NF-8 live button, DL-4) creates a new run. It isn't specified what happens to review decisions, overrides, saved scenarios and *acknowledged* award memos tied to the old values. Define carry-forward by (vendor, line, value match), or invalidate and mark stale.
- **FX change:** PRD NRM-4 AC says scenarios are "recomputed", while Arch §5.3 says they are marked "stale". Pick one.
- **Rounding:** no money precision or rounding policy is given. Use Decimal and say at which step rounding happens (per box vs annual totals). The grounding check and the "byte-identical" scenario test both depend on it.

### I7 — Ground-truth isolation is a convention, not a control
- The PRD (§11) says the answer key is "outside the app's readable paths". The architecture puts it at `data/answer_key/` inside the repo, which the app process can read, guarded only by a grep test.
- `data/generator/` holds the **truth spec YAML** (all the true values), is not covered by any exclusion, and sits next to `data/seed/` and `data/inbox/`, which the app does read.

**Fix:** move the answer key and the generator truth spec out of the app's data root (a sibling directory or separate repo). Configure the app with an explicit `DATA_ROOT` allowlist and a runtime guard that refuses to open paths outside it. Keep the static test as a second layer. Also have the M10 perturbation run use a seed the builder hasn't seen during development.

### I8 — "Silent error = 0" has two blind spots
- **Unchecked auto-VERIFIED:** the magnitude and outlier checks need ≥ 3 peers or a baseline. On lines with no baseline (about 5 of them) and few peers (missing or not-convertible cells), a digital value skips plausibility checks entirely and can still auto-promote to `VERIFIED`. **Fix:** when no plausibility reference exists, cap the status at `EXTRACTED` and record "plausibility unchecked".
- **Analyst correctness:** the grounding check proves that numbers *came from* tool results, not that the SQL was *right*. The analyst eval target of ≥ 90% allows 1 in 10 wrong answers to be shown with full confidence. **Fix:** add an "analyst silent error" metric (wrong number, no interpretation stated, no caveat) with a target of 0 on the walkthrough set, and steer award-type questions to `run_scenario` instead of free SQL.

### I9 — Stack practicality: small but real gaps
API usage was checked against current Claude API guidance. `claude-opus-5-5` with adaptive thinking, `output_config.effort`, structured outputs via `messages.parse`/`output_config.format`, citations being incompatible with structured outputs, forced `tool_choice` returning a 400, `strict: true` tools, and refusal handling with server-side fallback are **all correct**. Items to fix:
- **Opus 5.5 default effort is `medium`.** The doc sets effort per route explicitly. Keep that explicit everywhere.
- **Preserved thinking:** the analyst loop and the "regenerate once with feedback" step (Arch §11.5) must *append* to the conversation and never edit earlier turns, or thinking blocks are invalidated or rejected.
- **python-docx** doesn't expose footnotes and doesn't iterate paragraphs and tables in document order by default. Arch §6.1 claims both. Plan for direct XML handling (body children + `footnotes.xml`).
- **`.xls`** (EXT-1) isn't readable by openpyxl and needs `xlrd`. **`.heic`** needs `pillow-heif`.
- **Tesseract** is a system dependency, which conflicts with NF-7 "one command". Ship a setup check or a container.
- **Unit dictionary cross-check:** a string the dictionary doesn't recognise ("per nos.", "/pc", "per hundred") must count as *no opinion*, not *disagreement*. Otherwise §5.1 floods the review queue.

### I10 — Plan coverage and effort balance
- **A-01 is under-resourced.** "Talks an RFx into existence" is the assignment's first sentence, but M6 gives one day to the co-pilot *and* send, inbox and upload. Generating 30 lines with per-layer GSM as JSON-Patch is non-trivial. Give the co-pilot its own eval and at least 1 day.
- **Demo coherence:** if the panel drafts a new RFx live, the prepared inbox answers the *seeded* RFx. Define this in the runbook (for example: live drafting edits the seeded draft as a new version, or a separate sandbox RFx that receives uploads only).
- **P0 traceability is by assignment requirement, not by FR.** Some P0 FRs have no clear milestone owner: DIS-2 status board, AWD-5 memo listing of alternates, EXP-3 analyst export (M9 mentions it only briefly), CMP-6 baseline Δ%. Add an FR → milestone column so §7 "all P0 FRs meet AC" can be checked.
- **Generator scope:** M1 at 1.5 d includes a generator that renders *different layouts* across xlsx, pdf, docx and the photo for the perturbation test. That is likely 2–3 d on its own. Either reduce the scope of the perturbation (values, names and row order, plus one layout change per format) or re-budget it.

---

## Verified as sound (no action)
- The AI/code split (PRD §8.1) and the fixed pipeline with one bounded analyst loop (§8.3) are the right call for the trust bar.
- DL-2 freight handling is consistent across the brief, PRD §5.4, Arch §8 and the M2 tests, including per-kg freight without weight → UNKNOWN.
- DL-3 roll-up, strict and inclusive modes, the deterministic tie-break, and "uncovered, never silently awarded" are consistent and testable.
- Evidence verification (Arch §7.3), the SQL view sandbox, caveats computed by code, and the independent test oracle are strong anti-fabrication controls.
- The status precedence order (§5.6) is consistent with the §6.1 table, and `ALTERNATE` is handled consistently as a flag in the PRD, architecture and plan.

---

## Suggested fix order (≈ ½ day, docs only)
1. B1, B5, I5: conversion and reference rules (PRD §5.2, NRM-8, EXT-5/8).
2. B3: status × inclusion table (PRD §6.1).
3. B2, I6: determinism boundary and line-level recompute (PRD NF-5, Arch §5.3/§9).
4. B4: separate vision call (PRD EXT-7, Arch §6.2).
5. B6, I10: re-tier priorities and add an FR → milestone column (PRD §12, plan §5).
6. I2, I3, I4: questionnaire sections, dataset eligibility mix, savings rules (PRD §7, §11, AWD-2).
7. I1, I7: brief supersession header, ground-truth relocation.
