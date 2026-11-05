# Product Brief — "Kill the Quote Spreadsheet"
**Category:** Corrugated packaging · **Author role:** Principal PM · **Status:** v1.6 · PM review adoptions DL-25…DL-32 · **Source:** `docs/assignment.pdf`

> **Authority (v1.2):** `docs/02_PRD.md` is the source of truth. Where this brief and the PRD disagree, **the PRD wins**. Sections superseded by the PRD are marked *Superseded*. Every change made after the pre-build review is listed in `docs/06_fix_log.md`. The final product decisions are recorded in `docs/08_final_product_decisions.md`. **`docs/00_source_of_truth.md` is the canonical requirements reference** (root `CLAUDE.md`). The demo is specified in `docs/10_demo_runbook.md`.

---

## Decisions locked in v1.1

These were agreed after v1 and override anything below that conflicts with them. Each is a product decision **[R]**; the assignment does not dictate any of them.

| ID | Decision | Replaces / resolves |
|---|---|---|
| **DL-1** | **₹/kg → ₹/box conversion happens only when the board construction and weight inputs are sufficient.** That means either a vendor-stated box weight, or a complete RFx construction spec (dimensions, box style, ply, flute profile, GSM of every layer). If any input is missing, the line is marked *Not convertible* and the missing inputs are named. **The system never invents a missing input.** *(Amended by DL-18: weight-source hierarchy.)* | F-NRM-2, E-08(a) |
| **DL-2** | **Normalised ex-GST unit price and freight are kept separate.** Landed cost (= unit price + freight) is calculated **only** when freight is *known* (included in a delivered price, or stated by the vendor) or comes from an **explicitly disclosed estimate** that the buyer has accepted. Otherwise landed cost is shown as *Not calculable — freight unknown*. The default comparison basis is the normalised ex-GST unit price per box. | PD-1, PD-10, F-NRM-1, F-NRM-4, E-08(d) |
| **DL-3** | **Questionnaire eligibility has three states: Pass, Fail, Unverified.** Unverified (claimed without proof, unanswered, or unreadable proof) is excluded under *strict* eligibility but is **never labelled or reported as Fail**. | PD-8, E-15, open question 4 |
| **DL-4** | **Uploading new vendor files is supported** through the same real pipeline. An unseen-file upload is an **optional** part of the main demo, used only if the panel asks for it. | Open question 3 |
| **DL-5** | **Last year's prices are kept as a reference dataset** (used for savings and to resolve "same as last year"). | Open question 1 |
| **DL-6** | **Alternate specifications are excluded from like-for-like awards by default.** The buyer can include them explicitly, and that choice is recorded. | PD-6, open question 2 |
| **DL-7** | **Buyer overrides are allowed, and each one leaves an audit record** (original value, new value, who, when, reason). | F-REV-3, F-AWD-5 |

### Decisions added in v1.2 (pre-build review, `docs/05_prebuild_review.md`)

| ID | Decision | Resolves |
|---|---|---|
| **DL-8** | "Same as last year" resolves **only** against the **same vendor's** baseline row for the **same line with a matching specification**. Another vendor's historical price is never used. Otherwise the cell is *Unresolved*. **Historical freight terms are never carried forward.** If this year's freight is unknown, it is shown as unknown (FD-4). | B1, FD-4 |
| **DL-9** | Two-phase processing. Per-document extraction and per-cell normalisation run first. Peer-price and outlier checks run only after all responses are processed. Any correction triggers a global recompute. Human resolutions are sticky. | B2 |
| **DL-10** | One canonical status model (PRD §6): Verified, Extracted, Assumed, Needs review, Unresolved, Not convertible, Missing. Unresolved, Not convertible and Missing values **never** enter calculations. *Unverified* is an eligibility state only. | B3, I1 |
| **DL-11** | OCR and visual AI extraction of photos run **independently**. The vision call never sees OCR output. Disagreements, or values only one read found, need human review. | B4 |
| **DL-12** | An elliptical unit (the "38" in "₹42/kg for the 5-ply, 38 for the 3-ply") is inferred from the preceding clause, **recorded as an inference with evidence**, and marked *Assumed*. Weight conversion applies only to supported item types (RSC; die-cut and pads with a blank size) with complete inputs. Partitions are never weight-computed. | B5, I5 |
| **DL-13** | The demo dataset and demo script depend only on P0 capabilities that are implemented and tested. Optional features stay optional. | B6 |

### Final decisions locked in v1.3 (`docs/08_final_product_decisions.md`)

| ID | Decision | FD |
|---|---|---|
| **DL-14** | Only the **Quality** section decides whether a vendor "cleared the quality questionnaire". Commercial questions are evaluated and shown separately. | FD-1 |
| **DL-15** | **V2 quotes its entire response in USD**, which is the assignment's USD vendor. Original USD values are preserved. Conversion to INR uses a stated, editable FX rate and date. | FD-2 |
| **DL-16** | *Needs review* values are **excluded from formal award calculations by default**. The buyer can override this per scenario, with a warning and an audit record. Exploratory analysis can include them on request, labelled "Exploratory" with caveats. | FD-3 |
| **DL-17** | Live co-pilot drafting uses a separate **sandbox RFx**. The prepared five-vendor dataset is never changed. | FD-5 |
| **DL-18** | Engineering constants (flute take-up, joint allowance, tolerances, thresholds) are **configurable, versioned, and labelled "not validated"** until a packaging engineer validates them. ₹/kg → ₹/box uses, in order: the documented SKU reference unit weight; then a vendor-stated weight; then an estimate from constants (*Needs review*, never in a formal award without buyer review); otherwise *Not convertible* / *Unresolved*. The weight source and every step are kept. | FD-6 |

| ID | Post-audit decision (approved SC-04) | Source |
|---|---|---|
| **DL-19** | The **primary demo RFx is drafted live by the co-pilot** from a buyer brief pack plus conversational answers. It must pass a **conformance check** against the canonical RFx spec that the prepared vendor responses were written against. That one RFx then flows through responses, extraction, comparison, analysis and award. The sandbox (DL-17) stays for free-form drafting. The canonical spec is never changed and serves as the labelled fallback. | SOT REQ-03, FN-01 |
| **DL-20** | "Rest same as last year" may mean the remaining **prices** or the remaining **terms**. Both are kept, flagged *Unresolved*, and a clarification request is generated. Nothing historical is applied without buyer confirmation. | SOT EDGE-05c (SC-05) |
| **DL-21** | The V4 photo fixture is a **genuine phone photograph** of a printed rate card. The synthetic image is for extra tests only. Never AI-generated. | SOT EDGE-04/06 (SC-08) |
| **DL-22** | Dataset realism is signed off by a **procurement-literate human**. AI self-review doesn't count. | SOT REQ-05 (SC-07) |
| **DL-25…DL-32** | Principal PM review adoptions: freight-aware award with break-even freight (DL-25); GST silence uses the disclosed RFx basis (DL-26); deterministic item-master import with AI column mapping (DL-27); decision sensitivity (DL-28); line-level food-grade, no FSC question (DL-29); V2 as a domestic supplier with USD-linked prices invoiced in INR, FX exposure disclosed (DL-30); reference-weight conversions ASSUMED with a billed-weight caveat (DL-31); deterministic clarification pack (DL-32). Details in PRD §0.1. | PM review |

Timeline (FD-7): **FD-7 rev. 4:** 29.0 days of estimated effort for one builder (20.5 P0 implementation + 6.5 testing, evaluation & integration + 2.0 demo prep), re-sequenced around a vertical slice at day ~6.5. Not a deadline or contract. P1 (3.25 d) outside the schedule. Protected testing and rehearsal allocations kept.

The detailed requirements, acceptance criteria and data model for these decisions are in `docs/02_PRD.md` (v1.1).

---

## 0. How to read this document

Every statement is tagged so the hiring team can see what came from them and what came from us.

| Tag | Meaning |
|---|---|
| **[A]** | **Assignment requirement.** Stated in the brief. Quotes are verbatim. |
| **[A-i]** | **Assignment, implied.** Not stated as a requirement, but clearly signalled (e.g. the "ugly edges" list). |
| **[R]** | **Our recommendation.** A product choice we're making. It could be argued the other way. |
| **[H]** | **Hypothesis.** Something we believe and plan to test or argue in the one-page note. |

Requirement IDs (`A-01`…) are used in the traceability matrix in §10.

---

## 1. Core problem and user personas

### 1.1 The problem in one sentence
Turning five differently shaped vendor quotes into one comparison you can trust takes days of manual retyping. Every follow-up question from leadership restarts the work by hand. **[A]**

### 1.2 Why it's worse in corrugated packaging **[R]**
We chose corrugated because its quotes are hard to compare in ways that are specific to the category:

- **The unit of price varies.** Vendors quote ₹/kg, ₹/box, ₹/100 pcs or ₹/1000 pcs. A ₹/kg quote only becomes ₹/box once you know the box weight, and that comes from the dimensions, ply and paper GSM. A plain unit conversion can't do it, so this is real domain normalisation.
- **Specs drift.** Vendors often quote a slightly different spec than the one asked for, such as 140 GSM instead of 150, B-flute instead of C, or a lower bursting factor (BF). A lower price can just mean a weaker box.
- **One-time charges hide.** Printing plates and cutting dies are often charged separately, quoted once and left out of the unit price.
- **Commercial terms move the landed cost.** Freight (ex-works or delivered), GST shown inclusive or exclusive, MOQ, and price validity tied to kraft paper index movements.
- **Quality matters a lot.** BCT/ECT strength, Cobb (moisture) value, food-grade or FSC certification, and capacity all decide whether the cheapest vendor can be used at all. That is why the VP's question filters on the quality questionnaire.

### 1.3 Personas

| Persona | Role in flow | Job to be done | What they fear | Tag |
|---|---|---|---|---|
| **Priya — Category Buyer, Packaging** (primary) | Creates RFx, chases vendors, builds comparison, recommends award | "Get from 5 messy quotes to a defensible recommendation without retyping anything." | Making a ₹4 cr award on a number that was misread or mis-converted | [A] persona implied by brief; name/details [R] |
| **Rahul — VP / Head of Procurement** (approver) | Asks "what-if" questions, approves award | "Answer my question in minutes, and show me why I should believe it." | Signing off on a recommendation he can't audit | [A] ("the VP asks one question") |
| **Vendor sales rep** (secondary, external) | Responds to RFx in whatever format they want | "Send my quote the way I always do." | Being forced into a portal/template | [A] ("nobody is forced into your template") |
| **Quality / Plant packaging engineer** (tertiary) | Defines spec and pass criteria for the questionnaire | "Make sure nobody wins on a box that collapses in the monsoon." | Spec deviations hidden behind price | [R] |

---

## 2. Explicit requirements (from the assignment)

| ID | Requirement | Source (verbatim where possible) |
|---|---|---|
| A-01 | Buyer creates an RFx **conversationally** with an AI co-pilot | "A buyer *talks* an RFx into existence with an AI co-pilot" |
| A-02 | RFx contains **scope, line items, questionnaire, terms** | same sentence |
| A-03 | RFx is **sent to vendors** over a channel we choose | "It goes out to vendors over a channel you choose" |
| A-04 | Vendors respond **in any format**, no forced template | "Vendors reply however they like; nobody is forced into your template" |
| A-05 | System **reads every response regardless of shape**, including Excel (non-template), PDF on letterhead, Word with prose commercials, photo of a printed rate card taken at an angle, and a free-text email | Opening narrative + "whatever shape it arrives in" |
| A-06 | All responses land in a **single side-by-side comparison** | "lands them all in a single side-by-side comparison" |
| A-07 | Comparison is **normalised: same lines, same units, same currency** | "same lines, same units, same currency" |
| A-08 | **Questionnaire answers and attached docs** appear alongside the numbers | "with questionnaire answers and attached docs sitting alongside the numbers" |
| A-09 | Buyer queries the whole comparison in **natural language** | "Natural language, over the whole comparison" |
| A-10 | Answers can be **text, tables, charts, exports** | "Text answers, tables, charts, exports" |
| A-11 | Analysis must be **real, on real extracted data** | "Real analysis on real extracted data" |
| A-12 | Flow ends in a **defensible award decision** | "all the way to a defensible award decision" |
| A-13 | Demo scale: **5 vendors, 30 line items, a questionnaire, attached documents** | "five vendors, thirty line items, a questionnaire, attached documents" |
| A-14 | **Fabricated, realistic dataset** | "Fabricate a dataset a procurement person would nod at" |
| A-15 | Plumbing may be stubbed; **AI loops must be real**: no faked extraction, no faked reasoning, no hardcoded demo answers | "One rule: stub the plumbing, but the AI loops must be real…" |
| A-16 | Handle the ugly edges: **angled photo; partial quote (27/30 lines); USD quote; unit ambiguity ("per box" vs "per 100 pcs")** | "What we're actually looking at" |
| A-17 | **Show the buyer** what the system does **when it isn't sure** | "what does it *show the buyer* — when it isn't sure?" |
| A-18 | **Earn trust** for a ₹4 crore decision | "Would a buyer with ₹4 crore on the line act on what's on your screen?" |
| A-19 | Show **judgment and taste**, and be able to **explain why** | "We want to see how you made them, and whether you can say why" |
| A-20 | Must support the VP-style **compound what-if**: line-level split award, filtered by questionnaire outcome | "what if we split it, cheapest per line, but only among vendors who cleared the quality questionnaire?" |
| A-21 | Deliverable: **working prototype**, ready for a **live demo the panel drives** | Deliverable section |
| A-22 | Deliverable: **recorded walkthrough of the analyst conversation**, with questions chosen by us | Deliverable section |
| A-23 | Deliverable: **one-page note** on decisions and **what was deliberately left out** | Deliverable section |
| A-24 | Optional: say so if **"the interesting problem was actually somewhere else"** | Closing paragraph |
| A-25 | We choose framework, models, email path, storage, UI, personas, industry, data, export formats, guardrails | "Total liberty" |

> Note on A-05: the five response shapes are written as narrative, not as a list of requirements. We treat all five as **must-handle** because they are the obvious demo script the panel will compare us against. **[A-i]**

---

## 3. Implicit expectations of the hiring team **[A-i]**

What we think the panel is actually scoring, read from what the brief stresses and what it leaves out.

1. **The happy path doesn't count.** "Everyone can build the happy path." Points come from how the system degrades: partial data, low confidence, contradictions.
2. **Uncertainty is a product surface, not just a model property.** The phrase "what does it *show the buyer*" means they want to see the UX for uncertainty, not just a confidence number in a log.
3. **The live demo will go off script.** "A live demo we'll drive with you" means they will ask questions we didn't prepare. The NL analyst has to generalise, which is why A-15 forbids hardcoding.
4. **Domain credibility.** "A dataset a procurement person would nod at" means real spec attributes, plausible price spreads, and realistic commercial terms. Toy data will be noticed.
5. **PM judgment over engineering breadth.** It's a PM role. They want to see scope cuts, explicit trade-offs and a clear "why". A smaller product with sharp decisions beats a sprawling one.
6. **Auditability of the award.** "Defensible" means someone other than the buyer, such as the VP, audit or finance, can trace each number in the recommendation back to a vendor's own document.
7. **Honest reporting.** The one-pager should name what doesn't work as well as what does. Hiding limitations looks worse than admitting them.
8. **Problem reframing is welcome.** A-24 invites us to say where the real problem is (see §11).
9. **Indian enterprise context.** ₹, crore, ₹/kg pricing, GST and freight conventions should be native to the product, not converted from a US template.

---

## 4. End-to-end user workflow

```
 ① Draft RFx ──▶ ② Send ──▶ ③ Ingest responses ──▶ ④ Extract & normalise ──▶ ⑤ Review exceptions
   (co-pilot)    (email)     (any format)            (to RFx line + unit)      (buyer resolves)
                                                                                     │
 ⑨ Export & audit ◀── ⑧ Award decision ◀── ⑦ Ask & analyse (NL) ◀── ⑥ Comparison workspace
```

| # | Stage | Actor | What happens | Output | Tag |
|---|---|---|---|---|---|
| 1 | **Draft RFx** | Buyer + co-pilot | Buyer describes need in plain language ("30 SKUs of RSC boxes for our Pune plant, mostly 3- and 5-ply…"). Co-pilot asks follow-up questions, proposes line items with full specs, builds the questionnaire, proposes commercial terms and the **response basis** (unit, currency, Incoterm, GST treatment). Buyer edits and approves. | Structured RFx: scope, 30 lines, questionnaire, terms | [A] flow; co-pilot behaviour [R] |
| 2 | **Send** | Buyer | Pick 5 vendors and send. Each vendor gets an email with the RFx summary, an *optional* Excel template and attachments. | Sent log per vendor | [A] channel choice; email [R] |
| 3 | **Ingest** | System | Responses come in as email body and/or attachments (xlsx, pdf, docx, jpg). Each one is matched to the vendor and RFx. | Raw response record with original files kept | [A] |
| 4 | **Extract & normalise** | System (AI) | Pull out prices, units, specs, terms and questionnaire answers. Map each vendor line to an RFx line. Convert units (incl. ₹/kg → ₹/box via computed box weight) and currency. Every value carries a confidence score and a link to its source. | Normalised comparison data + exceptions list | [A] |
| 5 | **Review exceptions** | Buyer | The system shows only the items that need a person to look: low-confidence reads, ambiguous units, unmapped lines, spec deviations, missing lines, unresolved references ("same as last year"). Buyer accepts, corrects or marks "ask vendor". | Reviewed dataset; clarification drafts | [R] (answers A-17) |
| 6 | **Comparison workspace** | Buyer | Side-by-side grid: 30 lines × 5 vendors. Normalised ex-GST ₹/box (freight separate; landed only where calculable), status badges, questionnaire scorecard and attached docs per vendor. | Single source of truth | [A] |
| 7 | **Ask & analyse** | Buyer / VP | NL questions → text, tables, charts. Each answer shows its method, filters, exclusions and assumptions. | Answers that can be reproduced | [A] |
| 8 | **Award decision** | Buyer → VP | Build or accept a scenario (single-source, split-by-line, filtered). The system writes a recommendation with rationale, savings vs baseline, risks and open items. | Award memo | [A] |
| 9 | **Export & audit** | Buyer | Export comparison + award memo. Every number links back to its source. | xlsx + PDF/memo | [A] exports; format [R] |

---

## 5. Functional requirements

Priority: **P0** = needed for the demo story · **P1** = strengthens trust/judgment signal · **P2** = nice to have, likely cut.

### 5.1 RFx co-pilot
| ID | Requirement | Priority | Tag |
|---|---|---|---|
| F-RFX-1 | Conversational creation of scope, line items, questionnaire and terms | P0 | [A] |
| F-RFX-2 | Co-pilot asks clarifying questions when the spec is incomplete (e.g. "Internal or external dimensions?", "Printed? How many colours?") | P0 | [R] |
| F-RFX-3 | Line item template specific to corrugated: box style (RSC/die-cut), L×W×H (internal, mm), ply, flute, paper GSM per layer, BF, printing, annual volume, delivery location | P0 | [R] |
| F-RFX-4 | Questionnaire split into **Quality** and **Commercial** sections (v1.2, I2; locked as DL-14), with **typed answers** (yes/no, numeric, document upload) and **pass/fail rules**, for example "ISO 9001 certificate attached", "BCT test report available", "Monthly capacity ≥ X tonnes", "Lead time ≤ 15 days". This is what makes "cleared the quality questionnaire" computable. That phrase means the Quality section **only** (DL-14). Commercial results are shown separately. | P0 | [R] (enables A-20) |
| F-RFX-5 | Declare the **response basis** up front: price per box, INR, delivered, GST shown separately, validity in days | P0 | [R] |
| F-RFX-6 | Buyer can edit any co-pilot output directly. The co-pilot never sends anything by itself. | P0 | [R] |
| F-RFX-7 | Optional Excel template generated from the RFx (offered, never required) | P1 | [R] (respects A-04) |

### 5.2 Distribution
| ID | Requirement | Priority | Tag |
|---|---|---|---|
| F-DIS-1 | Send RFx to selected vendors via a single channel (email) | P0 | [A] |
| F-DIS-2 | Sending may be simulated (stubbed); sent log visible | P0 | [A] (A-15 allows) |
| F-DIS-3 | Track response status per vendor: sent / responded / partial / clarification pending | P1 | [R] |

### 5.3 Ingestion & extraction
| ID | Requirement | Priority | Tag |
|---|---|---|---|
| F-EXT-1 | Accept xlsx (any layout), pdf (digital), docx, image (photo, skewed), plain-text email | P0 | [A] |
| F-EXT-2 | Real AI extraction on every document. Nothing pre-parsed or hardcoded. | P0 | [A] |
| F-EXT-3 | Pull out line prices, units, quantities and specs as quoted, plus commercial terms (freight, GST, payment, validity, MOQ, tooling/plate charges, discounts **including footnotes**) and questionnaire answers | P0 | [A] |
| F-EXT-4 | **Line matching:** map each vendor line to an RFx line by spec and description, not by row order. Show match confidence. | P0 | [A-i] |
| F-EXT-5 | Every extracted value keeps **provenance**: file, page/sheet/cell or image region, and the raw text as quoted | P0 | [R] (answers A-18) |
| F-EXT-6 | Every extracted value has a **confidence state** (see §7) | P0 | [A] (A-17) |
| F-EXT-7 | Apply **document-level terms** (e.g. "5% discount on all items", "freight extra") to every line they cover, and show that the term was applied | P0 | [A-i] (footnote discount, "freight extra") |
| F-EXT-8 | Re-run extraction when a vendor sends a revised quote. Keep version history. | P2 | [R] |

### 5.4 Normalisation
| ID | Requirement | Priority | Tag |
|---|---|---|---|
| F-NRM-1 | Convert all prices to a **single comparison basis: normalised ex-GST ₹ per box**. Freight is kept separately. Landed cost is shown only when freight is known or comes from a disclosed estimate (DL-2). | P0 | [A] (same units/currency); basis [R] |
| F-NRM-2 | **Unit conversion with domain logic:** ₹/kg → ₹/box using the **weight-source hierarchy** (DL-18): documented SKU reference weight → vendor-stated weight → estimate from versioned, not-yet-validated constants (*Needs review*) → otherwise *Not convertible*, with the missing inputs named (DL-1). ₹/100 pcs and ₹/1000 pcs → ₹/box. | P0 | [A] (A-16) |
| F-NRM-3 | **Currency conversion** using a stated rate, rate date and source. The buyer can change the rate. | P0 | [A] (A-16) |
| F-NRM-4 | **Freight handling:** record the freight basis (included / stated / unknown). A freight estimate is used only when it is disclosed as an estimate and accepted by the buyer. It is never added silently (DL-2). | **P0** (v1.2) | [R] |
| F-NRM-5 | **Tooling/plate charges:** detect and show separately (**P0**, v1.2, B6). Spreading them over annual volume in the total-cost view stays **P1**. | P0 / P1 | [R] |
| F-NRM-6 | **Spec deviation flag:** if the quoted spec differs from the RFx beyond the tolerances in PRD MAT-3 (GSM −5%, dims ±2 mm, ply/flute exact, BF ≥ RFx), flag the line **Alternate**, never "equivalent". *Superseded wording: v1 said "non-compliant" for any difference.* | P0 | [R] |
| F-NRM-7 | No silent conversions. Every conversion is recorded in an **assumptions ledger** the buyer can see and edit. | P0 | [R] |

### 5.5 Exception review
| ID | Requirement | Priority | Tag |
|---|---|---|---|
| F-REV-1 | One **exceptions queue**, sorted by money at risk (value × volume) | P0 | [R] |
| F-REV-2 | Side-by-side view: source snippet/image region next to the extracted value | P0 | [R] |
| F-REV-3 | Actions: Accept / Correct / Mark missing / Ask vendor. Every action is logged with user and timestamp. | P0 | [R] |
| F-REV-4 | "Ask vendor" writes a **clarification email** for the buyer to review (e.g. "Please confirm whether ₹4.80 is per box or per 100 pcs for lines 12–18") | P1 | [R] |

### 5.6 Comparison workspace
| ID | Requirement | Priority | Tag |
|---|---|---|---|
| F-CMP-1 | Grid: 30 RFx lines × 5 vendors, normalised ex-GST ₹/box (landed view where calculable, DL-2), with best compliant price per line highlighted | P0 | [A] |
| F-CMP-2 | Cell status badges from the **canonical status model** (PRD §6): verified / extracted / assumed / needs review / unresolved / not convertible / missing, plus flags such as Alternate and FX. *Superseded: the v1 list of six.* | P0 | [A] (A-17) |
| F-CMP-3 | Click any cell to see the original quote, conversion steps and source | P0 | [R] |
| F-CMP-4 | Vendor panel: questionnaire answers with pass/fail, attached docs (certificates, test reports), commercial terms | P0 | [A] |
| F-CMP-5 | Coverage indicator per vendor (e.g. "27/30 lines quoted") | P0 | [A] (A-16) |
| F-CMP-6 | Toggle between "as quoted" and "normalised" values | P1 | [R] |

### 5.7 NL analyst
| ID | Requirement | Priority | Tag |
|---|---|---|---|
| F-NLA-1 | Free-form NL questions over the full comparison data, questionnaire and terms | P0 | [A] |
| F-NLA-2 | Answers as text, table, chart, or export | P0 | [A] |
| F-NLA-3 | **The AI plans the analysis; the numbers come from actual computation over the data.** The model never makes up figures. | P0 | [R] (answers A-11, A-15) |
| F-NLA-4 | Every answer shows: **method** (in plain steps), **filters applied**, **vendors/lines excluded and why**, **assumptions used**, **data quality caveats** (e.g. "2 cells used are unreviewed") | P0 | [R] (answers A-18) |
| F-NLA-5 | Multi-turn context ("now exclude Vendor C", "what about only 5-ply lines?") | P0 | [A-i] |
| F-NLA-6 | Asks back when the question is ambiguous ("cheapest by unit price or by total annual cost?") instead of guessing | P1 | [R] |
| F-NLA-7 | Says so plainly when the data can't answer the question ("No vendor provided lead-time by line; I can only compare quoted overall lead times") | P0 | [R] |
| F-NLA-8 | Save a useful answer as a **scenario** to compare or award from | P1 | [R] |

### 5.8 Award & export
| ID | Requirement | Priority | Tag |
|---|---|---|---|
| F-AWD-1 | Scenario builder: single-source, split by line, filtered by questionnaire (Quality or all mandatory; strict or inclusive). **A vendor share cap is P1, with no demo dependency** (v1.2, B6). | P0 | [A] (A-20) |
| F-AWD-2 | Award memo: recommendation, total value, savings vs baseline (e.g. last year's price), rationale per vendor, risks, open items, assumptions | P0 | [A] (A-12) |
| F-AWD-3 | **Award readiness gate:** warn when the recommendation depends on unreviewed, assumed or missing data, and list exactly which cells | P0 | [R] |
| F-AWD-4 | Export: comparison as xlsx (with source references), award memo as PDF/markdown | P0 | [A] exports; formats [R] |
| F-AWD-5 | Full audit trail: who changed what, when, original vs corrected value | **P0** (v1.2, DL-7) | [R] |

---

## 6. Edge cases and failure scenarios

Our design rule **[R]**: **the system may be uncertain, but it must never be silently wrong.** Every edge case below ends either in an automatic fix *the buyer can see*, or in an item for the buyer to review.

### 6.1 Assignment-named edges **[A]**
| # | Scenario | System behaviour | What the buyer sees |
|---|---|---|---|
| E-01 | **Photo of printed rate card, taken at an angle** | Correct for skew, then read it **twice, independently**: OCR, and a separate visual AI read that never sees the OCR output (DL-11). Compare the two. | Agreeing values shown with the image region (at most *Extracted*). A disagreement, or a value only one read found, is *Unresolved* and shows both readings for a person to decide. The image is always one click away. |
| E-02 | **Vendor quoted 27 of 30 lines** | Mark 3 lines "Not quoted". Never fill them with zero or an average. | Coverage "27/30". Empty cells clearly marked. Analyses state how missing lines were handled ("Vendor D excluded from lines 8, 14, 22 — not quoted"). |
| E-03 | **Quote in USD** (V2 quotes its entire response in USD, DL-15) | Convert at a stated rate and date. Keep the original. Status *Assumed (FX rate)*. | ₹ value with a "USD-converted" badge. Rate shown and editable. Editing it recomputes everything and can flip rankings. (A dedicated sensitivity tool is P1.) |
| E-04 | **"Per box" vs "per 100 pieces"** | Detect the unit stated on the quote. If none is stated, check whether the price is plausible against other vendors and the expected box cost. If a ~100× gap points to a unit problem, **flag it, don't auto-fix**. The value is *Unresolved* and **excluded from all calculations** until the buyer resolves it (DL-10). The peer check runs only after all responses are processed (DL-9). | "Unit ambiguous: ₹480 looks like per-100 (₹4.80/box). Confirm?" with Accept / Correct / Ask vendor. |
| E-05 | **Discount buried in a PDF footnote** | Pull out document-level terms and apply them to the lines they cover | Line shows "−5% footnote discount applied (p.3, footnote 2)" |
| E-06 | **Commercials in a Word paragraph** | Pull terms out of the prose | Each term linked to the sentence it came from |
| E-07 | **Excel that ignores the template** | Work out the layout (header row, merged cells, extra columns) and match lines by spec, not row position | Match confidence per line. Unmatched rows listed. |
| E-08 | **"₹42/kg for the 5-ply, 38 for the 3-ply, rest same as last year, freight extra"** | (a) "38" has no unit of its own: it inherits ₹/kg from the preceding clause, recorded as an inference with both evidence spans, status *Assumed* (DL-12); (b) apply the ply-level price to all lines of that ply; (c) ₹/kg → ₹/box via the weight-source hierarchy (DL-18): a documented SKU reference weight converts directly. Without one, a vendor-stated weight is used. Without either, an estimate from approximate constants is *Needs review* and kept out of the formal award until the buyer reviews it. Estimation is only possible for supported item types (RSC; die-cut or pad with blank size). Partitions and die-cuts without a blank size, with no reference or vendor weight, are *Not convertible*; (d) **"same as last year"** is ambiguous (DL-20): both readings (remaining prices / remaining terms) are kept as *Unresolved*, with this vendor's own same-spec last-year values shown as candidates (never another vendor's), and a clarification request is generated. A value is applied only after the buyer confirms it; (e) "freight extra" → freight basis = *unknown*. Last year's freight terms are never carried forward (DL-8); landed cost is not calculated unless the buyer accepts a disclosed estimate (DL-2) | Each derived price shows its chain: "₹38/kg × 0.42 kg (computed from RFx spec) = ₹15.96/box ex-GST · Freight: unknown". Lines with incomplete construction show "Not convertible — missing: flute GSM". Last-year lines are tagged with where they came from, or "Pending clarification". |
| E-09 | **VP's compound what-if** | Filter vendors by **Quality-section** eligibility (strict), take the cheapest per line, compute the total and the savings (PRD §5.9 definitions), and show what changes vs the best single vendor | Table + total + excluded vendors and why + lines where no qualified vendor quoted |

### 6.2 Additional edges we expect **[R]**
| # | Scenario | Behaviour |
|---|---|---|
| E-10 | Vendor quotes an **alternate spec** (140 GSM vs 150, B vs C flute) | Flag as "Alternate". Exclude from like-for-like ranking by default. Buyer can choose to include it. |
| E-11 | **Same line priced twice** in one response (e.g. table vs summary page disagree) | Flag conflict, show both, never pick one silently |
| E-12 | **Tiered/slab pricing** by volume | Pick the slab matching RFx annual volume. Show the other slabs. |
| E-13 | **GST inclusive vs exclusive** unclear | Default to "unclear" status. Compare ex-GST. Flag it. |
| E-14 | **Price validity / paper-index escalation clause** | Shown as a commercial risk on the vendor panel and in the award memo |
| E-15 | **Questionnaire partially answered** or answered "Yes" with no proof attached | Status **Unverified**. Excluded under strict eligibility, but never labelled Fail. The buyer can verify it or override it, with an audit record (DL-3, DL-7). |
| E-16 | **Attached cert expired** or names a different legal entity | **Unverified** for that question (not Fail), with the reason shown on the vendor panel (PRD §5.7). *Superseded: v1 said "flag" only.* |
| E-17 | **Revised quote** arrives after analysis | Show what changed. Earlier scenarios marked stale. |
| E-18 | **Unreadable / corrupt file** | Say "could not read". Never return an empty result as if it were a real answer. Offer "ask vendor to resend". |
| E-19 | **NL question outside the data** ("what's Vendor B's financial health?") | Say it isn't in the data, and suggest what could be asked or collected |
| E-20 | **Extraction or AI service failure** mid-run | Stage marked failed, retry available. No half-updated grid shown as complete. Analyst conversations stay intact: a failed turn is never written into the history (PRD AI-13). |
| E-21 | **Outlier price** (e.g. 3× peer median) | Checked only after all responses are in (DL-9). A unit-sized gap (≥ 20×) is *Unresolved*. A smaller outlier is *Needs review*: excluded from formal awards by default, and shown with a warning in exploratory views (DL-16). |

---

## 7. Trust, accuracy and explainability requirements

The bar **[A]**: *"Would a buyer with ₹4 crore on the line act on what's on your screen?"*

Our answer is five commitments **[R]**:

### 7.1 Every number has a source (provenance)
- Any normalised cell opens to: original file → exact region/cell/sentence → raw value as quoted → each conversion step → final value.
- The original documents are never changed and are always viewable.

### 7.2 Uncertainty is visible and has a clear set of states

> **v1.2: the v1 six-state table is superseded.** The only definition is PRD §6 (DL-10). Summary:

| State | Meaning | In calculations |
|---|---|---|
| ✅ **Verified** | Buyer resolved it, or it was auto-verified (digital source, all checks passed, no assumptions) | Included |
| 🔵 **Extracted** | AI-read, checks passed, not reviewed by a person (photo values are capped here) | Included, counted as unreviewed |
| 🟣 **Assumed** | Depends on a disclosed assumption: FX rate, computed box weight, inherited unit, "same as last year" | Included, assumption listed |
| 🟠 **Needs review** | A number exists, but an advisory check fired (outlier, arithmetic, weight mismatch, **estimated weight**) | **Excluded from formal award calculations by default** (audited buyer override allowed). Included in exploratory analysis on request, labelled with caveats (DL-16). |
| 🔶 **Unresolved** | No trustworthy number yet (unit unknown/suspect, read disagreement, evidence not found, baseline not for this vendor…) | **Never included** |
| ⚫ **Not convertible** | Inputs insufficient or item type not weight-computable; landed with freight unknown | **Never included** |
| ⚪ **Missing** | Not quoted | **Never included** |

*Alternate* (spec deviation) is a flag, not a state. *Unverified* belongs only to questionnaire eligibility (Pass / Fail / Unverified).

### 7.3 Calculations are deterministic and can be re-run
- The AI decides *what* to compute. The figures come from running the calculation on the data.
- **Determinism boundary (v1.2, I6):** AI extraction isn't repeatable. Everything from the stored extracted facts onward is: same inputs give the same numbers, in any processing order. An analyst answer is reproducible for the same tool calls, which are shown in "Show work".
- Every analyst answer shows its working in plain language (filters → method → result) so a non-technical VP can check it.

### 7.4 Checks before trust
Automatic consistency checks on extracted data:
- line total = unit price × qty
- price within a plausible band vs peers (checked only after all responses are in, DL-9) and vs last year's price. *Superseded: v1's "box weight × paper cost" check was dropped, as there is no paper-cost data.* With no plausibility reference, a value can't be auto-verified.
- currency and unit stated
- the same value doesn't disagree across a document

A failed check moves the cell to *Needs review* (advisory) or *Unresolved* (blocking), per PRD §6.2.

### 7.5 A person decides the award
- The system **recommends**. The buyer **decides**.
- The award gate (F-AWD-3) lists every unreviewed, assumed or missing input the recommendation depends on. The buyer can still go ahead, but has to acknowledge them, and that is recorded.
- All corrections and overrides are logged (original value, new value, who, when, why).

### 7.6 Accuracy targets (for the prototype) **[R]**
We'll measure against the fabricated dataset's answer key. The key is used only to *measure*; it is never shown to the model.
- Line-to-RFx matching accuracy
- Price extraction accuracy (exact match after normalisation)
- **Silent error rate**: wrong values shown as Verified/Extracted/Assumed (target: **zero** on the demo set; this is the metric that matters)
- **Analyst silent error rate** (v1.2, I8): a wrong number with no stated interpretation or caveat (target: **zero** on the walkthrough set)
- Percentage of cells sent to review (lower is better, but only after the silent error rate is at zero)

---

## 8. Expected deliverables

| # | Deliverable | Required? | Contents | Tag |
|---|---|---|---|---|
| D-1 | **Working prototype** for a panel-driven live demo | Required | The full flow in §4 on the demo dataset. Must hold up when the panel goes off script. | [A] |
| D-2 | **Recorded walkthrough of the analyst conversation** | Required | 8–12 questions, chosen by us, running from simple to compound to award (see below) | [A] |
| D-3 | **One-page decision note** | Required | Key decisions + why. What we left out on purpose. Known limitations. | [A] |
| D-4 | **"The better problem"** perspective | Invited | Included in D-3 or as an addendum (see §11) | [A] optional |
| D-5 | **Fabricated dataset** | Implied (needed for D-1) | RFx (30 lines + questionnaire + terms), 5 vendor responses in 5 formats, attached docs, last-year baseline prices, answer key | [A-i] |
| D-6 | Accuracy scorecard on the demo set | Our addition | The §7.6 metrics, honestly reported | [R] |

*Delivery estimate (FD-7): FD-7 rev. 4: 29.0 days of estimated effort for one builder (20.5 P0 implementation + 6.5 testing, evaluation & integration + 2.0 demo prep), re-sequenced around a vertical slice at day ~6.5. Not a deadline or contract. P1 (3.25 d) outside the schedule. Protected testing and rehearsal allocations kept.*

### 8.1 Proposed dataset shape **[R]** (v1.2: superseded by PRD §11; summary below)
Each vendor carries one response format and several edge cases. Every planted behaviour depends only on P0 features (DL-13).

| Vendor | Format | Edge cases carried | Quality eligibility |
|---|---|---|---|
| V1 — large integrated mill-converter | Excel, own layout | Ignores template; tiered pricing; tooling charges separate; delivered; skips the 2 printed die-cut mailers | **Pass** |
| V2 — import-capable converter | PDF on letterhead, **entire quote in USD** | 5% footnote discount; 2 lower-GSM alternates (on the mailers); escalation clause; no partitions | **Pass** |
| V3 — regional converter | Word doc | Commercials in prose; **27/30 lines**; ISO certificate expired | **Unverified** |
| V4 — small local supplier | Angled phone photo | Prices **per 100 pcs**, some unlabelled; hard-to-read digits; capacity below requirement; certificate in another entity's name | **Fail** |
| V5 — regional mill | Terse email, the assignment's exact sentence | ₹/kg by ply with an inherited unit; documented reference weights for most SKUs, 2 RSC without one (estimated weight → *Needs review*); "same as last year" (own baseline, changed-spec baseline, other-vendor-only baseline); freight extra; payment terms rejected | **Pass** (Commercial: Fail) |

The VP's split question therefore runs over **three eligible vendors** (V1, V2, V5). It leaves the two die-cut mailers uncovered like-for-like, and lists V3 (Unverified) and V4 (Failed) separately.

Line items: about 30 SKUs covering 3-, 5- and 7-ply RSC boxes, a few die-cut boxes, partitions and pads, with realistic dimensions, GSM, BF and annual volumes. The total annual spend should come out near **₹4 crore** to match the brief's stakes.

### 8.2 Candidate walkthrough questions **[R]**
> v1.4: the authoritative question set is `docs/10_demo_runbook.md` §4 (Q1–Q10). It adds a document-fact question (SOT FN-11). The list below is kept for history.
1. "Which vendor is cheapest overall, and how confident are you?"
2. "Show me landed cost per box by vendor for all 5-ply lines, as a chart." (Lines with unknown freight are excluded and listed, DL-2.)
3. "Who didn't quote everything, and what does that do to the ranking?"
4. "Which vendors cleared the quality questionnaire, and why didn't the others?" (v1.2. The earlier wording, "on what grounds did the others fail?", is kept as an eval **trap**: the answer must correct the premise, because V3 is Unverified, not failed.)
5. **"What if we split it, cheapest per line, but only among vendors who cleared the quality questionnaire?"** (the VP's question, verbatim)
6. "How much of that saving depends on assumptions, such as FX or freight estimates?"
7. "Which quotes deviate from our spec, and how much cheaper are they because of it?"
8. "What's our saving vs last year's prices?"
9. "Which lines does the split leave uncovered, and what happens if we accept alternates there?" (v1.2: replaces the vendor-cap question, because the cap is P1 and the demo may only use P0, DL-13.)
10. "Draft the award recommendation and export it."

---

## 9. Product decisions we need to make

Each row records the decision, the options, our recommendation, and the reason. The one-page note (D-3) will draw from this table.

| # | Decision | Options | Recommendation **[R]** | Why |
|---|---|---|---|---|
| PD-1 | Comparison basis | ₹/box · ₹/kg · total annual cost | **Normalised ex-GST ₹/box as the main view. Freight shown separately. Landed ₹/box only where freight is known or comes from a disclosed estimate. Annual total cost as a second view.** (DL-2) | ₹/box is how plants consume and budget. ₹/kg hides box-weight differences. Mixing in guessed freight would make guesses look like facts. |
| PD-2 | Distribution channel | Email · vendor portal · WhatsApp | **Email (simulated send)** | Matches the brief's story. Zero vendor friction. A portal would go against "nobody is forced into your template". |
| PD-3 | Behaviour under uncertainty | Auto-fix silently · always ask · fix-and-flag | **Fix and flag when confident. Ask when ambiguous. Never fix silently.** | Avoids silent errors without burying the buyer in review items |
| PD-4 | Ambiguous unit (100× gap) | Auto-correct · flag | **Flag with a suggested fix. The buyer confirms. Until then the value is Unresolved and excluded from calculations** (v1.2, DL-10). | A wrong 100× correction on ₹4 cr spend is the worst possible failure |
| PD-5 | Missing lines in analysis | Exclude · penalise with max price · fill with average | **Exclude, and say so in every answer** | Filling in prices is fabrication. A max-price penalty is a policy, offered only as an option the buyer can turn on. |
| PD-6 | Alternate-spec quotes | Treat as equivalent · exclude · separate | **Exclude from like-for-like by default. Show separately as "alternates".** | Protects quality. Still shows potential savings. |
| PD-7 | Questionnaire pass/fail | Free-text judgement · rule-based | **Typed answers + explicit pass rules set at RFx time** | Makes the VP's filter computable and auditable |
| PD-8 | "Claimed but unproven" answers | Pass · fail · separate state | **Three states: Pass / Fail / Unverified. Unverified is excluded under strict eligibility but never called Fail.** (DL-3) | Calling a vendor "failed" when they just didn't send proof is unfair to them and misleading for the VP |
| PD-9 | FX rate | Fixed · live · buyer-set | **Stated reference rate + date, editable by the buyer** | Transparent. Live rates add plumbing without adding to the demo. |
| PD-10 | Freight when "extra" | Ignore · estimate · ask | **Freight = unknown. Landed cost not calculated. The buyer may accept a disclosed estimate. Suggest asking the vendor.** (DL-2) | Ignoring freight makes the vendor look cheaper, and a hidden estimate looks like a fact. A disclosed, accepted estimate does neither. |
| PD-11 | "Same as last year" | Ignore · resolve from history · ask | **Resolve only from this vendor's own last-year price for the same line and spec (tag as Assumed). Otherwise Unresolved. Never use another vendor's price.** (v1.2, DL-8) | "Same as last year" means *their* last year. Borrowing another vendor's price would be fabrication. |
| PD-12 | How much the co-pilot drafts | Full auto-draft · guided Q&A | **Guided Q&A that proposes a full draft. Buyer edits.** | Fast, and the buyer stays in control |
| PD-13 | Analyst output when the question is ambiguous | Guess · ask | **Ask one short question, or answer with the stated interpretation** | Speed vs correctness. Default to stating the interpretation. |
| PD-14 | Export formats | xlsx · PDF · CSV · docx | **xlsx (comparison with source refs) + PDF/markdown award memo** | What buyers and approvers actually forward |
| PD-15 | Vendor-facing experience | None · clarification emails · portal | **Only system-drafted clarification emails the buyer reviews** | Keeps scope tight. Fits the "vendors reply however they like" rule. |
| PD-16 | What to cut | — | See §12 | Taste = what we don't build |

---

## 10. Traceability: assignment requirement → product capability

| Req | Assignment requirement (short) | Proposed capability | FR IDs | Priority |
|---|---|---|---|---|
| A-01 | Talk the RFx into existence | Conversational RFx co-pilot with clarifying questions | F-RFX-1, F-RFX-2, F-RFX-6 | P0 |
| A-02 | Scope, lines, questionnaire, terms | Corrugated line-item template; typed questionnaire with pass rules; terms + response basis | F-RFX-3, F-RFX-4, F-RFX-5 | P0 |
| A-03 | Send via chosen channel | Email distribution (simulated) + sent log | F-DIS-1, F-DIS-2, F-DIS-3 | P0 |
| A-04 | No forced template | Accept any format; optional template only | F-EXT-1, F-RFX-7 | P0 |
| A-05 | Read every shape (xlsx, pdf, docx, photo, email) | Multi-format AI extraction, line matching, document-level term handling | F-EXT-1…7 | P0 |
| A-06 | Single side-by-side comparison | Comparison grid 30 × 5 | F-CMP-1 | P0 |
| A-07 | Same lines, units, currency | Line matching; ₹/kg & per-100 → ₹/box; FX conversion; freight & tooling normalisation; assumptions ledger | F-EXT-4, F-NRM-1…7 | P0 |
| A-08 | Questionnaire + docs alongside numbers | Vendor panel with scored questionnaire and attached docs | F-CMP-4 | P0 |
| A-09 | NL over whole comparison | NL analyst with multi-turn context | F-NLA-1, F-NLA-5 | P0 |
| A-10 | Text, tables, charts, exports | Multiple answer formats + export | F-NLA-2, F-AWD-4 | P0 |
| A-11 | Real analysis on real data | AI plans, actual calculation produces the numbers | F-NLA-3 | P0 |
| A-12 | Defensible award decision | Scenario builder, award memo, readiness gate, audit trail | F-AWD-1…5 | P0 |
| A-13 | 5 vendors, 30 lines, questionnaire, docs | Demo dataset | D-5 | P0 |
| A-14 | Realistic fabricated data | Corrugated-specific dataset with real spec attributes and plausible commercials | D-5, §8.1 | P0 |
| A-15 | Real AI loops, no hardcoding | Live extraction + live analysis; answer key used only for scoring | F-EXT-2, F-NLA-3, §7.6 | P0 |
| A-16 | Angled photo, 27/30, USD, unit ambiguity | Specific handling for each named case | E-01…E-04, F-CMP-5, F-NRM-2/3 | P0 |
| A-17 | Show the buyer when unsure | Canonical status model (PRD §6, seven value states + flags); exceptions queue; caveats in every answer | F-EXT-6, F-CMP-2, F-REV-1…3, F-NLA-4 | P0 |
| A-18 | Earn trust for ₹4 cr | Source links, consistency checks, award gate, audit log | §7, F-EXT-5, F-AWD-3, F-AWD-5 | P0 |
| A-19 | Judgment & taste, explain why | Decision log (§9) → one-page note | PD-1…16, D-3 | P0 |
| A-20 | VP's compound what-if | Computable questionnaire pass/fail + line-level split scenario | F-RFX-4, F-AWD-1, E-09 | P0 |
| A-21 | Live demo the panel drives | Generalising NL analyst; edge cases built into the data | D-1, F-NLA-6/7 | P0 |
| A-22 | Recorded analyst walkthrough | Scripted question path (§8.2) | D-2 | P0 |
| A-23 | One-page note incl. what's left out | Decision table + cut list | D-3, §9, §12 | P0 |
| A-24 | "Better problem" (optional) | Problem-reframe hypothesis | §11 | P1 |
| A-25 | Total liberty on stack/UI/etc. | Recorded in a later technical design doc, not here | — | — |

**Coverage check:** all 25 assignment requirements map to at least one capability or deliverable. No P0 capability exists without a link back to an assignment requirement or to trust (A-17/A-18).

---

## 11. "Was the interesting problem somewhere else?" — hypotheses to test **[H]**

We'll build what the brief asks for, but these are the hypotheses we expect to argue in the one-pager:

1. **Normalisation is the real product, not extraction.** Reading the text is close to solved. The hard part is *meaning*: what "per box" means, what "same as last year" refers to, whether 140 GSM is acceptable. That is domain logic plus judgment.
2. **The clarification loop is where the days go.** Retyping takes 3 days, but chasing vendors to fix ambiguities often takes longer. A system that turns its uncertainty into precise, batched vendor questions may save more time than the extraction itself.
3. **Garbage in starts at the RFx.** Many messy responses come from vague RFx specs. A co-pilot that produces an unambiguous spec and response basis means fewer normalisation problems later.
4. **"Cheapest qualified" is the wrong objective for packaging.** Total cost of ownership (damage rates, lead-time reliability, paper-price escalation clauses) often matters more than unit price. The VP's question may be the wrong question, and the product could point that out.

---

## 12. Deliberately out of scope **[R]**

| Left out | Why |
|---|---|
| Real SMTP/inbox integration | Allowed to stub (A-15). Adds no product signal. |
| Vendor portal / vendor login | Goes against A-04. Vendors reply however they like. |
| Multi-round negotiation / reverse auction | Beyond the "one flow" in the brief |
| ERP/PO creation after award | The flow ends at a defensible decision |
| Live FX feeds, live paper-index feeds | A stated, editable reference is more transparent for a demo |
| Multi-user approval workflow, roles & permissions | Award memo + audit log stands in for it |
| Multiple categories | Depth in corrugated beats breadth |
| Vendor risk / financial health scoring | Not in the data. The analyst says so (E-19). |
| Handwritten documents, scanned multi-page faxes | The angled photo already covers the hard image case |

---

## 13. Open questions for the team

All four v1 open questions are now resolved:

1. Last year's prices → **kept as a reference dataset** (DL-5), used for "same as last year" only with the same vendor and spec (DL-8).
2. Alternate-spec bids → **excluded from like-for-like awards by default; the buyer can include them explicitly** (DL-6).
3. Unseen-file upload → **supported, optional in the main demo** (DL-4).
4. Claimed but unproven → **Unverified: excluded under strict eligibility, never labelled Fail** (DL-3).
