# 11 — Dataset Realism Review (external, human)
**Resolves:** audit SC-07 · **Source requirement:** SOT **REQ-05**, "Fabricate a dataset a procurement person would nod at." (PDF p.1)
**Locked decision:** **DL-22**: realism is validated only by a procurement-literate human. **AI self-review is not external validation** and doesn't count towards this sign-off.
**When:** after the M1 generator produces the demo dataset, and **before** the dataset is frozen (Plan M1 exit). Corrections are re-reviewed for the items they touch.

---

## 1. Reviewer
| Field | Value (to be filled by the owner) |
|---|---|
| Reviewer name | |
| Role / experience (must include hands-on procurement or packaging buying) | |
| Relationship to the project (must not have authored the dataset) | |
| Date(s) of review | |
| Dataset version / generator seed reviewed | |
| Time spent | |

**Eligibility rule:** the reviewer has bought, sourced or managed category spend in packaging, MRO or similar direct materials, or has evaluated vendor quotes professionally. The builder and any AI tool are not eligible.

## 2. Materials given to the reviewer
- RFx (the canonical spec rendered as the vendors would see it) and the buyer brief pack.
- The five vendor responses exactly as delivered (xlsx, PDF, docx, **real phone photo**, email) with their attachments.
- Last year's reference prices and terms (baseline).
- **Not given:** ground truth, expected statuses, or any explanation of which edge cases are planted. The reviewer should react as a buyer would.

## 3. Checklist
Rate each item **Realistic / Plausible with changes / Unrealistic**, and comment. Any item rated "Unrealistic" blocks the M1 exit until it is corrected and re-reviewed.

### 3.1 Pricing
| # | Question | Rating | Comment |
|---|---|---|---|
| P1 | Are ₹/box prices plausible for each box size, ply and print spec (Indian market, current year)? | | |
| P2 | Is the spread between vendors (≈ ±15–25%) realistic for this category? | | |
| P3 | Are ₹/kg rates (e.g. ₹38–42/kg for 3/5-ply) plausible relative to kraft paper prices? | | |
| P4 | Are volume slabs, tooling/plate/die charges and their sizes realistic? | | |
| P5 | Is V2 believable as a domestic converter quoting USD-linked prices invoiced in INR, and is the implied INR level consistent? | | |
| P6 | Is the per-100-pieces pricing (V4) something a small local converter would really do? | | |
| P7 | Are last year's prices plausible relative to this year's (inflation, paper index)? | | |
| P8 | Does the total annual spend (~₹4 crore for 30 SKUs) feel right for a single plant? | | |

### 3.2 Specifications
| # | Question | Rating | Comment |
|---|---|---|---|
| S1 | Are the dimensions, ply, flute profiles, GSM per layer and BF values realistic and internally consistent? | | |
| S2 | Are the item types (RSC, die-cut mailers, partitions, pads) and their mix typical of a plant's packaging list? | | |
| S3 | Are the documented reference unit weights plausible for the stated construction? | | |
| S4 | Where a vendor offers a construction different from the one requested, is that the kind of substitution vendors really propose? | | |
| S5 | Are annual quantities per SKU realistic? | | |

### 3.3 Vendor behaviour
| # | Question | Rating | Comment |
|---|---|---|---|
| B1 | Does each vendor's format and tone match its profile (large mill, import-capable converter, regional converter, small local supplier, regional mill)? | | |
| B2 | Is the Excel that ignores the template laid out the way a real vendor would send it? | | |
| B3 | Does the letterhead PDF with a footnote discount look genuine? | | |
| B4 | Does the Word response with commercials in paragraphs read like a real vendor letter? | | |
| B5 | Is the terse email ("₹42/kg for the 5-ply, 38 for the 3-ply, rest same as last year, freight extra") plausible as a reply from that vendor? | | |
| B6 | Where a vendor did not quote every line, are the gaps (and any reason given) realistic for that vendor? | | |
| B7 | Does the rate card in the phone photo look like a real printed rate card? | | |

### 3.4 Commercial terms
| # | Question | Rating | Comment |
|---|---|---|---|
| C1 | Are payment terms, validity, lead times and MOQ realistic and varied the way real vendors vary? | | |
| C2 | Are freight terms (delivered / per box / "freight extra") realistic for each vendor type? | | |
| C3 | Is the GST treatment shown the way Indian vendors typically show it? | | |
| C4 | Is the paper-price escalation clause realistic in wording and mechanism? | | |
| C5 | Are last year's commercial terms plausible for these vendors? | | |

### 3.5 Questionnaire answers and documents
| # | Question | Rating | Comment |
|---|---|---|---|
| Q1 | Are the quality questions (ISO 9001, BCT/ECT reports, food-grade compliance for food-contact lines, capacity, in-house printing) what a buyer would actually ask? | | |
| Q2 | Are the commercial questions (payment terms, lead time, GST registration) realistic? | | |
| Q3 | Do the vendors' answers sound like real vendor answers? | | |
| Q4 | Do certificates and test reports look plausible (issuer, number format, dates, entity names)? | | |
| Q5 | Taken together, do the vendors' certificates look like what a buyer actually receives (validity dates, issuing body, the company named on them)? | | |

### 3.6 Overall
| # | Question | Answer |
|---|---|---|
| O1 | Would you "nod at" this dataset as a procurement professional? (Yes / Yes with changes / No) | |
| O2 | What's the single least believable thing? | |
| O3 | Is anything missing that a real RFx response set would almost always contain? | |

## 4. Feedback log
| ID | Checklist item | Reviewer feedback (verbatim or close paraphrase) | Severity (blocking / should-fix / nice-to-have) | Decision (accept / reject with reason) |
|---|---|---|---|---|
| F-01 | | | | |

## 5. Corrections log
| Feedback ID | Change made (generator truth spec / artefact) | Files affected | Ground truth updated? | Re-reviewed by reviewer? (date) |
|---|---|---|---|---|
| | | | | |

## 6. Sign-off
| | |
|---|---|
| All "Unrealistic" ratings resolved | ☐ |
| Reviewer re-checked the corrected items | ☐ |
| Reviewer's overall answer to O1 | |
| Reviewer signature / name and date | |

**Rules:**
- The builder may not fill in sections 3, 4 or 6 on the reviewer's behalf.
- AI-generated commentary may be attached as a *separate, labelled* appendix, but it never substitutes for any rating.
- Rejecting reviewer feedback requires a written reason in §4 and is reported in the fix log.

---

## 7. Review record — 2026-11-05 (owner-approved deviation from DL-22)

**Who reviewed:** an AI tool (ChatGPT), prompted to take a senior packaging buyer's perspective. The project owner then checked the review manually. **No independent, procurement-literate human reviewed the dataset.** The review itself states that it "does not satisfy the required independent human-review gate".

**Deviation:** REQ-05 ("Domain-realism review by a human with procurement knowledge (not only an AI review)") and DL-22 ("AI self-review is not external validation") are **not met as specified**. The owner explicitly approved using this AI review, with their own manual check, in place of the independent human review (session of 2026-11-05). The deviation must be disclosed in the one-page note (DEL-03/04) as a deliberate limitation.

**Review file:** `EVAL_ROOT/reviews/2026-11-05_ai_review_owner_checked.md` (unchanged copy of `5_Review_checklist_FILLED.md`).

**Overall answer (O1):** "Yes with changes". Three items were rated Unrealistic: P5, Q5 and B7.

### 7.1 Decisions on the feedback

| ID | Item | Feedback (short) | Decision | Reason / change |
|---|---|---|---|---|
| F-01 | P5 | V2's stated rate of ₹84.20/USD for 30-Oct-2026 is about 13% off the RBI reference (about ₹95.25) | **Accept** | Verified against a published RBI reference-rate series (CEIC: 95.249 on 30-Oct-2026). `V2_REFERENCE_RATE` changed to 95.25 and V2's USD prices regenerated. The runbook/live FX setting is now 95.25. |
| F-02 | Q5 | Malwa's ISO certificate expired before the offer date while the questionnaire says "Yes" | **Reject (keep)** | A deliberate, realistic vendor error: vendors do attach lapsed certificates. The product must catch it (Quality "Unverified", never "Failed"; PRD §11 V3). |
| F-03 | B7 | No phone photo in the pack | **Open** | The images supplied on 2026-11-05 were downloaded from chatgpt.com with no camera metadata. They are not camera originals, so they were not registered (DL-21) and were set aside in `EVAL_ROOT/fixtures/v4_rejected_not_camera_originals/`. V4 stays "Awaiting response" until a genuine phone photo exists. |
| F-04 | Q4 | Lab reports lack methods, conditioning, accreditation and signatory | **Accept** | Reports now state the BCT/ECT methods (IS 7028 Part 8 / ASTM D642; IS 7063 / TAPPI T 839), 23 °C / 50% RH conditioning, an NABL accreditation reference, "mean of 5 specimens" and a named signatory. |
| F-05 | B5/C1/C2 | Sahyadri's terse email, 30-day credit | **Accept as realistic, no change** | The email is the assignment's exact text (SOT EDGE-05). The 30-day credit is the planted Commercial "Fail". |
| F-06 | P7/C5 | Prices flat or down against paper inflation; baseline 25/30; terms only for Sahyadri | **Partly accept** | Last year's prices are now 2–9.5% below this year's. The 25/30 baseline (new SKUs this year) and the Sahyadri-only terms (reading B of "rest same as last year", DL-20) are by design. |
| F-07 | S3 | 9 SKUs without a standard weight | **Reject (keep)** | By design (DL-18 weight hierarchy; PRD §11: 21 SKUs with reference weights). Realistic for new and non-standard items. |
| F-08 | S1/Q4 | No BCT/ECT acceptance thresholds in the buyer brief | **Reject for scope** | Adding thresholds changes the canonical questionnaire and the buyer brief. Recorded as a known simplification. |
| F-09 | B1 | `.example` email domains | **Accept as-is** | Deliberate: the dataset is labelled synthetic, and reserved domains avoid real addresses. |
| F-10 | P4 | V1 says slabs are "shown in your RFx" | **Accept** | V1's note now reads "Our quantity slabs above apply to your annual requirement per item". |
| F-11 | B4/C1 | Validity of 45/60 days is shorter than the RFx's 90 | **Accept as realistic, no change** | Commercial deviations the comparison must surface. |
| B6 | — | V1 omits the mailers without a reason | **Accept** | V1 now states "Not quoted: PK-D401 and PK-D402 … not in our product range". |
| Q3 | — | Malwa answers "up to 4 colours" with a 3-colour remark while quoting 4-colour mailers | **Accept** | Remark changed to "4-colour flexo, in-house". |
| C4 | — | Escalation clauses name no index or base | **Accept** | Both clauses now name the index and base month and say how revisions apply. |
| P3 | — | Per-kg basis undefined | **Reject (keep)** | Part of the assignment's exact V5 sentence. Handled by the clarification pack (DL-32). |

### 7.2 Sign-off status
| | |
|---|---|
| All "Unrealistic" ratings resolved | ☐ No. P5 resolved (F-01); Q5 kept deliberately (F-02); B7 open until a genuine photo exists (F-03). |
| Independent human reviewer sign-off | ☐ Not obtained. Owner-approved AI-review deviation (above). |
| Dataset frozen | ☐ Not yet: V4 is pending the genuine photo. |
