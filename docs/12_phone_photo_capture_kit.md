# 12 — Phone Photo Capture Kit (V4 rate card)
**Resolves:** audit SC-08 · **Source requirements:** SOT **EDGE-04**, "A photo of a printed rate card, taken at an angle, on a phone." (p.1), and **EDGE-06**, "The angled photo." (p.2)
**Locked decision:** **DL-21**:
- the **primary demo fixture is a genuine phone photograph** of a printed vendor rate card, taken at an angle;
- the synthetic warped image is kept **only** for additional tests and perturbation variants;
- **an AI-generated or AI-edited image must never substitute for the real photograph.**

**Who takes it:** the project owner, on a real phone. **When:** after M1 has generated the final V4 values, because the printed card must contain exactly the ground-truth values.

---

## 1. Sequence
1. **M1 generator** renders `EVAL_ROOT/fixtures/v4_rate_card_print.pdf` from the truth spec (layout in §2). Ground truth = the values printed.
2. **The owner prints** it on plain A4 paper (§3).
3. **The owner photographs** it with a phone, following the capture protocol (§4).
4. **The owner sends back the original file**, unedited, exactly as the phone saved it (HEIC or JPEG).
5. **The builder registers** the photo (§5): it goes into the V4 `.eml` in `DATA_ROOT/inbox/`, the metadata is recorded in `EVAL_ROOT`, and the readability annotations are added to ground truth.
6. **T-EDGE-04 runs on the real photo** (primary) and on the synthetic variants (additional).

## 2. Rate card design (rendered by the generator; nothing here is a final value)
The card should look like a small local converter's printed price list.

| Element | Requirement | Why (SOT / test) |
|---|---|---|
| Header | Vendor trading name, address line, phone, "RATE LIST — CORRUGATED BOXES", a date | Realism (REQ-05) |
| Table columns | Sr. No. · Item / Size (L×W×H mm) · Ply · **Rate per 100 pcs (₹)** · Remarks | Unit stated in the header (EDGE-09) |
| Rows | The V4 lines from the truth spec (≈ 24–26 rows) | EDGE-04/06 |
| **Unlabelled rows** | 2 rows printed in a separate "Other items" block **without** a unit header, with values ~100× the per-box level | UNIT_SUSPECT path (EDGE-09, T-EDGE-09) |
| **Ambiguous digits** | At least one value with a 3/8 pair and one with a 1/7 pair, printed in a compact font at 9–10 pt | READ_DISAGREEMENT path (T-EDGE-04) |
| Footer | "Rates ex-works, GST extra as applicable. Subject to change with paper prices." | Terms extraction, realism |
| Font / size | A common sans font at 10–11 pt for the table body. No decorative fonts. | Readable but not trivial |
| Paper | Plain white A4, black ink, no colour | Realistic small-vendor print |

The generator also writes `v4_rate_card_truth.json` (in EVAL_ROOT) with every printed value and its row/column position.

## 3. Printing instructions
- Print `v4_rate_card_print.pdf` at **100% scale** (no "fit to page") on plain A4.
- Laser or inkjet, black only. Don't laminate.
- Fold it once across the middle and unfold it, so there's a slight crease as on a real card that has been handled. Optional but recommended.

## 4. Capture protocol (the photo must meet all of these)
| # | Requirement |
|---|---|
| 1 | **Device:** a real phone camera, using the phone's default camera app. No scanner apps, no "document mode", no auto-crop or auto-straighten. |
| 2 | **Angle:** hold the phone about **30–45° off perpendicular** (tilted, not straight down), so the card is clearly a trapezoid in the frame. |
| 3 | **Rotation:** the card is also rotated about **5–15°** within the frame. |
| 4 | **Framing:** the whole card is visible, including all four corners, with some table or desk surface around it. Fill about 60–80% of the frame. |
| 5 | **Lighting:** ordinary indoor light. A mild shadow or light gradient across the card is fine and realistic. **No flash.** Avoid glare that hides any digits completely. |
| 6 | **Focus:** tap to focus on the table. The text should be legible to a human, while some small digits may be soft. |
| 7 | **Surface:** an ordinary desk or table. The card lies flat or slightly curled. |
| 8 | **No edits:** don't crop, rotate, filter, enhance or run it through any AI tool. Send the **original file**. |
| 9 | **Take 3 shots** at slightly different angles. The builder selects the primary one using the §5 checks. The others are kept as extra real-photo test inputs. |

## 5. Registration and authenticity checks (builder, M1)
| Check | Pass condition |
|---|---|
| Original file | HEIC/JPEG straight from the phone. SHA-256 recorded in `EVAL_ROOT/fixtures/v4_photo_manifest.json`. |
| Camera metadata | EXIF present: device make/model, capture timestamp, no editing-software tag. Recorded in the manifest. **A file without camera EXIF, or with an AI/editing tag, is rejected.** |
| Angle present | Perspective correction (OpenCV quadrilateral) finds the card corners, and the measured skew is ≥ 20° off perpendicular |
| Legible to a human | The builder can read every printed value against `v4_rate_card_truth.json`. If a value is unreadable **to a human**, it is annotated as `human_unreadable` in ground truth (expected system outcome: UNRESOLVED, never a guess). |
| Ambiguous digits present | The planted 3/8 and 1/7 values are visible in the photo |
| Stored | The photo is attached to the V4 `.eml` in `DATA_ROOT/inbox/`. The manifest and annotations are in `EVAL_ROOT` only (DL-9/I7 isolation). |

## 6. Ground-truth annotation for the real photo
For each printed value, record in `EVAL_ROOT`: the printed value (from the truth JSON), the row/column, whether a human can read it in the photo (`clear` / `difficult` / `human_unreadable`), and the **expected status**:
- `clear` → EXTRACTED with the correct value. If the two reads disagree, UNRESOLVED (READ_DISAGREEMENT) is also acceptable, never a wrong EXTRACTED.
- `difficult` → EXTRACTED with the correct value, or UNRESOLVED.
- `human_unreadable` → UNRESOLVED.

**Silent-error rule:** a wrong value shown as EXTRACTED is a failure in every case.

## 7. What stays synthetic
The synthetic rendered-and-warped image (Plan M1) is kept for: the perturbation/unseen-seed runs (different warp angles), the negative fixtures, and CI tests that must not depend on the owner's photo. It is never shown as the primary demo fixture.

---

## 8. Owner-approved deviation — 2026-11-05: AI-generated image as V4's fixture

**Decision (owner):** no rate card is printed or photographed. One of three AI-generated images of the rate card, made by the owner with ChatGPT from `v4_rate_card_print.pdf`, is V4's image fixture. This deviates from **DL-21** ("an AI-generated or AI-edited image must never substitute for the real photograph") and weakens the demo evidence for **SOT EDGE-04/06** ("A photo of a printed rate card, taken at an angle, on a phone"; required test: "ideally a real phone photo of a printout"). It must be disclosed in the one-page note (DEL-03/04) and wherever V4 is shown.

**Labelling:**
- File name: `Shivam_rate_list__AI-generated-image.jpg`.
- Label in the manifest and the answer key: "AI-generated image (synthetic fixture), NOT a camera photograph".
- The app shows the file name wherever V4's source is shown (provenance drawer, exports).

**Registration (`EVAL_ROOT/generator/register_v4_image.py`):**
- `--source camera`: the §5 checks are unchanged (camera EXIF required; editing/AI tags and AI download origins rejected; angle thresholds).
- `--source synthetic-ai`: no camera EXIF is required, but a written provenance and a content check are. The same angle, distortion and OCR checks run, and their results are recorded. A failed check blocks registration unless the owner acknowledgement is given.
- A synthetic image can never pass the camera path; an eval lint asserts this.

**Selection:**
- **Image 1** was chosen.
- **Image 2** shifts the "Set" remarks one row up.
- **Image 3** misaligns values and remarks, and OCR finds 0 of 24 values even after flattening. As fixtures, both would encode a different card from the printed truth.

**Measured results for image 1** (recorded in `fixtures/v4_image/manifest.json`):
| Check | Kit requirement | Result |
|---|---|---|
| Camera EXIF | required (camera) | none — exempt as synthetic |
| Tilt off perpendicular | ≥ 20° | ≈ 0° (page outline near-frontal; keystone 1.003) — **FAIL, owner-acknowledged** |
| Rotation in frame | 5–15° | 2.2° — **FAIL, owner-acknowledged** |
| Distortion | — | non-uniform warping of the text rows inside the page (not a projective distortion) |
| Tesseract on the raw image | — | 0 / 24 printed values found |
| Tesseract after page flattening | — | 5 / 24 found, 0 on their own row |
| Content matches the print card | every value | yes, by the builder's (AI's) visual check — not a human check |

**Consequences:**
- The fixture does **not** exercise "taken at an angle".
- It does exercise a distorted, hard-to-read image: the expected product outcome is mostly UNRESOLVED (read disagreement or single source), never a guessed value (§6 silent-error rule).
