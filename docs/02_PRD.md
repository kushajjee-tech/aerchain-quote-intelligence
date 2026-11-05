# PRD — Quote Intelligence for Corrugated Packaging RFx
**Status:** v1.5 · Principal PM review changes applied (P0-1…4; P1-5, 6, 9, 10, 11) · **Inputs:** `docs/assignment.pdf`, `docs/01_product_brief.md` (v1.3), `docs/05_prebuild_review.md`, `docs/08_final_product_decisions.md`
**Next docs:** `docs/03_architecture.md`, `docs/04_implementation_plan.md`, `docs/10_demo_runbook.md` · **Fix log:** `docs/06_fix_log.md` · **Canonical requirements:** `docs/00_source_of_truth.md` (SOT IDs)

> **Authority:** this PRD is the source of truth. Where the brief and this PRD disagree, this PRD wins.

---

## 0. Conventions

| Tag | Meaning |
|---|---|
| **[A]** | Required by the assignment (IDs `A-01`…`A-25` from brief §2). |
| **[A-i]** | Implied by the assignment (e.g. the "ugly edges" list). |
| **[R]** | Our recommendation / product decision. It could reasonably be argued the other way. |
| **[DL-n]** | A locked decision. Non-negotiable for the build. |
| **(Bn / In)** | Marks a requirement changed to resolve pre-build review finding Bn/In. Details are in `06_fix_log.md`. |

Priorities:
- **P0**: needed for the demo story and the trust bar. **The demo dataset and demo script may depend only on P0 capabilities (DL-13).**
- **P1**: strengthens the demo, but no dataset or demo dependency is allowed.
- **P2**: if time allows.

### 0.1 Locked decisions

| ID | Decision | Source |
|---|---|---|
| DL-1 | ₹/kg → ₹/box only when the inputs are sufficient **and the item type is supported** (§5.2). Missing inputs are never invented. *(Amended by DL-18: weight-source hierarchy.)* | Brief v1.1 |
| DL-2 | Normalised ex-GST unit price is kept separate from freight. Landed cost is calculated only when freight is known or comes from a disclosed estimate the buyer has accepted. | Brief v1.1 |
| DL-3 | Eligibility has three states: **Pass / Fail / Unverified**. Unverified is excluded under strict eligibility and is **never** described as Fail. | Brief v1.1 |
| DL-4 | Uploading new vendor files is supported. An unseen-file upload is optional in the main demo. | Brief v1.1 |
| DL-5 | Last year's prices are kept as a reference dataset. | Brief v1.1 |
| DL-6 | Alternate specs are excluded from like-for-like awards by default. | Brief v1.1 |
| DL-7 | Buyer overrides are allowed, and each one writes an audit record. | Brief v1.1 |
| **DL-8** | **"Same as last year" resolves only against the *same vendor's* baseline row for the *same line with a matching specification*.** Another vendor's historical price is never used. **Historical freight terms are never carried forward.** Freight comes only from this year's response; if it is not stated, it is UNKNOWN. | Review B1, FD-4 |
| **DL-9** | **Processing has two phases.** Per-document extraction and per-cell normalisation come first. Cross-vendor checks (peer price, outlier, unit magnitude) run only after all responses in the set are processed. Any change triggers a **global recompute** of derived values and statuses. Human resolutions are kept across recomputes. | Review B2 |
| **DL-10** | **One canonical value-status model (§6).** Unresolved values never enter calculations. | Review B3, I1 |
| **DL-11** | **Photo reads are independent.** OCR extraction and visual AI extraction run separately. The vision call never sees OCR output. Any disagreement, or a value only one read found, needs human review. | Review B4 |
| **DL-12** | **A unit inferred from context (e.g. the "38" in "₹42/kg for the 5-ply, 38 for the 3-ply") is recorded as an inference, with evidence, and has status ASSUMED.** Weight conversion applies only to supported item types with sufficient inputs. *(Amended by DL-18.)* | Review B5, I5 |
| **DL-13** | **The demo dataset and demo script depend only on P0 capabilities that are implemented and tested.** Optional (P1/P2) features stay optional. | Review B6 |
| **DL-14** | **Only the Quality section decides "cleared the quality questionnaire".** Commercial questions are evaluated and shown separately. | FD-1 |
| **DL-15** | **V2 quotes its entire response in USD.** *(Framed by DL-30: a domestic supplier with USD-linked prices invoiced in INR; FX exposure disclosed.)* Original values are preserved. Conversion to INR uses a stated, editable FX rate and date. | FD-2 |
| **DL-16** | **`NEEDS_REVIEW` values are excluded from formal award calculations by default.** An explicit buyer override is allowed per scenario, with a warning and an audit record. Exploratory analysis may include them on request, labelled with caveats. | FD-3 |
| **DL-17** | **Live co-pilot drafting uses a separate sandbox RFx.** The seeded RFx and the prepared five-vendor dataset are never changed by it. *(Under DL-19, "the seeded RFx" is the canonical RFx spec. The primary RFx is drafted live and conformance-checked against it.)* | FD-5 |
| **DL-18** | **Engineering constants are configurable, versioned, and labelled UNVALIDATED until validated.** ₹/kg → ₹/box uses the weight-source hierarchy (§5.2): documented SKU reference weight → vendor-stated weight → estimate from constants (`NEEDS_REVIEW`, never in a formal award without buyer review) → `NOT_CONVERTIBLE` / `UNRESOLVED`. Amends DL-1 and DL-12. *(Amended by DL-31: reference-weight conversions are ASSUMED.)* | FD-6 |
| **DL-19** | **The primary demo RFx is created live by the co-pilot**, from a buyer brief pack (item master, quality checklist, commercial policy) plus the buyer's conversational answers. Before sending, it must pass a deterministic **conformance check** against the **canonical RFx specification** that the prepared vendor responses were authored against. That one RFx then flows through responses, extraction, comparison, analysis and award. The canonical spec is never changed. It also serves as the visible "seeded fallback". The sandbox (DL-17) is unchanged and remains the place for free-form drafting. | Audit SC-04 (SOT REQ-03, FN-01) |
| **DL-20** | **"Rest same as last year" is ambiguous and is never resolved by assumption.** Both readings are kept: (A) the remaining **line-item prices**; (B) the remaining **commercial terms**. All affected information is `UNRESOLVED (REFERENCE_AMBIGUOUS)`, the historical candidates are shown, and a **clarification request** is generated. A historical price or term is applied **only after buyer-recorded confirmation** (audited), and still under DL-8 (same vendor, same spec, never freight). | Audit SC-05 (SOT EDGE-05c) |
| **DL-21** | **The primary photo fixture is a genuine phone photograph** of a printed rate card taken at an angle (`docs/12_phone_photo_capture_kit.md`). The synthetic image is for additional tests only. An AI-generated or AI-edited image never substitutes for it. | Audit SC-08 (SOT EDGE-04/06) |
| **DL-22** | **Dataset realism is validated by a procurement-literate human** using `docs/11_dataset_realism_review.md`. AI self-review is never counted as external validation. | Audit SC-07 (SOT REQ-05) |
| **DL-23** | **V5's email body is exactly the assignment's one sentence and is never altered.** V5's questionnaire answers and certificates arrive as a **separate submission** (a second message from V5 for the same RFx), linked to V5's single Response. This submission is the evidence for V5's Quality Pass and Commercial Fail. | Final audit #1 (SOT EDGE-05) |
| **DL-24** | **Food-grade compliance and FSC certification are separate Quality questions.** Food-grade applies only where a line is `food_contact`. FSC is **non-mandatory unless a line has `requires_fsc`**. Where a question's applicability condition isn't met, the question-level outcome is **NOT_APPLICABLE**: excluded from roll-ups, shown openly (e.g. "FSC certificate: not provided — not required for this RFx"). Vendor eligibility stays Pass / Fail / Unverified (DL-3). *(Amended by DL-29: line-level gating; FSC question removed from the primary RFx.)* | Final audit #2 |
| **DL-25** | **Freight-basis-aware award comparison (P0-1).** Formal award scenarios default to `basis = freight_aware`. Each line is decided on landed cost where it is calculable. A candidate with UNKNOWN freight is compared on its unit price as a lower bound. If it wins only on that lower bound, the line is `FREIGHT_DEPENDENT`, with a **break-even freight** (₹/box) at which it would stop winning. The award readiness check lists every freight-dependent line and needs an audited acknowledgement. The grid default stays unit price (DL-2). | PM review P0-1 |
| **DL-26** | **GST when the vendor is silent (P0-2).** If a response says nothing about GST, the RFx-defined tax basis (`response_basis.gst_treatment`) is applied as a disclosed assumption: `ASSUMED (GST_PER_RFX_BASIS)`. If the RFx defines no basis, or the vendor's statement is ambiguous, the value is `UNRESOLVED (GST_UNCLEAR)`. Nothing is assumed silently. | PM review P0-2 |
| **DL-27** | **Deterministic item-master import (P0-3).** The 30 lines are imported deterministically from the item-master file. The AI proposes the **column mapping** (the buyer confirms), identifies **gaps** and asks about them, drafts the questionnaire and terms from the checklist and policy, and applies conversational edits. The AI never transcribes line values. | PM review P0-3 |
| **DL-28** | **Decision sensitivity (P1-5).** For every line, deterministic analysis shows whether an uncertain value (unresolved candidate, excluded needs-review value, assumed FX or weight, unknown freight) could change the winner. Impact is quantified where possible: annual ₹ delta, flip margin %, or break-even freight. | PM review P1-5 |
| **DL-29** | **Food-grade eligibility is line-level; FSC removed (P1-9).** Food-grade compliance gates a vendor only on `food_contact` lines. It doesn't affect the vendor-level Quality result. The FSC question is removed from the primary RFx; an FSC-required variant exists only as a test fixture. Amends DL-24. | PM review P1-9 |
| **DL-30** | **V2 is a domestic supplier with USD-linked pricing invoiced in INR (P1-10).** It still quotes its entire response in USD (DL-15, SOT EDGE-08). FX exposure is disclosed and quantified (₹ impact per 1% USD/INR move on V2-awarded spend). | PM review P1-10 |
| **DL-31** | **Reference-weight conversions are ASSUMED; billed-weight risk is disclosed (P1-11).** A ₹/kg → ₹/box conversion using a documented reference weight is `ASSUMED (REFERENCE_WEIGHT)`. Every per-kg-priced line carries a billed-weight caveat (₹ impact per 1% weight variance). Amends DL-18. | PM review P1-11 |
| **DL-32** | **Deterministic clarification pack (P1-6).** One buyer-approved, template-generated pack per vendor covering the important vendor-resolvable review items, ordered by decision sensitivity. No AI drafting, no reply parsing; the buyer records resolutions. Extends the DL-20 request. Not a vendor-response platform. | PM review P1-6 |

---

## 1. Summary

A category buyer creates a corrugated-packaging RFx by talking to a co-pilot and sends it to 5 vendors. Responses come back in any format: Excel, PDF, Word, a phone photo, or a plain email. The system reads every response with real AI and normalises the results into one comparison: same lines, same unit, same currency. It shows uncertainty rather than hiding it. Questions in plain language get answers built on deterministic calculations, ending in an award recommendation that can be audited. **[A]**

### 1.1 Goals
| # | Goal | Tag |
|---|---|---|
| G1 | No manual retyping: every vendor response lands in the comparison automatically | [A] |
| G2 | A comparison trustworthy enough for a ₹4 crore decision | [A] |
| G3 | Ad-hoc analytical questions answered in minutes, including compound what-ifs | [A] |
| G4 | A defensible award decision, traceable to sources | [A] |
| G5 | Uncertainty shown openly. Never silently wrong. | [A] / [R] |

### 1.2 Success metrics (measured on the demo dataset **and** on one perturbed variant) **[R]**
| Metric | Target |
|---|---|
| **Extraction silent error rate.** A wrong value shown as `VERIFIED`, `EXTRACTED` or `ASSUMED`. | **0** |
| **Analyst silent error rate.** A wrong number shown with no stated interpretation and no caveat that explains the difference. (I8) | **0** on the walkthrough set |
| Price-field accuracy after normalisation, on lines that can be normalised | ≥ 95% |
| Line-to-RFx matching accuracy | ≥ 95% |
| Planted edge cases handled correctly or sent to review | 100% |
| Analyst eval: correct numeric answers (walkthrough + off-script) | ≥ 90% |
| Analyst eval: document-fact and questionnaire-answer questions correct and source-linked (NLA-11/12) | ≥ 90% correct, 100% source-linked |
| Analyst: missing facts invented (NLA-13) | 0 |
| Live co-pilot primary RFx conforms to the canonical spec (RFX-10) | ≥ 4 of 5 rehearsal runs |
| Historical price or term applied without a confirmation record (DL-20) | 0 |
| Awaiting vendors shown as zero, MISSING or Unverified (SC-10) | 0 |
| Numbers in analyst answers that trace to tool results | 100% |
| Unverified vendors described as failed (UI, exports, memo, analyst) | 0 |
| Buyer time from all responses received to a reviewed comparison | < 30 min (baseline ~3 days) |

### 1.3 Non-goals
See §13.

---

## 2. Personas

| Persona | Role | Primary needs | Uses |
|---|---|---|---|
| **Priya, Category Buyer (primary)** | Owns the RFx from draft to award recommendation | Draft fast, no retyping, see exactly what's uncertain, fix it quickly, defend the numbers | Co-pilot, review queue, comparison, analyst, award |
| **Rahul, VP Procurement (approver)** | Asks what-ifs, approves the award | Fast answers he can trust, clear exclusions and assumptions, a one-page memo | Analyst, award memo |
| **Vendor sales rep (external)** | Responds to the RFx | Reply in their own format, receive clear clarification questions | Email only |
| **Quality engineer (consulted)** | Defines spec and quality pass rules | Spec deviations and unproven claims are visible | The questionnaire's **Quality** section, via the co-pilot |

The prototype has a single user role and no login.

---

## 3. User journeys

### J1 — Draft the RFx with the co-pilot **[A]** (P0)
1. Priya describes the need in plain language and attaches her **buyer brief pack**: item master (SKUs, construction, annual quantities, reference weights with sources), the quality engineer's checklist, and the commercial policy. **The item master is imported deterministically (DL-27):** the co-pilot proposes the column mapping (e.g. "'GSM-L1' → top liner GSM"), Priya confirms it, and the 30 lines are created exactly from the file rows. The co-pilot then identifies gaps (missing construction fields, delivery location, internal vs external dimensions, GST basis) and asks about them, and drafts the questionnaire and terms from the checklist and policy.
2. The co-pilot proposes a structured draft:
   - scope;
   - line items with full construction;
   - a questionnaire split into **Quality** and **Commercial** sections, with pass rules (I2);
   - terms, including the response basis.
3. Priya edits fields directly or through chat. Each chat change is shown as a diff she accepts or rejects. She then approves, which locks a version.
4. **Conformance (DL-19):** before approval, Priya runs the conformance check against the canonical RFx specification. Any differences are listed, and she fixes them by chat or edit.
5. **Demo arrangement (DL-17, DL-19):** the **primary RFx is the one drafted live in steps 1–4** (`origin = COPILOT_LIVE`). It receives the prepared five-vendor responses and goes through J2–J7 without interruption. Free-form drafting by the panel happens on the separate **sandbox RFx**, which can receive uploads (J8) but has no prepared inbox. If live drafting is impossible (e.g. API outage), the canonical spec is loaded as a visibly labelled **seeded fallback** (`origin = SEEDED_FALLBACK`). The canonical spec and the prepared responses are never changed.

### J2 — Send to vendors **[A]** (P0)
Priya selects the vendors and sends. For the primary RFx, sending requires a passing conformance check (RFX-10). One email per vendor goes into a **simulated outbox**. A status board shows each vendor's progress (DIS-2).

### J3 — Responses arrive and are read **[A]** (P0)
The prepared .eml responses are delivered from the simulated inbox, or files are uploaded (J8).
- **Phase A, per response:** parse → extract → verify evidence → match lines → normalise each cell → run per-cell checks.
- **Phase B, once all responses in the set are processed (DL-9):** cross-vendor checks run, then statuses, eligibility and review items are computed for the whole comparison.

**Several messages from the same vendor for the same RFx** (e.g. V5's quote email and its separate questionnaire submission, DL-23) are linked into that vendor's **single Response** as separate submissions. Each document is extracted, and a later submission triggers the global recompute. Two submissions pricing the same line → PRICE_CONFLICT (E-11). This is the same mechanism as J8 "upload to an existing vendor".

Until Phase B has run, the comparison is labelled **"Provisional — N responses still processing"**, and the analyst and award features are disabled.

**Vendors whose responses haven't arrived (SC-10, SOT EX-02)** show **"Awaiting response"**. They don't block Phase B. They have no cells, are never treated as a zero price or as MISSING lines, and are excluded from every calculation with the exclusion "Awaiting response: V_". When a late response arrives, it goes through Phase A and the global recompute (VAL-5). The comparison is valid at every arrival state.

### J4 — Review exceptions **[A]** (P0)
Items are sorted by money at risk. Each shows its source (image crop, cell or sentence), the reason it was flagged and a suggested resolution. Actions: **Accept / Correct / Mark missing / Override**, plus Ask vendor (P1). Every action is audited (DL-7), and each one triggers a global recompute (DL-9).

### J5 — Compare **[A]** (P0)
A grid of lines × vendors shows the ex-GST ₹/box price. Toggles switch to Landed or As-quoted values. Each cell has a status badge and a provenance drawer. Vendor panels show Quality and Commercial eligibility separately.

### J6 — Ask questions **[A]** (P0)
The VP asks the split question. The answer is a deterministic scenario. It shows:
- the interpretation used ("quality questionnaire = Quality section, strict; values needing review excluded") (DL-14, DL-16);
- totals;
- savings, defined as in §5.9;
- exclusions, with Failed and Unverified vendors listed separately;
- uncovered lines;
- caveats.

### J7 — Decide and export **[A]** (P0)
Priya saves a scenario on the Award screen. Formal award calculations exclude `NEEDS_REVIEW` values by default (DL-16). She resolves the review items, or explicitly overrides the exclusion for the scenario (warning + audit). She then runs the readiness check, acknowledges any remaining weak inputs (audited), and exports the memo and the xlsx.

### J8 — Upload a new vendor file **[DL-4]** (P0 capability, optional in the demo)
The upload goes through the same Phase A pipeline, followed by the Phase B global recompute.

### J9 — Ask a vendor to clarify
- **P0, clarification pack (DL-32):** one deterministic, template-generated pack per vendor covering its important vendor-resolvable items: unit unknown/suspect, read disagreements, GST unclear, unknown freight on freight-dependent or decision-sensitive lines, price conflicts, ambiguous slabs, missing evidence for Unverified quality questions, the ambiguous reference (below), and lines left uncovered by the scenario that the vendor didn't quote. Items are ordered by decision sensitivity (DL-28). The buyer reviews, edits and approves it into the outbox, then records resolutions manually (no reply parsing).
- **Reference section of the pack (DL-20):** for an ambiguous reference ("rest same as last year"), the system generates a **template-based clarification request**. It lists both readings, the affected lines with their historical candidate prices, and the affected terms with their historical candidate terms. The buyer reviews and edits it, then places it in the simulated outbox. The buyer then records the vendor's answer as a confirmation (audited). There is no automatic reply parsing.
- **J9b, P1 (deferred):** AI-drafted free-text clarification emails.

---

## 4. Functional requirements and acceptance criteria

The FR → milestone owner is listed in the implementation plan §5 (I10).

### 4.1 RFx co-pilot (`RFX`)

| ID | Requirement | Tag | Pri |
|---|---|---|---|
| RFX-1 | Conversational creation of scope, line items, questionnaire and terms | [A] | P0 |
| RFX-2 | Ask clarifying questions when construction or terms are missing | [R] | P0 |
| RFX-3 | Line schema specific to corrugated, including `item_type`, per-layer construction and an optional **documented reference unit weight with its source document** (§7, DL-18) | [R] | P0 |
| RFX-4 | Typed questionnaire. Each question has a **section ∈ {QUALITY, COMMERCIAL}**, a mandatory flag, a pass rule and an evidence requirement. (I2) | [R] | P0 |
| RFX-5 | Response basis: unit, currency, freight basis, GST treatment, validity | [R] | P0 |
| RFX-6 | Every field editable. Chat edits shown as diffs. Nothing is sent without explicit approval. | [R] | P0 |
| RFX-7 | Optional Excel response template | [R] | P1 |
| RFX-8 | Canonical RFx specification (seed; the basis of the prepared responses; also the labelled seeded fallback). A separate sandbox RFx for free-form drafting. (I10, DL-17, DL-19) | [R] | P0 |
| RFX-9 | **Brief-pack attachments and deterministic item-master import (DL-27):** attached files are parsed into evidence units. For the item master, the AI proposes a column → `RfxLine` field mapping with confidence. The buyer confirms or edits it. Rows are imported **deterministically** (values copied exactly, units normalised by rule). The AI then lists gaps and asks about them. Questionnaire and terms patches cite checklist and policy sentences. Conversational edits stay as patches. (SC-04, P0-3) | [R] | P0 |
| RFX-10 | **Conformance check (DL-19):** deterministic comparison of a drafted RFx with the canonical spec on: SKU set; per-SKU construction, dimensions, annual quantity and reference weight; questionnaire `requirement_key` set, sections and pass rules; response basis. Output: Conforms, or a list of differences. Only a conforming RFx can receive the prepared responses. | [R] | P0 |
| RFX-11 | **RFx provenance:** each RFx stores `origin` (COPILOT_LIVE / SEEDED_FALLBACK / SANDBOX), its co-pilot transcript, accepted patches and conformance result. All are visible in the RFx header. | [R] | P0 |

**Acceptance criteria**
- **RFX-1/2:** given a one-paragraph need, the co-pilot produces a draft with line items, a questionnaire covering both sections, and terms. It asks about missing construction before marking a line complete. Each line shows `Complete` or `Incomplete: <fields>`.
- **RFX-3, construction completeness (I5):**
  - An RSC line is `construction_complete` only if all of these hold: internal L/W/H, ply ∈ {3,5,7}, `flute_profile` length = (ply−1)/2, layer count = ply, count of mediums = length of `flute_profile`, and every layer has a GSM.
  - A DIE_CUT or PAD line also needs `blank_size_mm` before its weight can be *estimated* (it can always convert with a reference or vendor weight, DL-18).
  - PARTITION lines are never weight-*estimated* (they convert only with a documented reference weight or a vendor-stated weight).
  - `reference_unit_weight_g` is optional, but if present it must carry `reference_weight_source` (document name or item-master id). A line without one shows "No reference weight — ₹/kg quotes will need a vendor weight or an estimate".
- **RFX-4:** every question has a `section`, `answer_type` ∈ {yes_no, number, text, date, document}, `mandatory`, an optional `pass_rule`, and `evidence_required` (+ document type). A question without a section can't be approved.
- **RFX-6:** a rejected patch changes nothing. An accepted patch is recorded as a new draft version.
- **RFX-8 (DL-17, DL-19):** the canonical spec loads as a seeded fallback in < 2 s, labelled `SEEDED_FALLBACK`. Co-pilot edits to the sandbox or to the primary RFx never change the canonical spec or the prepared five-vendor dataset (snapshot hash unchanged).
- **RFX-9:** imported line values equal the item-master cells exactly (30/30 rows, every mapped field), and each line cites its source row. The AI makes **no** call that outputs line values (gateway log). The mapping proposal is correct for the demo item master and for 3 header-variant fixtures (renamed, reordered, merged headers); low-confidence columns are left for the buyer. Gap questions cover every incomplete construction field and unset response-basis field (incl. GST basis). Every quality and commercial question carries a `requirement_key` from the checklist or policy. A question with no source citation is shown as "co-pilot proposed — no source" and needs explicit acceptance.
- **RFX-10:**
  - **Positive:** the co-pilot draft from the brief pack plus the scripted answers in the runbook (P1–P2) conforms in **≥ 4 of 5** rehearsal runs. Every non-conforming run lists its differences precisely.
  - **Negative:** changing one SKU's GSM, deleting a line, or dropping a quality question each produces exactly that difference.
  - Delivering prepared responses to a non-conforming RFx is refused.
- **RFX-11:** the primary RFx in the demo shows `origin = COPILOT_LIVE` and a transcript that contains the patches that created its lines.
- **Co-pilot eval (I10):** a scripted set of ~12 instructions passes at ≥ 90%: initial drafts, bulk edits ("make lines 12–15 BC flute with 150/120/150/120/150 GSM"), and completeness questions. Patches are always schema-valid. Invalid patches are rejected, never applied.

### 4.2 Distribution (`DIS`)

| ID | Requirement | Tag | Pri |
|---|---|---|---|
| DIS-1 | Send the RFx by email (simulated outbox) | [A] | P0 |
| DIS-2 | Per-vendor status: **Awaiting response** (invited, nothing received) / Received / Processing / Processed / Failed. Comparison-level state: Provisional / Final. (SC-10) | [R] SOT EX-02 | P0 |
| DIS-3 | Simulated inbox delivers the prepared .eml responses | [R] | P0 |

**AC:** DIS-1 makes no real SMTP call and its outbox records are viewable. In DIS-3, delivering the inbox runs Phase A for each response. Phase B runs once all **received** responses have reached Processed or Failed.
- **DIS-2 / SC-10:**
  - A vendor with no response shows "Awaiting response" on the status board, in its grid column header and in each of its cells (never a number, `0`, or MISSING).
  - Its eligibility shows "Not assessed — awaiting response", never Unverified or Fail.
  - It is listed under "Awaiting response" in every answer's exclusions, in scenario output and in the award readiness check. An award with any vendor still awaiting response needs an acknowledgement (audited).
  - Comparison results after each arrival equal the oracle for that arrival subset, and the final result is identical whatever the arrival order.

### 4.3 Ingestion & extraction (`EXT`)

| ID | Requirement | Tag | Pri |
|---|---|---|---|
| EXT-1 | Accept .eml (body + attachments), .xlsx, .xls, .csv, .pdf (digital and scanned), .docx, .jpg/.png/.heic | [A] | P0 |
| EXT-2 | Real AI extraction on every document. No per-vendor or per-file logic. Nothing hardcoded. | [A] A-15 | P0 |
| EXT-3 | Extract line quotes, document terms, references and questionnaire answers into the raw schema (§7) | [A] | P0 |
| EXT-4 | Every extracted field cites evidence: unit id(s) plus a verbatim quote | [R] | P0 |
| EXT-5 | Units are recorded as stated and then classified. Each unit has a **unit_source**: STATED (in the same evidence as the price), INHERITED_FROM_CONTEXT (DL-12), or NONE. | [A-i] | P0 |
| EXT-6 | Document-level terms (discount, freight, GST, validity, tooling, escalation, MOQ, lead time) are extracted with their scope | [A-i] | P0 |
| EXT-7 | Photo path (DL-11): the image is corrected, then gets **two independent reads**. (a) OCR → text-only structuring. (b) A vision-only extraction that never sees OCR output. The two reads are reconciled deterministically. | [A] | P0 |
| EXT-8 | Group prices ("₹42/kg for the 5-ply") are expanded to the RFx lines matching the group attribute that the vendor didn't price individually. Each expanded line is tagged. | [A] | P0 |
| EXT-9 | Unresolved references ("rest same as last year") are captured as explicit references, not values | [A] | P0 |
| EXT-10 | An unreadable or corrupt file gives `FAILED` with a reason. Never an empty success. | [R] | P0 |
| EXT-11 | **Basic re-run** of extraction for a response. Creates a new run, carries human resolutions forward per §6.5, and triggers a global recompute. (B6: promoted to P0) | [R] | **P0** |
| EXT-11b | Extraction run history browser and diff view | [R] | P1 |
| EXT-12 | Revised-quote versioning with a change summary | [R] | P2 |
| EXT-13 | **Tooling/plate/die charges are detected and stored as `DocumentTerm(TOOLING)`.** They are never matched as a line item and never added to a unit price. (B6: promoted to P0) | [R] | **P0** |
| EXT-14 | **Tiered/slab prices are captured as slabs on the line quote** (B6: promoted to P0) | [R] | **P0** |

**Acceptance criteria**
- **EXT-2:** a regenerated, perturbed dataset meets the §1.2 targets with no code or prompt changes.
- **EXT-4:** for text-native sources (xlsx, docx, pdf text, email), the cited verbatim quote must be present in the cited unit. Otherwise the cell is `UNRESOLVED (EVIDENCE_NOT_FOUND)`.
- **EXT-5:**
  - "₹480 per 100 nos" → `unit_class=PER_100`, `unit_source=STATED`.
  - "₹480" with no unit anywhere in its context → `unit_class=UNKNOWN`, `unit_source=NONE` → `UNRESOLVED (UNIT_UNKNOWN)`.
- **EXT-5 / DL-12, the assignment's exact text** "₹42/kg for the 5-ply, 38 for the 3-ply, rest same as last year, freight extra":
  - **42** → PER_KG, STATED, currency INR stated.
  - **38** → PER_KG, **INHERITED_FROM_CONTEXT**, currency INR inherited. It cites both its own span ("38 for the 3-ply") and the source span ("₹42/kg").
  - The inherited cell's status is **ASSUMED**, with reason `UNIT_INHERITED` shown as "unit and currency inferred from '₹42/kg' earlier in the same sentence".
  - Inheritance is accepted only when both spans are in the same evidence unit or in adjacent units of the same message, **and** no other unit token appears between them. Otherwise → `UNIT_UNKNOWN`.
- **EXT-7 (DL-11):**
  - The vision call's request contains no OCR text (verified by a request-inspection test).
  - Reconciliation per matched line: both reads agree on value and unit → OCR-read value with OCR-line evidence, status capped at EXTRACTED.
  - Values differ → `UNRESOLVED (READ_DISAGREEMENT)`, both readings shown with the crop.
  - Only one read found a value → `UNRESOLVED (READ_SINGLE_SOURCE)`.
  - `value_as_stated` is always the OCR reading. `image_read_value` is the vision reading. A mismatch between them never produces `EVIDENCE_NOT_FOUND`.
- **EXT-8:**
  - Group expansion targets RFx lines whose group attribute matches (e.g. ply=3), of **any** item type, that the vendor did not price individually.
  - Whether each expanded cell can be converted is decided by the §5.2 weight-source hierarchy. Without a reference or vendor weight, incompatible types become `NOT_CONVERTIBLE` and are never given a box formula.
  - Expanded cells carry the flag `DERIVED_FROM_GROUP_PRICE` and cite the group statement.
- **EXT-9 (DL-20):** "Rest same as last year" → `Reference(type = PRIOR_UNSPECIFIED, interpretation = AMBIGUOUS)` with **two candidate scopes**:
  - **(A) prices:** RFx lines not priced by any other statement in the response;
  - **(B) terms:** commercial term types required by the response basis or commercial section that the response doesn't state anywhere. Freight is excluded (DL-8): it stays as stated, or UNKNOWN.

  The extraction must **not** pick one reading.
- **EXT-11:** a re-run never deletes the old run. Carry-forward follows §6.5. Changed values reopen review items.
- **EXT-13:** in V1, the tooling row appears as a `DocumentTerm(TOOLING)` and is visible in the vendor panel. No RFx line is matched to it.
- **EXT-14:** V1's slabs are all stored. The slab is selected per NRM-10.

### 4.4 Line matching (`MAT`)

| ID | Requirement | Tag | Pri |
|---|---|---|---|
| MAT-1 | Map each vendor line to one RFx line or `UNMATCHED`, by spec and description, not by row order | [A-i] | P0 |
| MAT-2 | Match confidence HIGH/LOW. LOW → `UNRESOLVED (MATCH_LOW)` until resolved. | [R] | P0 |
| MAT-3 | Spec comparison → `COMPLIANT`, `ALTERNATE` (with the differences listed) or `NOT_RESTATED` | [R] DL-6 | P0 |
| MAT-4 | RFx lines with no quote → `MISSING` | [A] | P0 |
| MAT-5 | Two vendor lines mapped to one RFx line → `UNRESOLVED (MATCH_CONFLICT)` | [R] | P0 |

**AC:**
- MAT-1: shuffling the rows of the V1 sheet produces identical matches.
- MAT-3: any of these makes the line `ALTERNATE`: a layer GSM lower than the RFx value by more than 5%, a ply or flute mismatch, a BF below the RFx value, or any dimension differing by more than 2 mm. If the vendor doesn't restate the spec, the line is `NOT_RESTATED`, treated as quoted against the RFx spec, and labelled as such.
- MAT-4: V3 shows coverage 27/30 with 3 `MISSING` cells.

### 4.5 Normalisation (`NRM`) — rules in §5

| ID | Requirement | Tag | Pri |
|---|---|---|---|
| NRM-1 | Comparison basis: normalised ex-GST ₹ per box | [A]/[DL-2] | P0 |
| NRM-2 | Quantity-unit conversion (per 100/1000/dozen → per box) | [A] | P0 |
| NRM-3 | ₹/kg → ₹/box using the **weight-source hierarchy** (§5.2): reference weight → vendor weight → estimate (NEEDS_REVIEW) → NOT_CONVERTIBLE/UNRESOLVED. The weight source and every step are recorded. | [DL-1, DL-12, DL-18] | P0 |
| NRM-4 | FX conversion at a stated, editable reference rate. The original is kept. | [A] | P0 |
| NRM-5 | Freight is held separately with a basis (INCLUDED/STATED/ESTIMATED/UNKNOWN). Landed cost only for the first three. | [DL-2] | P0 |
| NRM-6 | Comparison is ex-GST. A stated GST rate is backed out. **Vendor silent on GST → apply the RFx-defined tax basis as `ASSUMED (GST_PER_RFX_BASIS)` (DL-26).** RFx basis undefined, or the vendor's statement ambiguous → `UNRESOLVED (GST_UNCLEAR)`. | [R] | P0 |
| NRM-7 | Discounts are applied in a fixed order and scope, and each step is recorded | [A-i] | P0 |
| NRM-8 | "Same as last year" per §5.8 (DL-8, DL-20): historical candidates (same vendor, same line/term, matching spec) are **shown but not applied**. Affected cells and terms are `UNRESOLVED (REFERENCE_AMBIGUOUS)` until the buyer records a confirmation. | [DL-5, DL-8, DL-20] | P0 |
| NRM-9 | Tooling is kept separate from unit prices (P0, via EXT-13). Spreading tooling over annual volume in the annual-cost view is **P1**. | [R] | P0 / P1 |
| NRM-10 | **Slab selection:** pick the slab whose quantity range contains the RFx annual quantity. Other slabs are kept. If no slab contains it → `UNRESOLVED (SLAB_AMBIGUOUS)`. (B6: promoted to P0) | [R] | **P0** |
| NRM-11 | Calculation trace on every normalised value | [R] | P0 |
| NRM-12 | No silent conversions. Every assumption goes to the ledger. | [R] | P0 |
| NRM-13 | **Money handling:** decimal arithmetic and a fixed rounding policy (§5.10) (I6) | [R] | P0 |

**Acceptance criteria**
- **NRM-2:** "₹480 per 100 nos" → ₹4.8000/box. Trace: `480 ÷ 100`. Status unaffected (exact conversion, flag `CONVERTED`).
- **NRM-3 (DL-18):**
  - Line with a documented reference weight + ₹/kg → that weight is used, `weight_source=SKU_REFERENCE`, status **`ASSUMED (REFERENCE_WEIGHT)`** (DL-31). The trace cites the reference source document. A billed-weight caveat states the ₹ impact per 1% weight variance.
  - No reference weight, vendor-stated weight → `weight_source=VENDOR_STATED`, flag `CONVERTED`.
  - Both present and differing by more than the tolerance in the active constant set (default 10%) → `NEEDS_REVIEW (WEIGHT_MISMATCH)`. The reference weight is used.
  - Neither present, RSC with complete construction → estimated weight, `weight_source=ESTIMATED_CONSTANTS`, status **`NEEDS_REVIEW (WEIGHT_ESTIMATED)`** + assumption `METHOD_CONSTANTS`. The trace lists each constant with its value, version and `UNVALIDATED` label. Excluded from formal award calculations until the buyer reviews it (DL-16). After review → `ASSUMED`.
  - PARTITION + ₹/kg with no reference or vendor weight → `NOT_CONVERTIBLE: item type not weight-computable`.
  - DIE_CUT with no reference weight, no vendor weight and no blank size → `NOT_CONVERTIBLE: missing blank size`.
  - A vendor weight whose evidence fails verification → `UNRESOLVED (EVIDENCE_NOT_FOUND)`.
- **NRM-4 (DL-15):** V2 quotes everything in USD. The original USD values are kept and shown ("As quoted" view and the trace). INR values carry the `FX` flag and the rate, as-of date and source. Changing the rate recomputes every dependent value globally (DL-9). Saved scenarios are marked **stale** and recompute when opened (I6). Acknowledged awards are marked **superseded**.
- **NRM-5:** "Freight extra", or no freight statement this year → `UNKNOWN`, landed = null, "Landed not calculable — freight unknown". Last year's freight basis is never used to fill it (DL-8). A buyer-entered disclosed estimate → `ESTIMATED`, the landed status becomes `ASSUMED (FREIGHT_ESTIMATE)`, and the action is audited.
- **NRM-8:** see §5.8 acceptance table.
- **NRM-6 (DL-26):** V5 (silent on GST) with the RFx basis "prices exclusive of GST" → V5 cells `ASSUMED (GST_PER_RFX_BASIS)`, with the assumption listed. The same response against an RFx with no GST basis → `UNRESOLVED (GST_UNCLEAR)`. An ambiguous statement ("GST as applicable" with a GST-inclusive-looking total) → `UNRESOLVED (GST_UNCLEAR)`, never assumed.
- **NRM-10:** V1 annual qty 25,000 against slabs "≤ 10k / 10k–50k / > 50k" → the 10k–50k slab is used, with the slab cited in the trace.

### 4.6 Validation & status (`VAL`)

| ID | Requirement | Tag | Pri |
|---|---|---|---|
| VAL-1 | Every price cell has exactly one canonical status (§6) | [A] | P0 |
| VAL-2 | **Phase A (per cell) checks:** evidence, unit, read agreement, arithmetic, intra-response conflict, weight mismatch, GST clarity, slab selection | [R] | P0 |
| VAL-3 | **Phase B (cross-vendor) checks, after all responses are processed (DL-9):** unit magnitude (`UNIT_SUSPECT`), outlier (`OUTLIER`), plausibility availability | [R] | P0 |
| VAL-4 | Statuses are set only by deterministic rules. The model can raise flags but can never set `VERIFIED`. | [R] | P0 |
| VAL-5 | **Global recompute** after any correction, override, FX change, freight estimate, re-run or new response. Recompute never undoes a human resolution (§6.5). | [DL-9] | P0 |
| VAL-6 | A cell with no plausibility reference (fewer than 2 other numeric peers and no same-line baseline) is capped at `EXTRACTED`, flag `PLAUSIBILITY_UNCHECKED` (I8) | [R] | P0 |

**AC:**
- **VAL-3:** V4's unlabelled "₹480" against a leave-one-out peer median of ₹5.10 → `UNRESOLVED (UNIT_SUSPECT)` with the suggestion "Looks like a price per 100 (₹4.80/box). Confirm?" It is **excluded** from all calculations until the buyer resolves it.
- **DL-9 determinism:** ingest the 5 responses in any of 10 randomised completion orders → identical statuses, values and review items (byte-identical comparison snapshot).
- **VAL-5:** correcting V4's line 7 changes the peer median for line 7. Every other vendor's line-7 status is re-evaluated. A cell the buyer already accepted stays `VERIFIED`. If it now trips a check, it gets the flag `NEW_WARNING_AFTER_REVIEW` and the warning appears in caveats.

### 4.7 Exception review (`REV`)

| ID | Requirement | Tag | Pri |
|---|---|---|---|
| REV-1 | One queue covering: `UNRESOLVED`, `NEEDS_REVIEW`, `NEW_WARNING_AFTER_REVIEW`, Unverified eligibility items, pending freight estimates | [R] | P0 |
| REV-2 | Sorted **decision-sensitive first** (DL-28: could change a line winner, by quantified annual impact), then by money at risk = annual qty × max(leave-one-out peer median, the value if numeric) | [R] | P0 |
| REV-3 | Source view, value, reason, suggested resolution | [R] | P0 |
| REV-4 | Accept, Correct (value/unit/mapping), Mark missing, Override (reason required), **Confirm reference** (DL-20: choose prices / terms / both / neither, with a source note), **Generate clarification pack** (DL-32, template-based, P0, incl. the DL-20 reference section). Generic AI-drafted Ask vendor stays P1. | [R] DL-7, DL-20 | P0 |
| REV-5 | Bulk accept | [R] | P1 |

**AC:** each action writes an `AuditEvent` (before/after/actor/time/reason) and triggers a global recompute that finishes in < 2 s. Accepting a `UNIT_SUSPECT` suggestion records the chosen unit as a buyer resolution.

### 4.8 Comparison workspace (`CMP`)

| ID | Requirement | Tag | Pri |
|---|---|---|---|
| CMP-1 | Grid of lines × vendors with the ex-GST ₹/box price. The best price per line is highlighted among cells that are **includable under the formal policy** (DL-16), compliant and eligible under the current mode. NEEDS_REVIEW cells are shown with a warning but never highlighted as best. | [A] | P0 |
| CMP-2 | Basis toggle: Unit (default) / Landed / As quoted | [DL-2] | P0 |
| CMP-3 | Canonical status badge + flag badges on every cell | [A] | P0 |
| CMP-4 | Provenance drawer: source + trace + audit | [R] | P0 |
| CMP-5 | Vendor panel: coverage, **Quality and Commercial eligibility shown separately** with per-question results, documents, terms (incl. tooling and escalation). **Every supporting document opens directly from the comparison workspace**: from the vendor panel, a questionnaire-answer row, a document-fact row, and the provenance drawer. It opens in the viewer with the cited evidence highlighted, and the original file is downloadable (SC-11, SOT FN-10). | [A] | P0 |
| CMP-6 | Baseline column (last year's awarded price per line) and Δ% per vendor | [DL-5] | P0 |
| CMP-7 | Alternates never highlighted as best like-for-like | [DL-6] | P0 |
| CMP-8 | "Provisional" banner until Phase B completes | [DL-9] | P0 |

**AC:** the Landed view never shows a number for `UNKNOWN` freight. Excluded statuses (§6.2) render as a status chip, never as a number.
- **CMP-5 / SC-11:** for every attached document of every vendor, the document list API returns it with type and facts. Opening it returns the original bytes (SHA-256 equals the stored hash) with the right content type. In the UI, each of the four entry points opens the right document at the cited page or region.
- **SC-10:** an awaiting vendor's column shows "Awaiting response" chips. Best-price highlighting ignores it.

### 4.9 Eligibility (`ELG`) — rules in §5.7

| ID | Requirement | Tag | Pri |
|---|---|---|---|
| ELG-1 | Per question per vendor: Pass / Fail / Unverified, or **NOT_APPLICABLE** when the question's applicability condition isn't met (DL-24). NOT_APPLICABLE is not an eligibility verdict and is excluded from roll-ups. | [DL-3, DL-24] | P0 |
| ELG-2 | **Roll-up per section** (Quality, Commercial) and overall. For each scope: any mandatory Fail → Fail; otherwise any mandatory Unverified → Unverified; otherwise Pass. (I2) | [DL-3] | P0 |
| ELG-3 | Modes: Strict (Pass only) / Inclusive (Pass + Unverified, labelled). **Scope:** `quality` (default; the **only** scope that means "cleared the quality questionnaire", DL-14) or `all_mandatory` (explicit opt-in, labelled "quality and commercial requirements") | [DL-3, DL-14] | P0 |
| ELG-4 | Every state shows its reason and evidence | [R] | P0 |
| ELG-5 | Buyer override with reason, audited | [DL-7] | P0 |
| ELG-6 | **Label control:** the words fail/failed/rejected/disqualified/"did not clear" are used only for vendors whose state in the stated scope is FAIL. This is enforced in templates, exports, the memo, and analyst text through a runtime lint (§8.2 AI-12). (I2) | [DL-3] | P0 |

**AC:**
- V5 is Quality = Pass and Commercial = Fail (payment terms not accepted). The VP question (quality scope, strict) includes V5. The analyst states the scope it used and reports V5's commercial result **separately**, never as part of the quality questionnaire (DL-14).
- V3 is Quality = Unverified and is listed as "Excluded — unverified (ISO 9001 certificate expired 2026-03-31)", never as failed.
- **DL-29:** the primary RFx has no FSC question, so V1's lack of an FSC certificate affects nothing (the panel lists the documents V1 did provide). Food-grade gates only food-contact lines: in the line-level test variant, a vendor without a food-grade declaration is excluded **only** from the 3 food-contact lines, and its vendor-level Quality result is unchanged.
- **DL-23:** V5's Quality Pass and Commercial Fail are evidenced by documents in its separate questionnaire submission. The V5 quote email body is byte-identical to the assignment sentence.
- The trap question "on what grounds did the others fail?" gets an answer that corrects the premise.

### 4.10 Natural-language analyst (`NLA`)

| ID | Requirement | Tag | Pri |
|---|---|---|---|
| NLA-1 | Free-form questions over the **whole comparison** (SOT FN-11): lines, quotes, terms, eligibility, **questionnaire answers (incl. answer text), structured document facts (incl. certificate details), and their supporting evidence**, baseline | [A] | P0 |
| NLA-2 | Answers as text, table, chart, file export | [A] | P0 |
| NLA-3 | Every number comes from a deterministic tool result | [A] | P0 |
| NLA-4 | Every answer includes the method, basis, filters, **interpretation (when one was chosen)**, exclusions with reasons, assumptions, and data caveats | [R] | P0 |
| NLA-5 | Multi-turn context | [A-i] | P0 |
| NLA-6 | Ask a clarifying question back when interpretations differ materially | [R] | P1 |
| NLA-7 | Say so when the data can't answer the question | [R] | P0 |
| NLA-8 | Save an analyst answer as a scenario (scenarios can always be saved from the Award screen, P0) | [R] | P1 |
| NLA-9 | Show work: the exact tool calls and raw results | [R] | P0 |
| NLA-10 | **Award, split, savings and eligibility-filtered cost questions must use `run_scenario`**, not free-form SQL (I8) | [R] | P0 |
| NLA-11 | **Read-only access to structured document facts and questionnaire answers (SC-02):** the analyst can query questionnaire answers (value, verbatim answer text, state, reason), document facts (document type, standard, certificate number, entity name, issue/expiry dates, validity vs RFx dates, entity match) and the **cited evidence snippets** behind them. Every row carries an `evidence_ref`. There is **no access to full document text**: only evidence units cited by an extracted fact or answer, as length-capped snippets. | [A] SOT FN-10/11 | P0 |
| NLA-12 | **Traceability of non-numeric facts:** every document fact or answer stated in a narrative (dates, certificate numbers, entity names, quoted terms) must come from a tool result row with an `evidence_ref`. The answer automatically gets a source link per fact, which opens the provenance drawer. | [R] | P0 |
| NLA-13 | **No invention of missing facts:** if a fact was not extracted (null, `NOT_EXTRACTED`) or the document isn't in the data, the analyst says so ("not stated in V4's documents"). It never infers expiry dates, certificate scope or entity names. | [R] SOT AI-03 | P0 |

**AC:**
- NLA-3: the grounding check (§8.2 AI-7) passes. Otherwise the answer is regenerated once by **appending** feedback (§8.2 AI-13). If it still fails, a "numbers not verified" banner is shown with the raw tables.
- NLA-4, for the VP question:
  - interpretation line;
  - table;
  - total;
  - savings vs baseline and vs the best single vendor, per §5.9;
  - "Excluded — failed: V4 (capacity 150 t < 250 t)";
  - "Excluded — unverified: V3 (…)";
  - uncovered lines;
  - caveat line;
  - freight-dependent lines with break-even (DL-25), the decision-sensitive line count with the largest impact (DL-28), V2 FX exposure (DL-30) and billed-weight exposure (DL-31), all code-generated;
  - by default, NEEDS_REVIEW values are excluded, as in a formal award (DL-16). If the user asks to include them, the answer is labelled **"Exploratory — includes N values needing review"**, lists them, and is never shown as an award figure.
- **NLA-2 charts (SC-09, SOT FN-14):** every chart's bound data equals the tool-result rows it references, value for value at stored precision, with no extra or missing series or categories. Axis and series labels name the correct vendor, line and unit. Chart values are never typed by the model.
- **NLA-2 / EXP-3 exports (SC-09, SOT FN-15):** an exported analyst table re-read from xlsx/csv equals the result rows: same row count; same values (Decimal text equality); same vendor names and ids, line numbers, units and currency labels, and status and flag columns. Exclusions and caveats are included as a sheet or footer.
- NLA-10: on the walkthrough and off-script sets, every award-type answer's numbers come from `run_scenario` results (checked in the eval).
- **NLA-4 coverage disclosure (SOT EDGE-07):** any answer that ranks, totals or compares vendors where an included vendor has MISSING lines must list that vendor's coverage ("V3: 27/30") and the missing line numbers in its code-generated exclusions. Single-vendor totals are computed over covered lines and labelled with their coverage.
- **NLA-11:** *"Whose ISO 9001 certificate is valid through the contract period?"* is answered from the document-fact rows, with each vendor's expiry date, validity result and source link. V3's expired certificate is reported as expired with its date. V4's entity mismatch is reported.
- **NLA-12:** the grounding check is extended to dates and identifiers. A date, certificate number or entity name in the narrative with no matching result row fails grounding (→ appended regeneration, then a banner).
- **NLA-13:** questions about facts that are absent from the fixtures (e.g. "when does V1's FSC certificate expire?" when V1 provided none) are answered "not in the data" in 100% of eval cases.
- No hardcoded question→answer mappings. Prompts contain no dataset values (enforced by tests).

### 4.11 Scenarios & award (`AWD`)

| ID | Requirement | Tag | Pri |
|---|---|---|---|
| AWD-1 | Deterministic scenario engine with these params: `strategy` ∈ {single_vendor, cheapest_per_line}; `basis` ∈ {**freight_aware (default for formal, DL-25)**, unit, landed}; `eligibility_mode` ∈ {strict, inclusive, none}; `eligibility_scope` ∈ {quality (default), all_mandatory}; `include_alternates` (default false); `status_policy` ∈ {**exclude_needs_review (default)**, include_needs_review}; `context` ∈ {formal, exploratory}; `exclude_vendors[]`; `line_filter`. **No vendor cap in P0.** In `formal` context, `include_needs_review` requires an **explicit buyer override** (warning + audit, DL-16). In `exploratory` context it is allowed on request and the result is labelled "Exploratory". | [A] A-20, DL-6, DL-16 | P0 |
| AWD-2 | Output: per-line award, per-vendor share and spend, total, savings per §5.9 (lower bounds flagged), uncovered lines, exclusions with reasons, **per-line freight status (`FREIGHT_DEPENDENT` + break-even, DL-25)**, **per-line decision sensitivity (DL-28)**, **FX exposure (DL-30)** and **billed-weight exposure (DL-31)**, `cells_used` | [A] | P0 |
| AWD-3 | Readiness check + acknowledgement (audited). Lists any NEEDS_REVIEW override and the cells it brought in, **any vendor still awaiting response**, **any unresolved REFERENCE_AMBIGUOUS items**, **every FREIGHT_DEPENDENT line with its break-even (DL-25)**, **decision-sensitive lines with quantified impact (DL-28)**, and **FX and billed-weight exposure (DL-30/31)**. | [R] | P0 |
| AWD-4 | Award memo | [A] | P0 |
| AWD-5 | Include-alternates toggle. When used, the memo lists the alternate lines and their spec differences. | [DL-6] | P0 |
| AWD-6 | Vendor share cap | [R] | **P1, no demo or dataset dependency** (B6) |
| AWD-7 | Scenario staleness: a scenario is stale when any of its `cells_used` fingerprints change. Opening it offers recompute. Acknowledged awards are never mutated; they are marked superseded. (I6) | [R] | P0 |

**AC:**
- Determinism: identical inputs → identical output.
- Excluded statuses never enter totals. In `formal` context with the default policy, NEEDS_REVIEW cells never enter totals.
- Turning on `include_needs_review` in `formal` context without an override record is rejected. With the override: a warning lists the cells and money at risk, an `AuditEvent(NEEDS_REVIEW_OVERRIDE)` is written, and the memo names the cells.
- An exploratory result promoted to the Award screen is recomputed under the formal policy.
- Uncovered lines are never awarded to an ineligible or excluded cell.
- Tie-break: Pass over Unverified, then VERIFIED over other statuses, then lower vendor id. The tie-break is disclosed.
- **DL-25:** on the VP split, every V5-won line where V1/V2 have known landed cost and V5's freight is unknown is FREIGHT_DEPENDENT, with break-even = best_K − best_U to 4 dp. A line where V1's delivered price beats V5's unit price goes to V1, with no flag. Readiness requires an acknowledgement. Entering a disclosed V5 freight estimate removes the flag and recomputes.
- **DL-28:** for each line, `sensitivity.sensitive = true` iff some uncertain input's alternative outcome changes the winner. The quantified impact equals the oracle (annual ₹ delta / flip margin % / break-even).
- **Oracle parity:** for 20 parameter combinations, the engine output equals the independent test oracle (implementation plan §4.2, M7).

### 4.12 Export & audit (`EXP`, `AUD`)

| ID | Requirement | Tag | Pri |
|---|---|---|---|
| EXP-1 | xlsx export with sheets: Comparison, Sources, Traces, Assumptions, Eligibility (by section), Exclusions. Every Comparison cell equals the grid value and status, including "Awaiting response" and excluded chips, which are never exported as numbers. (SC-09) | [A] | P0 |
| EXP-2 | Memo export (Markdown + printable HTML) | [A] | P0 |
| EXP-3 | Analyst table export (.xlsx/.csv) | [A] | P0 |
| AUD-1 | Audit log of all human actions and assumption changes | [DL-7] | P0 |
| AUD-2 | Override marker everywhere it applies | [DL-7] | P0 |

---

## 5. Domain rules (deterministic)

### 5.1 Unit taxonomy and classification
Units: `PER_BOX` (incl. per pc / nos / each) · `PER_100` · `PER_1000` · `PER_DOZEN` · `PER_KG` · `PER_SET` · `LUMP_SUM` · `UNKNOWN`.

- The AI classifies the verbatim unit string. A deterministic dictionary then cross-checks it:
  - **dictionary recognises the string and agrees** → accepted;
  - **dictionary recognises it and disagrees** → `UNKNOWN`;
  - **dictionary doesn't recognise the string** → *no opinion*, and the AI class is accepted with the flag `UNIT_DICT_UNSEEN`. (I9)
- `unit_source` (EXT-5) decides the status impact: STATED → none; INHERITED_FROM_CONTEXT → ASSUMED; NONE → UNKNOWN.

### 5.2 Weight conversion (DL-1, DL-12, DL-18)

**Item-type support matrix (I5, B5)**
**Weight-source hierarchy (DL-18).** Each converted cell records `weight_source`, the weight, and every calculation step.
| Priority | Source | Status effect | Formal award |
|---|---|---|---|
| 1 | **Documented SKU reference unit weight** (`RfxLine.reference_unit_weight_g` + `reference_weight_source`) | **`ASSUMED (REFERENCE_WEIGHT)`** (DL-31): the vendor will invoice on actual weight | included (assumption + billed-weight caveat) |
| 2 | **Vendor-stated unit weight** (used when no reference weight; a cross-check when one exists, with a mismatch beyond tolerance → `NEEDS_REVIEW (WEIGHT_MISMATCH)`) | flag `CONVERTED` (the vendor's own billing basis) + billed-weight caveat | included unless mismatch |
| 3 | **Estimate from approximate engineering constants**, for supported item types with complete construction only (matrix below) | `NEEDS_REVIEW (WEIGHT_ESTIMATED)` + assumption `METHOD_CONSTANTS`; after buyer review → `ASSUMED` | **excluded until buyer review** (DL-16) |
| 4 | None of the above | `NOT_CONVERTIBLE` (missing inputs or unsupported type named) | excluded |
| — | Weight evidence present but unreadable or contradictory | `UNRESOLVED` | excluded |

**Item types that can be estimated (priority 3 only)**
| Item type | Estimate allowed? | Formula |
|---|---|---|
| RSC box | ✅ if `construction_complete` | RSC blank |
| DIE_CUT box | ✅ only if RFx `blank_size_mm` given **and** layers complete | Flat blank |
| PAD (sheet) | ✅ if `blank_size_mm` (L×W) **and** layers complete | Flat blank |
| PARTITION (set) | ❌ never | — |
| Any other / unknown | ❌ never | — |

**Estimation formulas.** Constants come from the active **versioned constant set** (§5.11). Each is labelled with its validation status and cited in the trace.
- **Flute-to-medium mapping:** mediums, in layer order from the outside in, map in order to the characters of `flute_profile` (e.g. a 5-ply "BC" → first medium B, second medium C). Count mismatch → construction incomplete.
- **Grammage (g/m²)** = Σ liner GSM + Σ (medium GSM × take-up factor of its flute). Initial take-up factors (**approximate engineering constants, UNVALIDATED**): A 1.50, C 1.45, B 1.35, E 1.25.
- **RSC blank (mm)** = (2L + 2W + joint allowance) × (W + H), using internal dimensions. Initial joint allowance 35 mm (**UNVALIDATED**). The trace records: "computed from internal dimensions; excludes caliper allowance and trim; may understate weight by a few percent."
- **Flat blank** = blank L × blank W.
- **Weight (kg)** = blank area (m²) × grammage ÷ 1000. **₹/box** = ₹/kg × weight.
- An estimated weight makes the cell `NEEDS_REVIEW (WEIGHT_ESTIMATED)` with assumption `METHOD_CONSTANTS`. A reference or vendor-stated weight does not.

Constants are disclosed, versioned approximations. They are **never** described as verified industry facts, and **never** used to fill in a missing input such as a GSM, flute, dimension or blank size.

### 5.3 Currency (DL-15)
INR is the base. `FxRate(currency, rate, as_of, source)` is set at RFx level and the buyer can edit it. A converted cell is `ASSUMED (FX_RATE)`. The original currency and amount are kept. **FX exposure (DL-30):** V2 is a domestic supplier quoting USD-linked prices **invoiced in INR at the rate on invoice date**. The comparison uses the stated reference rate. Every answer, scenario and memo that includes V2-awarded spend discloses the exposure deterministically: "each 1% USD/INR move changes V2-awarded spend by ₹X".

### 5.4 Freight (DL-2)
| Vendor says | `freight_basis` | `freight_inr_per_box` | Landed |
|---|---|---|---|
| Delivered / FOR destination / freight inclusive | `INCLUDED` | 0 (included in unit price) | = unit price |
| Freight amount per box, % of value, or per kg (with a weight available) | `STATED` | converted | unit + freight |
| "Freight extra" / ex-works / silent | `UNKNOWN` | null | not calculable (excluded on landed basis) |
| Buyer-entered disclosed estimate | `ESTIMATED` | buyer value | unit + freight, landed status ASSUMED |

**Freight-aware award comparison (DL-25).** In formal award scenarios (`basis = freight_aware`, the default), for each line:
- K = includable candidates with calculable landed cost; U = candidates with UNKNOWN freight.
- best_K = lowest landed in K; best_U = lowest unit price in U (a lower bound on its landed cost).
- If K is non-empty and best_K ≤ best_U: the winner is best_K. The result holds whatever U's freight turns out to be.
- If best_U < best_K: the provisional winner is best_U, and the line is **`FREIGHT_DEPENDENT`** with **break-even freight = best_K − best_U (₹/box)**: "V5 wins unless its freight exceeds ₹0.62/box".
- If K is empty: the winner is best_U, flagged `FREIGHT_UNKNOWN_ALL` (no break-even).
- Savings on freight-dependent lines are reported as **lower bounds**, with the count of such lines.
- The readiness check lists every freight-dependent line with its break-even. Proceeding needs an audited acknowledgement, unless the buyer has entered a disclosed freight estimate (ESTIMATED) that resolves it.

When the analyst ranks on unit price, it must mention mixed freight bases. **Freight always comes from this year's response.** Historical freight terms are never carried forward (DL-8).

### 5.5 Order of price adjustments
As-quoted → slab selection → qty/weight conversion → line discount → document discount (in scope) → GST back-out → FX → **unit_price_inr_ex_gst** → + freight (if allowed) → **landed_inr_ex_gst**. Each step is a trace entry.

### 5.6 Two-phase processing (DL-9)
- **Phase A (per response, may run concurrently):** parse, extract, verify evidence, match, normalise each cell, run Phase A checks. Its output does not depend on any other vendor.
- **Phase B (global, single-threaded, after all responses in the set are Processed/Failed):**
  - **leave-one-out peer median** per line, computed from Phase A numeric values of *other* vendors, excluding cells whose Phase A status is UNRESOLVED/NOT_CONVERTIBLE/MISSING;
  - unit-magnitude and outlier checks;
  - the plausibility-availability cap (VAL-6);
  - status precedence (§6.3);
  - eligibility roll-ups;
  - review items.
- **Peer independence:** peer medians use Phase A values, so they don't depend on other cells' Phase B statuses. That makes them order-independent and avoids circular dependencies.
- **Global recompute:** any change re-runs normalisation for affected cells and then the whole of Phase B. With 150 cells this is cheaper than tracking dependencies.

### 5.7 Eligibility (DL-3, I2)
- Each question has `section ∈ {QUALITY, COMMERCIAL}` and an `applicability` ∈ {ALL, LINES_WITH_FLAG(food_contact), LINES_WITH_FLAG(requires_fsc)} (DL-24).
- **Line-level gating (DL-29):** a flag-scoped question **never enters the vendor-level roll-up**. It gates only that vendor's cells on lines with the flag. A food-contact cell is a candidate only if the vendor's food-grade state is PASS (strict) or PASS/UNVERIFIED (inclusive). A vendor that quotes no flagged line gets **NOT_APPLICABLE**, shown with its reason.
- "Cleared the quality questionnaire" = the vendor-level Quality roll-up over ALL-scope questions **plus** line-level food-grade gating on food-contact lines. The analyst states this interpretation.
- **The primary RFx has no FSC question** (DL-29). An FSC-required (`requires_fsc`) variant exists only as a test fixture.
- **Per question:**
  - **Pass:** the answer meets the pass rule, and any required evidence is present, readable, of the right type, unexpired and in the vendor's name.
  - **Fail:** the answer explicitly doesn't meet the rule ("No"; 150 t vs ≥ 250 t).
  - **Unverified:** unanswered; claimed without the required evidence; evidence unreadable, expired or under another entity's name; or the answer couldn't be extracted confidently.
- **Roll-up** per section and for `all_mandatory`, per ELG-2.
- "Cleared the quality questionnaire" defaults to **Quality section, strict**. The analyst always states this interpretation.
- The AI extracts answers and document facts. Rules decide the state.

### 5.8 Baseline and "same as last year" (DL-5, DL-8, B1)
`BaselinePrice` rows always have a vendor: `(rfx_line_id, vendor_id, unit_price_inr_ex_gst, freight_basis, spec_signature, period, awarded: bool, source)`.
- `spec_signature` is a canonical hash of {item_type, dims, ply, flute_profile, layer GSMs, BF, printing}.
- At most one `awarded=true` row per line (last year's contract price).

`BaselineTerm` rows (DL-20) hold each vendor's last-year commercial terms: `(vendor_id (required), term_type, value, unit, period, source)`.

**"Same as last year" is ambiguous (DL-20).** Both readings are evaluated, and **neither is applied without confirmation**.

**Reading A — prices.** For vendor V and each line L in scope A, a *candidate* is computed:
| Condition | Candidate | Status before confirmation | After buyer confirms "prices" |
|---|---|---|---|
| Row with `vendor_id = V`, line L, `spec_signature` = current | that row's price (cited) | **UNRESOLVED (REFERENCE_AMBIGUOUS)**, candidate shown, excluded | **ASSUMED (BASELINE_REFERENCE)**, included |
| Row for V and L, signature differs | none | **UNRESOLVED (BASELINE_SPEC_CHANGED)** | unchanged (needs a vendor price) |
| Rows only for other vendors, or none | none | **UNRESOLVED (BASELINE_NOT_FOR_VENDOR)**. Another vendor's price is **never** a candidate. | unchanged |

**Reading B — terms.** For each term type in scope B: the candidate is V's own `BaselineTerm` of that type. The term shows **"Unresolved — candidate from last year: …"**. It is never used in any calculation or eligibility result. After the buyer confirms "terms", it becomes a `DocumentTerm(source = CONFIRMED_HISTORICAL)` with status ASSUMED. **Freight is never a reading-B candidate** (DL-8).

**Confirmation** is a buyer `Resolution(type = REFERENCE_CONFIRMATION, choice ∈ {prices, terms, both, neither}, source_note)`, audited (DL-7). "Neither" leaves everything UNRESOLVED and marks the reference closed. The **clarification request** (J9 P0) is generated from the same structured candidates by a template. No AI is involved, so no content is invented.

**Freight basis when resolving (DL-8):** only the unit price is taken from the row. Last year's freight basis and amount are **never** carried forward. Freight comes from **this year's** document terms. "Freight extra", or no statement → UNKNOWN, and landed cost is not calculated. If last year's basis was INCLUDED and this year's is not, the cell gets the flag `FREIGHT_BASIS_CHANGED` (a caveat only, never a value). The caveat reads: "last year's price was delivered; this year freight is extra — the unit price may not be like-for-like with last year".

**Other baseline uses:** savings (§5.9, using `awarded` rows), the CMP-6 column, and the Phase B plausibility reference.

**Acceptance table (tests, T-EDGE-05c-A/B):**
- Before confirmation: same vendor + same spec → UNRESOLVED (REFERENCE_AMBIGUOUS) with the candidate shown and excluded from every total. Changed spec → BASELINE_SPEC_CHANGED. Other vendor only / no rows → BASELINE_NOT_FOR_VENDOR. Unstated terms → unresolved term candidates, with no effect on calculations or eligibility.
- After "prices": only the same-vendor, same-spec cells become ASSUMED.
- After "terms": only the term candidates are applied, never freight.
- After "both": both.
- After "neither": nothing is applied.
- No path applies a candidate without a confirmation record.

### 5.9 Savings definitions (I4)
Let **A** = the set of lines the scenario awards (uncovered lines excluded). Spend uses the scenario basis, with `annual_qty` from the RFx.
- **Scenario spend** S = Σ_{l∈A} qty_l × price_l of the awarded cell.
- **Savings vs last year:**
  - computed over **A_b** = lines in A that have an `awarded` baseline row comparable on the scenario basis. On the landed basis, baseline rows with freight UNKNOWN are not comparable.
  - Savings = Σ_{A_b} qty × (baseline − awarded price), also as a % of the baseline spend on A_b.
  - Always reported as "on N of |A| awarded lines, covering ₹X (Y%) of scenario spend". Lines without a baseline are listed.
  - Lines carrying `FREIGHT_BASIS_CHANGED`, or with unit-basis cells whose freight basis differs from the baseline's, are listed in the caveats.
- **Savings vs best single vendor:**
  - Candidates = vendors that pass the same eligibility, alternates and status filters as the scenario.
  - Each candidate's coverage C_v = lines in A where the vendor has an includable cell.
  - The comparator is the candidate with the **largest |C_v|**. Ties go to the lowest Σ_{C_v} qty × its price, then the lower vendor id.
  - Savings = Σ_{C_v} qty × (vendor price − scenario awarded price), reported as "vs V1 on the 28 of 28 awarded lines V1 covers". If |C_v| < |A|, the uncovered lines are listed. Single-vendor totals are never extrapolated to missing lines.
- **Single-vendor strategy:** the total is over the lines the vendor covers. Coverage is shown and missing lines are listed. No imputation.
- **Rounding:** §5.10.

### 5.10 Money precision (I6)
- Decimal arithmetic throughout, never floating point.
- Unit prices are stored to 4 dp.
- Annual amounts = unrounded unit price × qty, rounded to whole rupees **once**, at the line total. Totals are sums of rounded line totals.
- Percentages are shown to 1 dp. Rounding is ROUND_HALF_UP.
- Display: ₹/box to 2 dp. Totals in ₹ lakh/crore to 2 dp.
- The grounding check compares at displayed precision.

### 5.11 Engineering constants (DL-18)
- All constants live in a **versioned constant set**:
  - flute take-up factors;
  - joint allowance;
  - spec tolerances (GSM −5%, dims ±2 mm);
  - weight-mismatch tolerance (10%);
  - unit-suspect (20×) and outlier ([0.5×, 2×]) thresholds;
  - OCR confidence threshold (80).
- Each constant records `value`, `unit`, `validation_status` (UNVALIDATED / VALIDATED), `source`, and `validated_by` / `validated_at`.
- All initial values are **UNVALIDATED**. They are shown as "approximate engineering constant — not validated" (tolerances and thresholds as "product heuristic — not validated") in the UI, traces, xlsx Assumptions sheet and memo.
- Every normalised value records the constant-set version used.
- Activating a new version (e.g. after a packaging engineer signs off) is an audited buyer action. It triggers a global recompute and marks scenarios stale.
- Editing constants in the UI is P0 only as **selecting an existing version**. Authoring new versions is done in the config file (no new UI feature).

---

## 6. Canonical status model (DL-10) — the only definition

This section supersedes the brief's six states and the earlier PRD's seven.

### 6.1 Three separate vocabularies
| Vocabulary | Applies to | Values |
|---|---|---|
| **Value status** | each price cell (unit basis); landed values computed separately | `VERIFIED`, `EXTRACTED`, `ASSUMED`, `NEEDS_REVIEW`, `UNRESOLVED`, `NOT_CONVERTIBLE`, `MISSING` |
| **Flags** | any cell, independent of status | `CONVERTED`, `FX`, `DERIVED_FROM_GROUP_PRICE`, `ALTERNATE`, `NOT_RESTATED`, `OVERRIDE`, `PLAUSIBILITY_UNCHECKED`, `UNIT_DICT_UNSEEN`, `FREIGHT_BASIS_CHANGED`, `NEW_WARNING_AFTER_REVIEW`, freight basis |
| **Eligibility state** | vendor × question / section | `PASS`, `FAIL`, `UNVERIFIED` |

"Unverified" is **only** an eligibility state. It is never a value status.

### 6.2 Value status definitions and inclusion
| Status | Meaning | Has number? | In calculations | Shown as |
|---|---|---|---|---|
| `VERIFIED` | Buyer accepted, corrected or overrode it; **or** it was auto-verified (§6.4) | yes | **Included** | number |
| `EXTRACTED` | Read by the AI, no failing check, not reviewed by a person, not eligible for auto-verify | yes | **Included**, counted as "unreviewed" in caveats | number + badge |
| `ASSUMED` | Depends on a disclosed assumption (§6.3 table) | yes | **Included**, assumption listed in caveats | number + badge |
| `NEEDS_REVIEW` | A number exists, but an **advisory** check flagged it: `OUTLIER`, `ARITHMETIC_MISMATCH`, `WEIGHT_MISMATCH`, `WEIGHT_ESTIMATED` | yes | **Formal award: excluded by default** (buyer override per scenario, warned + audited, DL-16). **Exploratory analysis: included on request**, labelled "Exploratory", with caveats. | number + warning |
| `UNRESOLVED` | No trustworthy number yet (**blocking**): `UNIT_UNKNOWN`, `UNIT_SUSPECT`, `READ_DISAGREEMENT`, `READ_SINGLE_SOURCE`, `EVIDENCE_NOT_FOUND`, `PRICE_CONFLICT`, `MATCH_LOW`, `MATCH_CONFLICT`, `GST_UNCLEAR`, `SLAB_AMBIGUOUS`, `BASELINE_SPEC_CHANGED`, `BASELINE_NOT_FOR_VENDOR`, `REFERENCE_UNRESOLVED`, `REFERENCE_AMBIGUOUS`, `LOW_OCR_CONFIDENCE` | maybe (shown as a candidate) | **Never included.** Listed in exclusions. | chip + candidate value in drawer |
| `NOT_CONVERTIBLE` | Insufficient inputs, an unsupported item type, or (landed basis only) `FREIGHT_UNKNOWN` | no | **Never included.** Listed. | chip |
| `MISSING` | Not quoted | no | **Never included.** Listed. | chip |

### 6.3 What sets each status (the complete list of transformations)
| Transformation / condition | Effect |
|---|---|
| Qty-unit conversion from a **stated** unit | flag `CONVERTED`, no status change |
| Unit **inherited from context** (DL-12) | `ASSUMED (UNIT_INHERITED)` |
| Weight conversion with a **vendor-stated** weight | flag `CONVERTED`, no status change |
| Weight conversion with a **documented SKU reference** weight | `ASSUMED (REFERENCE_WEIGHT)` (DL-31) + billed-weight caveat |
| Weight conversion with an **estimated** weight (approximate constants) | `NEEDS_REVIEW (WEIGHT_ESTIMATED)` + assumption `METHOD_CONSTANTS`. After buyer review → `ASSUMED`. |
| FX conversion | `ASSUMED (FX_RATE)` + flag `FX` |
| Group-price expansion | flag `DERIVED_FROM_GROUP_PRICE` only. A unit inherited inside the group statement adds ASSUMED. |
| "Same as last year", before confirmation (DL-20) | `UNRESOLVED (REFERENCE_AMBIGUOUS)`, candidate shown, excluded |
| "Same as last year", after buyer confirmation of "prices" (DL-8, DL-20) | `ASSUMED (BASELINE_REFERENCE)` |
| Discount in an explicit scope; GST back-out at a stated rate; slab selection | no status change (trace only) |
| Vendor silent on GST, RFx basis defined (DL-26) | `ASSUMED (GST_PER_RFX_BASIS)` |
| GST basis undefined or the vendor's statement ambiguous | `UNRESOLVED (GST_UNCLEAR)` |
| Discount with unclear scope | `UNRESOLVED (REFERENCE_UNRESOLVED)` |
| Freight ESTIMATED | the unit status is unchanged; the **landed** value is `ASSUMED (FREIGHT_ESTIMATE)` |
| Image-sourced value, both reads agree | at most `EXTRACTED` |
| No plausibility reference (VAL-6) | at most `EXTRACTED`, flag `PLAUSIBILITY_UNCHECKED` |

**Precedence (the worst wins):** `MISSING` > `NOT_CONVERTIBLE` > `UNRESOLVED` > `NEEDS_REVIEW` > `ASSUMED` > `EXTRACTED` > `VERIFIED`.
**Landed status** = the worse of the unit status and the freight condition. UNKNOWN freight → `NOT_CONVERTIBLE (FREIGHT_UNKNOWN)`; ESTIMATED → at least `ASSUMED`.

### 6.4 Auto-VERIFIED (all of these must hold)
- digital, text-native source;
- evidence verified;
- unit_source = STATED and unit recognised by the dictionary;
- all Phase A and Phase B checks pass, with a plausibility reference available;
- no model flags;
- no assumptions.

Anything else is at most `EXTRACTED`.

### 6.5 Human resolutions and recompute (DL-7, DL-9, I6)
- **Resolution types:**
  - **Accept:** keeps the candidate value and clears the blocking/advisory reason.
  - **Correct:** sets value, unit or mapping.
  - **Mark missing.**
  - **Override:** sets the value directly, flag `OVERRIDE`, reason required.
- After a resolution, the status = `VERIFIED`, unless an assumption remains (e.g. FX). In that case it is `ASSUMED`, with the assumption marked accepted.
- **Stickiness:** recompute never undoes a resolution. New check failures on a resolved cell add the flag `NEW_WARNING_AFTER_REVIEW` (shown in caveats and the queue). The status is not downgraded.
- **Carry-forward on re-run (EXT-11):** a resolution is keyed by (vendor, rfx_line, field) + the **raw fingerprint** (value_as_stated, unit_as_stated, evidence text).
  - Same fingerprint in the new run → the resolution carries forward.
  - Different → the resolution is marked `STALE_SOURCE_CHANGED`, is not applied, and the review item reopens. Overrides follow the same rule.
- **Scenarios** are marked stale when any `cells_used` fingerprint changes. **Acknowledged awards** are immutable: they are marked superseded and need re-acknowledgement.

---

## 7. Data model (logical)

| Entity | Key fields | Notes |
|---|---|---|
| **Rfx** | id, title, kind (primary/sandbox), **origin (COPILOT_LIVE/SEEDED_FALLBACK/SANDBOX)**, status, version, response_basis, delivery_location, **canonical_spec_version, conformance {status, differences[], checked_at}, copilot_transcript_id** | DL-17, DL-19 |
| **CanonicalRfxSpec** | version, content_hash, spec (lines, questionnaire with requirement_keys, response basis) | Seed. Read-only. Basis of the prepared responses (DL-19). |
| **RfxLine** | id, rfx_id, line_no, sku_code, description, item_type (RSC/DIE_CUT/PAD/PARTITION), dims_mm, blank_size_mm?, ply, flute_profile, layers [{position, role, gsm, bf}], printing, annual_qty, **reference_unit_weight_g?, reference_weight_source?**, **food_contact (bool), requires_fsc (bool)**, construction_complete (derived), missing_construction [], spec_signature (derived) | I5 rules in RFX-3 AC. Reference weight per DL-18. Flags per DL-24. |
| **Question** | id, rfx_id, **section (QUALITY/COMMERCIAL)**, **requirement_key**, **applicability**, text, answer_type, mandatory, pass_rule, evidence_required, evidence_doc_type | I2. `requirement_key` for conformance (RFX-10). Applicability per DL-24. |
| **Term** | id, rfx_id, type, text | |
| **Vendor** | id, name, contact_email | |
| **Invitation** | id, rfx_id, vendor_id, sent_at, status (**AWAITING_RESPONSE** / RESPONDED) | SC-10 |
| **Response** | id, rfx_id, vendor_id, version, received_at, status (received/processing/processed/failed), coverage_count, **submissions [{inbox_message_id, received_at, kind (QUOTE/QUESTIONNAIRE/OTHER)}]** | DL-23: multiple messages from one vendor link to one Response |
| **ProcessingSet** | id, rfx_id, phase_b_status (pending/running/final), last_recompute_at, snapshot_hash | DL-9 |
| **Document** | id, response_id, filename, mime, sha256, storage_path, kind, parse_status, failure_reason | Stored unchanged |
| **EvidenceUnit** | id, document_id, kind, locator, text, ocr_confidence? | |
| **ExtractionRun** | id, response_id, model, prompt_version, path (TEXT/OCR/VISION), status, token_usage, created_at | One per path per run (DL-11) |
| **RawLineQuote** | id, run_id, vendor_line_ref, description_as_stated, item_code, value_as_stated, value, currency_as_stated, currency_source, unit_as_stated, unit_class, **unit_source**, inherited_from_evidence?, slabs [], quoted_spec, vendor_box_weight_g, applies_to_group?, image_read_value?, evidence [], model_flags [], raw_fingerprint | DL-11, DL-12 |
| **DocumentTerm** | id, run_id, type (…/TOOLING/ESCALATION/…), value, unit, scope, text, evidence | EXT-13 |
| **Reference** | id, run_id, type (PRIOR_UNSPECIFIED/OTHER), interpretation (AMBIGUOUS/CONFIRMED_PRICES/CONFIRMED_TERMS/CONFIRMED_BOTH/CONFIRMED_NEITHER), scope_prices (line ids), scope_terms (term types), text, evidence, candidates [{target, baseline_ref, value}], confirmation_resolution_id? | DL-20 |
| **BaselineTerm** | id, vendor_id (required), term_type, value, unit, period, source | DL-20 (reading B candidates) |
| **ClarificationPack** (was ClarificationRequest) | id, vendor_id, items [{kind (UNIT/READ/GST/FREIGHT/PRICE_CONFLICT/SLAB/EVIDENCE/REFERENCE/UNCOVERED_LINE), target, question_text (template), candidate_values?, sensitivity_rank}], generated_body, edited_body, status (draft/approved/in_outbox), created_by, approved_by/at | DL-20, DL-32. Never sent without buyer approval. |
| **QuestionAnswer** | id, run_id, question_id, answer_value, answer_text (verbatim), evidence, attachment_ids, doc_facts | Exposed read-only to the analyst (NLA-11) |
| **DocumentFact** | id, vendor_id, document_id, doc_type, standard?, certificate_number?, entity_name?, issue_date?, expiry_date?, validity_vs_rfx (derived), entity_match (derived), fact_status (EXTRACTED/VERIFIED/NOT_EXTRACTED), evidence [] | SC-02. Derived fields computed by code. |
| **LineMatch** | id, raw_line_quote_id, rfx_line_id?, confidence, rationale, compliance, spec_diffs [] | |
| **NormalizedQuote** | id, rfx_line_id, vendor_id, unit_price_inr_ex_gst (Decimal 4dp)?, unit_status, unit_reasons [], landed_inr_ex_gst?, landed_status, freight_basis, freight_inr_per_box?, **weight_source? (SKU_REFERENCE/VENDOR_STATED/ESTIMATED_CONSTANTS), weight_g?, constant_set_version**, flags [], trace [], assumption_ids [], fingerprint | One per line × vendor |
| **Resolution** | id, target (vendor, rfx_line, field) or reference_id, type (ACCEPT/CORRECT/MARK_MISSING/OVERRIDE/**REFERENCE_CONFIRMATION**), value?, choice?, reason/source_note, raw_fingerprint, state (active/stale), actor, at | §6.5, DL-20 |
| **Assumption** | id, type (FX_RATE/METHOD_CONSTANTS/BASELINE_REFERENCE/UNIT_INHERITED/FREIGHT_ESTIMATE), description, value, source, accepted_by?, accepted_at? | |
| **FxRate** | currency, rate_to_inr, as_of, source, set_by | DL-15 |
| **ConstantSet** | version, active (bool), constants [{key, value, unit, validation_status, source, validated_by?, validated_at?}], activated_by, activated_at | DL-18 |
| **BaselinePrice** | id, rfx_line_id, **vendor_id (required)**, unit_price_inr_ex_gst, freight_basis, **spec_signature**, period, **awarded**, source | DL-8 |
| **EligibilityResult** | vendor_id, question_id, state (PASS/FAIL/UNVERIFIED/**NOT_APPLICABLE**), reason, evidence, override + roll-ups per section and all_mandatory over **ALL-scope questions only**; line-scoped results gate cells on flagged lines (DL-29) | DL-3, DL-24, DL-29 |
| **ReviewItem** | id, target, reason_code, severity (blocking/advisory), suggested_resolution, money_at_risk, state | |
| **AuditEvent** | id, actor, at, action, target, before, after, reason | Append-only |
| **Scenario** | id, name, context (formal/exploratory), params (incl. basis freight_aware/unit/landed), needs_review_override_id?, result_snapshot (incl. per-line freight status, break-even, sensitivity, exposures), freight_dependency_ack_id?, cells_used_fingerprints, computed_at, stale | DL-16, DL-25, DL-28 |
| **AnalystSession / AnalystTurn** | id, messages (append-only, as returned by the API), tool_calls [], results [], answer {…}, grounding_check, label_lint | I9 |
| **AwardDecision** | id, scenario_id, memo, readiness_items, acknowledged_by/at, superseded | |
| **OutboxMessage / InboxMessage** | simulated email | |

**Reason codes (additions, PM review):** `GST_PER_RFX_BASIS` (ASSUMED), `REFERENCE_WEIGHT` (ASSUMED); line flags `FREIGHT_DEPENDENT`, `FREIGHT_UNKNOWN_ALL`, `DECISION_SENSITIVE`.

**Reason codes**
- *Blocking → UNRESOLVED:* the list in §6.2.
- *Advisory → NEEDS_REVIEW:* `OUTLIER`, `ARITHMETIC_MISMATCH`, `WEIGHT_MISMATCH`, `WEIGHT_ESTIMATED`.
- *Non-convertible:* `MISSING_CONSTRUCTION_INPUT`, `ITEM_TYPE_NOT_WEIGHT_COMPUTABLE`, `FREIGHT_UNKNOWN`.
- *Eligibility:* `ELIGIBILITY_UNVERIFIED`.
- *Other:* `FREIGHT_ESTIMATE_PENDING`.

---

## 8. AI requirements

### 8.1 Where AI is used, and where it isn't
| Use | AI? |
|---|---|
| RFx drafting and clarifying questions | Yes |
| Reading text-native documents; structuring OCR text; **separate** vision reading of images | Yes |
| Unit-string interpretation, including context inheritance with evidence | Yes (checked by deterministic rules) |
| Line-match proposals | Yes |
| Questionnaire answers and document facts | Yes |
| Analyst planning, tool choice, narrative | Yes |
| Memo rationale prose; AI clarification drafts for generic items (P1) | Yes |
| Clarification request for an ambiguous reference (DL-20) | **No**: a template over structured candidates |
| Conversions, statuses, checks, eligibility states, rankings, totals, savings, chart data | **No** |

### 8.2 AI behavioural requirements
| ID | Requirement |
|---|---|
| AI-1 | Schema-valid structured output. Nullable fields. "Not found" is preferred to a guess. |
| AI-2 | Evidence ids + a verbatim quote on every value |
| AI-3 | Record values and units as stated. Never convert. |
| AI-4 | Raise flags rather than guess |
| AI-5 | No dataset vendor names, SKU codes, prices or answers in prompts or few-shot examples |
| AI-6 | Analyst: a bounded loop (≤ 8 tool calls), a fixed read-only tool set |
| AI-7 | Grounding check on every narrative number |
| AI-8 | The co-pilot outputs schema-valid patches only. It can't approve or send. |
| AI-9 | Every AI call is logged |
| AI-10 | Failure, timeout or refusal → the stage is `FAILED` with retry. Nothing is half-applied. |
| AI-11 | Quality is measured against ground truth the running app can't access (I7) |
| AI-12 | **Eligibility label lint** on analyst and memo text. A fail-family word near a vendor whose scoped state ≠ FAIL → regenerate once with appended feedback. If it still fails, a code-generated correction note is shown ("Correction: V3 is Unverified, not failed — reason"). (I2) |
| AI-13 | **Conversation integrity (I9):** analyst and co-pilot histories are **append-only**. Full response content (including thinking blocks) is passed back unchanged. Transport retries resend the identical request body. Grounding/lint regeneration **appends** a feedback message after the previous answer; it never edits or removes earlier turns. A turn that fails permanently is recorded as failed and **not** appended, so the conversation continues from the last successful turn. |
| AI-14 | The vision extraction call receives only the image + RFx context, never OCR output (DL-11) |
| AI-15 | Extraction is **not** expected to be deterministic. Determinism is guaranteed from stored raw facts onward (§10 NF-5). |
| AI-16 | **Vendor-document content is data, not instructions.** Evidence snippets shown to the analyst (NLA-11) and to extraction calls are marked as untrusted vendor content. Instructions inside them are ignored, and snippets are length-capped. (SC-02) |
| AI-17 | **Co-pilot over the brief pack:** patches cite brief-pack evidence (RFX-9). The co-pilot never sees the canonical spec, so conformance is a genuine check, not a copy. (SC-04) |

### 8.3 No agents for their own sake
Ingestion is a fixed, code-controlled pipeline. The only loop where the model chooses its next step is the analyst. It is bounded, read-only, grounded, linted, and steered to `run_scenario` for award-type questions (NLA-10).

---

## 9. Edge cases (requirements view)

| # | Case | Required behaviour | FRs |
|---|---|---|---|
| E-01 | Angled photo | Correction + **independent** OCR and vision reads. Disagreement or single-source → UNRESOLVED. Max status EXTRACTED. | EXT-7, DL-11 |
| E-02 | 27/30 lines (V3) | 3 × MISSING, coverage shown, listed in answers | MAT-4 |
| E-03 | Vendor quoting in USD (V2, whole response, DL-15) | Original USD kept and shown. FX at a disclosed, editable rate and date. ASSUMED (FX_RATE). Global recompute on change. | NRM-4 |
| E-04 | Per box vs per 100 | Stated → convert. Unlabelled/suspect → UNRESOLVED with a suggestion, excluded until resolved. | EXT-5, VAL-3 |
| E-05 | Footnote discount (V2) | DocumentTerm in scope, applied, traced | EXT-6, NRM-7 |
| E-06 | Prose commercials (V3) | Terms with sentence evidence | EXT-3/4 |
| E-07 | Excel ignores template (V1) | Spec-based matching. Slabs (EXT-14/NRM-10) and tooling (EXT-13) handled. | MAT-1 |
| E-08 | "₹42/kg for the 5-ply, 38 for the 3-ply, rest same as last year, freight extra" (V5) | 42 stated, 38 unit inherited → ASSUMED (UNIT_INHERITED). Group expansion by ply. Conversion per the §5.2 hierarchy: reference weight → CONVERTED; no reference weight on a complete RSC → NEEDS_REVIEW (WEIGHT_ESTIMATED), excluded from the formal award until reviewed; partitions and die-cuts without blank or reference weight → NOT_CONVERTIBLE. "Rest": ambiguous (DL-20). Both readings kept as UNRESOLVED (REFERENCE_AMBIGUOUS) with DL-8 candidates, plus a clarification request. Applied only after confirmation. Freight UNKNOWN; last year's freight never carried forward. | EXT-5/8/9, NRM-3/5/8 |
| E-09 | VP split question | `run_scenario`, quality scope, strict. Failed and Unverified listed separately. Savings per §5.9. Uncovered lines listed. | AWD-1/2, ELG-3 |
| E-10 | Alternate spec (V2) | ALTERNATE flag, excluded by default | MAT-3, AWD-5 |
| E-11 | Same item priced twice | UNRESOLVED (PRICE_CONFLICT) | VAL-2 |
| E-12 | Tiered pricing (V1) | Slab by annual qty (P0) | NRM-10 |
| E-13 | GST unclear | UNRESOLVED (GST_UNCLEAR) | NRM-6 |
| E-14 | Escalation clause (V2) | Shown as a risk | EXT-6, AWD-4 |
| E-15 | Claim without proof / expired cert (V3) | Unverified, never failed | ELG-1, ELG-6 |
| E-16 | Cert in another entity's name (V4) | Question-level Unverified | §5.7 |
| E-17 | Revised quote | P2. Not in the dataset. | EXT-12 |
| E-18 | Corrupt file | FAILED + reason | EXT-10 |
| E-19 | Question outside the data | Says so | NLA-7 |
| E-20 | AI failure | FAILED, retry, no partial merge, conversation intact | AI-10, AI-13 |
| E-21 | Outlier | NEEDS_REVIEW (OUTLIER): excluded from formal awards by default, shown with a warning in exploratory views (DL-16) | VAL-3, AWD-1 |
| E-22 | ₹/kg on an incompatible item (partition / die-cut without blank) with no reference or vendor weight | NOT_CONVERTIBLE, reason named | NRM-3 |
| E-23 | Vendor weight vs reference weight beyond tolerance | NEEDS_REVIEW (WEIGHT_MISMATCH), reference weight used | NRM-3 |
| E-31 | Live co-pilot draft differs from the canonical spec | Conformance lists the differences. Fix by chat or edit. Prepared responses refused until it conforms. Labelled seeded fallback as the last resort. | RFX-10, DL-19 |
| E-32 | Analyst asked about a document fact that wasn't extracted or doesn't exist | "Not in the data". Never inferred. | NLA-13 |
| E-30 | ₹/kg on a line with no reference or vendor weight, construction complete | NEEDS_REVIEW (WEIGHT_ESTIMATED). Constants shown as UNVALIDATED. Excluded from the formal award until reviewed. | NRM-3, DL-16, DL-18 |
| E-24 | Mixed freight bases | Badges. Analyst mentions it. Landed basis excludes UNKNOWN. | §5.4 |
| E-25 | New unseen file | Same pipeline + global recompute | J8 |
| E-26 | "Same as last year", baseline only for another vendor | UNRESOLVED (BASELINE_NOT_FOR_VENDOR). Never a candidate. | DL-8 |
| E-27 | "Same as last year", spec changed since last year | UNRESOLVED (BASELINE_SPEC_CHANGED) | DL-8 |
| E-33 | "Rest same as last year" could mean prices or terms | Both readings kept, UNRESOLVED (REFERENCE_AMBIGUOUS), candidates shown, clarification request generated, applied only after an audited confirmation | DL-20, EXT-9, NRM-8 |
| E-34 | A vendor's response hasn't arrived | "Awaiting response". No cells, no zero, not MISSING. Excluded and listed. Late arrival → global recompute. | DIS-2, SC-10 |
| E-35 | A cheaper unit price with unknown freight vs a delivered price | FREIGHT_DEPENDENT with break-even; readiness acknowledgement | DL-25 |
| E-36 | Vendor silent on GST | RFx basis applied as ASSUMED; no basis → UNRESOLVED | DL-26 |
| E-37 | An uncertain value could flip a line winner | DECISION_SENSITIVE with quantified impact; first in the queue and the clarification pack | DL-28, DL-32 |
| E-28 | Commercial Fail but Quality Pass (V5) | Eligible under the quality scope, excluded under all_mandatory. Analyst states the scope. | ELG-2/3 |
| E-29 | Correction changes peers | Global recompute. Accepted cells not downgraded. | VAL-5 |

---

## 10. Non-functional requirements

| ID | Requirement | Target |
|---|---|---|
| NF-1 | Phase A per response | < 90 s (photo: the two reads run in parallel) |
| NF-2 | Full demo ingestion (Phase A in parallel + Phase B) | < 4 min |
| NF-3 | Analyst answer | < 30 s typical |
| NF-4 | Global recompute | < 2 s |
| NF-5 | **Determinism boundary (I6):** from stored raw extraction facts onward (normalisation, Phase B, statuses, eligibility, scenarios, savings, charts, exports) the same inputs give byte-identical outputs, whatever the processing order. AI extraction and analyst *wording* are not deterministic. An analyst answer is reproducible **for the same tool calls** (stored in Show work). | 100% |
| NF-6 | Data stays local except model API calls | — |
| NF-7 | Setup: one command plus a preflight check (`make doctor`) for system dependencies (Tesseract) | — |
| NF-8 | Demo resilience: stored results from the real pipeline. A **P0 basic re-run** (EXT-11) is available live. | — |
| NF-9 | **Ground-truth isolation (I7):** the running app can't open the answer key or generator truth files (architecture §14) | enforced at runtime + by tests |

---

## 11. Demo dataset requirements (DL-13, I3)

Every planted behaviour depends only on P0 capabilities.

| Item | Spec |
|---|---|
| RFx | 30 lines: 18 RSC (3/5-ply plus 4 × 7-ply), 6 DIE_CUT (3 with `blank_size_mm`, 3 without, including the 2 printed mailers), 4 PARTITION sets, 2 PAD (with blank size). All 3- or 5-ply except the 4 × 7-ply RSC. Annual value ≈ ₹4 crore. **Documented reference unit weights (DL-18)** for **21 SKUs** (item-master source): **16 RSC** (all RSC except 2 of V5's group-priced 3/5-ply RSC), the **3 die-cuts** with blank size and the **2 pads**. **3 RSC lines are `food_contact`.** **No line has `requires_fsc`, and there is no FSC question** (DL-29). The RFx `response_basis.gst_treatment` = "prices exclusive of GST" (DL-26). **No reference weight** for the 4 partitions or the 3 die-cuts without blank size. |
| Questionnaire | **Quality (5):** ISO 9001 certificate; BCT/ECT test report; **food-grade compliance declaration** (applicability: food_contact lines, line-level gating, DL-29); monthly capacity ≥ 250 t; in-house printing. **No FSC question** in the primary RFx (an FSC-required variant is a test fixture only). **Commercial (3):** payment terms 60 days accepted; lead time ≤ 15 days; GST registration. Each question has a stable `requirement_key`. |
| **Buyer brief pack (DL-19, SC-04)** | Inputs to the live co-pilot, in `DATA_ROOT/seed/brief_pack/`: (1) **item master** xlsx with the 30 SKUs (codes, descriptions, item type, dims, ply, flute, layer GSMs, BF, printing, annual qty, reference weights + source ids); (2) **quality checklist** (5 requirements with keys and pass rules); (3) **commercial policy** note (payment, lead time, GST, response basis). These are realistic buyer inputs, **not** answers. A few facts are deliberately left out (delivery location, internal-dimension convention, validity) so the co-pilot has to ask. |
| **Canonical RFx specification (DL-19)** | `DATA_ROOT/seed/canonical_rfx.json`: the RFx that the brief pack + runbook answers should produce. Content-hashed. Used for the conformance check and as the labelled fallback. **All five vendor responses are authored against its SKU codes, descriptions and question requirement keys**, so matching against a conforming live RFx is reliable. |
| **Attached documents with extractable facts (SC-02)** | Every certificate and test report carries a clearly printed type, standard, certificate number, legal entity name, and issue/expiry dates. Planted: V3's ISO 9001 **expired** before the RFx date; V4's certificate is in **another entity's name**; V1 provides **no FSC certificate**. There is no FSC question in the primary RFx (DL-29), so this affects no eligibility result; it is used for the "not in the data" check. V1, V2 and V5 quote the 3 food-contact lines and provide valid food-grade declarations; V2's BCT report is valid. |
| **V1, Excel (own layout)** | Ignores the template. **Slabs** (EXT-14/NRM-10). **Tooling row** (EXT-13). Delivered (INCLUDED). Quotes 28/30: **not the 2 printed die-cut mailers**. Quality **Pass**, Commercial Pass. |
| **V2, PDF letterhead, entire quote in USD (DL-15, DL-30)** | A **domestic Indian converter** with import-linked kraft pricing. It quotes every line, the freight and the terms in USD, and states "invoiced in INR at the RBI reference rate on the invoice date". Original values preserved. Footnote on the price page: "\*5% trade discount on all items" (EDGE-02). 2 lower-GSM **alternates**, on exactly the 2 die-cut mailers V1 skips. Freight STATED per box. Escalation clause. Quotes 26/30 (no partitions). Quality **Pass**. |
| **V3, Word** | Commercials in prose (EDGE-03): payment terms, freight basis, price validity, lead time and an escalation condition, each in a separate sentence of running paragraphs, with no table. **27/30 lines** (the 3 missing lines are fixed by number in ground truth). ISO certificate expired → Quality **Unverified**. |
| **V4, angled phone photo** | **Primary fixture: a genuine phone photograph** of the printed rate card (DL-21, `12_phone_photo_capture_kit.md`). The synthetic warp is kept for additional tests. Prices **per 100** (EDGE-09): a "Rate per 100 pcs" column header for most lines, plus 2 rows with the unit missing whose values are ~100× the per-box peer median → UNIT_SUSPECT. At least 3 lines overlap with per-box quotes from V1/V5 for direct comparison. Hard digits (planted 3/8, 1/7 ambiguities). Capacity "150 t" → Quality **Fail**. Certificate in another entity's name → question-level Unverified. |
| **V5, terse email + separate questionnaire submission (DL-23)** | **Message 1:** the email body is exactly the assignment's sentence, byte-identical, with no attachments. **Message 2 (separate submission, same vendor and RFx):** the completed questionnaire plus certificates (ISO 9001 valid, BCT report valid, food-grade declaration valid). It answers payment terms "No". This is the evidence for Quality **Pass** and Commercial **Fail**. It contains no prices and doesn't state the reading-B term types. From message 1: The 5-ply and 3-ply groups cover the RSC, die-cut, pad and partition lines of those plies, so the §5.2 hierarchy is visible: lines with reference weights → CONVERTED; the 2 RSC without reference weight → NEEDS_REVIEW (WEIGHT_ESTIMATED); die-cut without blank and partitions → NOT_CONVERTIBLE. "Rest" (DL-20, both readings): **reading A** = the 4 **7-ply** RSC lines: 2 with V5's own same-spec baseline (→ candidate, UNRESOLVED (REFERENCE_AMBIGUOUS) until confirmed), 1 with V5's baseline under an older spec (→ BASELINE_SPEC_CHANGED), 1 with a baseline only for another vendor (→ BASELINE_NOT_FOR_VENDOR). Payment terms "No" → Commercial **Fail**, Quality **Pass**. |
| Baseline | `awarded` rows for 25/30 lines (last year's incumbents: V1, V5 and one vendor not invited this year). Non-awarded rows for V5 where needed. All rows have a vendor and a `spec_signature`. **`BaselineTerm` rows for V5** (last year's payment, validity, lead time and delivery terms) for **reading B** of "rest same as last year": at least 2 term types that V5 does **not** state this year. |
| Ground truth | True values, expected statuses/reasons, eligibility per question and section, expected matches, expected scenario outputs, **expected document facts**, **expected conformance result**. Stored in the isolated eval workspace (NF-9). |
| **Negative test fixtures (EVAL_ROOT only, not part of the demo)** | Variants used by the named edge-case tests (implementation plan §3a): **an FSC-required RFx variant** (one `requires_fsc` line + FSC question); **a food-grade line-level variant** (an eligible vendor without a food-grade declaration); **an RFx with no GST basis**; **item-master header variants** (renamed/reordered/merged); **freight-estimate variant**; V2 footnote scoped to "5-ply only"; V2 without a footnote; V3 with a conditional term and with a term removed; V4 genuine per-box price that is high but plausible; a non-conforming RFx draft. |
| **Realism review (DL-22)** | Completed `11_dataset_realism_review.md` by a procurement-literate person, with feedback and corrections logged. Required for the M1 exit. |
| **Arrival order (SC-10)** | The runbook delivers responses one at a time (V5, V1, V3, V4, V2). Ground truth includes the expected comparison state after each arrival subset used in tests. |

**Resulting headline behaviour (quality scope, strict):**
- Eligible: **V1, V2, V5** (3 vendors, I3).
- Excluded: V3 Unverified, V4 Failed.
- The 2 die-cut mailers are **uncovered** like-for-like: V1 didn't quote them, V2 quoted only alternates, V5's are NOT_CONVERTIBLE. They become covered if alternates are included (DL-6 demo).
- V5's 4 7-ply lines are UNRESOLVED (REFERENCE_AMBIGUOUS or baseline reasons) until the buyer confirms a reading (DL-20). They're excluded from the formal award meanwhile, and the clarification request is shown in the demo.
- V5's 2 estimated-weight RSC lines are excluded from the formal award by default (DL-16).
- V5 is silent on GST and freight: its cells are ASSUMED (GST_PER_RFX_BASIS). Where V5 wins only on unit price against V1's delivered or V2's stated-freight landed cost, the line is FREIGHT_DEPENDENT with a break-even shown (DL-25).
- At least 2 lines are DECISION_SENSITIVE (e.g. a V4 READ_DISAGREEMENT whose other reading would win, a V5 reference candidate) (DL-28). The readiness check lists them. Reviewing them (or an audited override) brings them in.
- Changing the FX rate by a plausible amount flips at least one line between V2 and V1/V5 (E-03).

---

## 12. Prioritisation (DL-13)

### 12.1 P0
- **Primary RFx drafted live by the co-pilot from the brief pack, with conformance check and provenance (DL-19, RFX-9…11)**; canonical spec as labelled fallback; sandbox (DL-17); co-pilot edits with eval.
- Simulated send/inbox + status board; upload.
- All five format extractions, with independent photo reads.
- Evidence verification; unit inheritance with evidence.
- Matching + ALTERNATE.
- Normalisation, incl. DL-1/2/8/12/15/18, **slabs, tooling separation**, weight-source hierarchy, **versioned constant set**, Decimal money.
- Phase A/B processing + global recompute.
- Canonical statuses.
- Review queue + overrides + carry-forward.
- **Basic re-run.**
- Comparison + provenance.
- Eligibility (sections, 3-state, label control).
- Baseline + savings rules.
- Analyst (tools, `run_scenario` steering, grounding incl. dates/identifiers, label lint, caveats incl. coverage disclosure, charts, export, **read-only document facts and questionnaire answers with evidence, NLA-11…13**).
- Scenario engine (no cap) with formal/exploratory context and the audited NEEDS_REVIEW override (DL-16).
- Award readiness + memo + exports + audit.
- **PM-review P0/P1 adoptions:** freight-aware award comparison with break-even (DL-25); GST silence rule (DL-26); deterministic item-master import with AI mapping (DL-27); decision sensitivity (DL-28); line-level food-grade, no FSC question (DL-29); V2 FX exposure (DL-30); reference-weight ASSUMED + billed-weight caveat (DL-31); deterministic clarification pack (DL-32).
- **Ambiguous-reference handling with both readings, template clarification request and audited confirmation (DL-20).**
- **"Awaiting response" vendor state (SC-10). Documents openable from the comparison (SC-11).**

### 12.2 P1 (no demo or dataset dependency)
Optional Excel template · J9b AI-drafted free-text clarification emails (the deterministic clarification pack is P0, DL-32) · bulk accept · tooling amortisation in the annual-cost view · **vendor share cap** · save an answer as a scenario from the analyst · analyst ask-back · run-history browser · FX sensitivity tool.

### 12.3 P2
Revised-quote versioning · PDF memo styling.

### 12.4 Never cut
Evidence/provenance, the canonical status model, DL-1/2/3/8/9/11/12/14–32 behaviour, the grounding check and label lint, the audit log, ground-truth isolation.

### 12.5 Timeline policy (FD-7)
**FD-7 rev. 4:** 29.0 days of estimated effort for one builder (20.5 P0 implementation + 6.5 testing, evaluation & integration + 2.0 demo prep; Plan v1.7 §2), re-sequenced around a vertical slice at day ~6.5 with checkpoints at days 10, ~15 and ~20. Not a calendar deadline or contract. P1 (3.25 d) outside the committed schedule. Extraction tuning, integration testing, independent evaluation and unscripted demo prep are not reduced. O3/X1–X4 rejected. O1/O2 optional only without loss of functionality. §12.4 items are never traded for time.

---

## 13. Scope
**Out of scope [R]:** real SMTP/IMAP · vendor portal · negotiation · ERP/PO · multi-user/roles · multiple categories · live FX or paper-index feeds · vendor risk scoring · handwriting · mobile layout · auth.

---

## 14. Decision log (product)
| # | Decision | Why |
|---|---|---|
| D1 | Ex-GST ₹/box default, freight separate | Like-for-like; guesses never look like facts (DL-2) |
| D2 | Weight conversion only for supported types with complete inputs | Plausible-looking but invented precision is worse than a gap (DL-1, DL-12) |
| D3 | Three-state eligibility with Quality/Commercial sections | Fair to vendors; the VP's question means quality (DL-3, I2) |
| D4 | Unit anomalies are UNRESOLVED (excluded), never auto-fixed | A wrong 100× correction is the worst failure (B3) |
| D5 | Missing lines excluded and disclosed | Imputing a price is fabrication |
| D6 | Alternates excluded by default | Protects quality (DL-6) |
| D7 | AI extracts, code calculates | Determinism (NF-5) |
| D8 | Image values capped at EXTRACTED; independent reads | The riskiest input (DL-11) |
| D9 | One bounded analyst loop; fixed pipeline elsewhere | Autonomy only where the problem is open-ended |
| D10 | Stored results + P0 re-run + optional upload | Reliable demo without faking (DL-4) |
| D11 | Overrides audited, sticky, carried forward only if the source is unchanged | Buyers know things documents don't, but a changed source must be looked at again (DL-7, I6) |
| D12 | Baseline references only the same vendor + same spec | "Same as last year" means *their* last year (DL-8) |
| D13 | Two-phase processing + global recompute | Reproducible statuses (DL-9) |
| D14 | Inherited units allowed but ASSUMED | Matches how buyers read the email, and discloses the inference (DL-12) |
| D15 | Vendor cap is P1 and out of the demo | No P0 path depends on it (DL-13) |
| D16 | Quality section alone decides "cleared the quality questionnaire" | Matches the VP's words. Commercial terms are a separate concern (DL-14). |
| D17 | V2 quotes entirely in USD | The assignment names "the one who quoted in USD" (DL-15) |
| D18 | NEEDS_REVIEW excluded from formal awards by default, audited override | A ₹4 cr award should rest on reviewed numbers (DL-16) |
| D19 | Reference weights first, constants versioned and UNVALIDATED | Documented data beats approximations. Approximations must not pose as facts. (DL-18) |
| D20 | The primary RFx is drafted live and gated by conformance to the canonical spec | One continuous flow with a real co-pilot, while the prepared responses still match (DL-19, SOT REQ-03) |
| D21 | The analyst sees structured facts and cited snippets, never full documents | "Over the whole comparison" without unrestricted document access or invented facts (SOT FN-11, NLA-11…13) |
| D22 | Effort estimate is 29.0 d for one builder (FD-7 rev. 4; rev. 3 = 25.75 d), with protected testing, integration and rehearsal allocations | Trust work (evaluation, tuning, unscripted rehearsal) is what the assignment scores (SOT EVAL-02/03, DEL-01). It must not be squeezed to hit a number. |
| D23 | "Rest same as last year": both readings kept, never assumed, confirmed by the buyer | The source text is genuinely ambiguous. Guessing either way could misprice or mis-term a ₹4 cr award (DL-20). |
| D24 | Real phone photo as the primary fixture; human realism review | Evidence must come from the real world, not from an AI checking itself (DL-21, DL-22) |
| D25 | An absent response is "Awaiting response", never zero or missing | Prices arrive over nine days. A partial comparison must stay honest (SOT EX-02). |
| D26 | V5's quote email stays the assignment's exact sentence; questionnaire evidence arrives separately | Fidelity to the source text without leaving V5 unable to qualify (DL-23) |
| D27 | Food-grade compliance is a line-scoped Quality question; vendors quoting no food-contact line get NOT_APPLICABLE, shown openly. FSC is not part of the primary RFx (DL-29). | A requirement that doesn't apply must not fail a vendor, and its non-applicability should still be visible (DL-24, as amended by DL-29) |
| D28 | Award comparisons are freight-aware with break-even; GST silence uses the disclosed RFx basis | A cheaper ex-works quote mustn't silently beat a delivered one, and tax mustn't be guessed (DL-25/26) |
| D29 | The item master is imported, not transcribed by the AI | 30 lines of numbers are a copying job; the AI adds value in mapping, gaps and edits (DL-27) |
| D30 | Show whether uncertainty matters (decision sensitivity) and ask vendors only what matters (clarification pack) | Buyers act on what could change the award (DL-28/32) |
| D31 | Food-grade gates lines; FSC is out; V2 FX and billed-weight exposure are disclosed | The quality rule matches the risk; currency and weight exposure aren't hidden (DL-29/30/31) |

## 15. Open product questions
All earlier open questions are closed by `08_final_product_decisions.md` (FD-1…FD-7, FD-7 at rev. 2). The one remaining non-blocking item: freight estimates are buyer-entered only (current scope). A suggested lane rate is out of scope.
