# Technical Architecture — Quote Intelligence Prototype
**Status:** v1.5 · PM review changes (DL-25…DL-32) · **Implements:** `docs/02_PRD.md` v1.5 · **Runbook:** `docs/10_demo_runbook.md` · **Decisions:** `docs/08_final_product_decisions.md` · **Fix log:** `docs/06_fix_log.md`
**Constraints:** one laptop, one builder, live demo, "stub the plumbing, AI loops must be real" (A-15).

Tags: **[A]** assignment · **[R]** recommendation · **[DL-n]** locked decision (PRD §0.1) · **(Bn/In)** review finding resolved here.

---

## 1. Architecture principles **[R]**

1. **AI reads, code calculates.** Every number on screen is computed by deterministic code.
2. **A pipeline, not agents.** A fixed two-phase ingestion pipeline. Only the NL analyst loops, and that loop is bounded and read-only.
3. **Provenance is part of the data model.** Every value points to EvidenceUnits.
4. **Determinism starts at stored raw facts (I6).** AI extraction is not repeatable. Everything after the stored raw facts is: same inputs → byte-identical outputs, in any processing order (DL-9).
5. **Unresolved never enters calculations (DL-10); NEEDS_REVIEW never enters a formal award without buyer review or an audited override (DL-16).** Inclusion is decided by the canonical status table plus the calculation context (formal / exploratory), in one module.
6. **Fail visibly.** Every stage reports an explicit status. Nothing is half-applied.
7. **Ground truth is unreachable at runtime (I7).** Enforced by layout, a runtime guard and tests, not by convention.
8. **Boring infrastructure.** One process, SQLite, local files.

---

## 2. System overview

```
┌──────────────────────────── Browser (React SPA) ─────────────────────────────┐
│ Co-pilot │ Vendors/Inbox │ Review │ Comparison │ Analyst │ Award │ Settings  │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ REST + SSE
┌───────────────────────────────▼──────────────────────────────────────────────┐
│                       Backend (Python 3.12, FastAPI)                          │
│                                                                               │
│  PHASE A — per response (concurrent, ≤5)                                      │
│   parse → EvidenceUnits → AI extract (TEXT | OCR-structuring ∥ VISION)        │
│   → evidence verify → photo reconcile → AI match + spec diff                  │
│   → per-cell normalise → Phase A checks → store                               │
│                                                                               │
│  PHASE B — global, single-threaded, after all responses processed (DL-9)      │
│   leave-one-out peer medians → magnitude/outlier/plausibility checks          │
│   → status precedence → resolutions applied → eligibility roll-ups            │
│   → review items → snapshot hash → scenarios stale-marking                    │
│                                                                               │
│  Recompute trigger (any edit / FX / estimate / re-run / upload)               │
│   → re-normalise affected cells → full Phase B                                │
│                                                                               │
│  Analysis core (deterministic): views · scenario engine · savings ·           │
│   caveats · grounding check · label lint · chart binder                       │
│  LLM gateway: SDK client · schemas · prompts · append-only conversations ·    │
│   call log                                                                    │
│  Storage guard: all file I/O confined to DATA_ROOT (I7)                       │
└─────────┬───────────────────────────┬───────────────────────────┬─────────────┘
     ┌────▼─────┐             ┌───────▼────────┐          ┌───────▼────────┐
     │ SQLite   │             │ DATA_ROOT/     │          │ Claude API     │
     │ app.db   │             │ seed inbox     │          └────────────────┘
     └──────────┘             │ storage        │
                              └────────────────┘
   (outside the app's reach)  EVAL_ROOT/ : generator · truth specs · answer keys · oracle
```

---

## 3. Technology choices

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + TypeScript + Vite, TanStack Table, Vega-Lite (vega-embed), Tailwind | Custom cells/badges. Charts are declarative specs with data bound by the backend. |
| Backend | Python 3.12, FastAPI, Pydantic v2 | Best document-parsing ecosystem. One schema source for the API, the DB and LLM outputs. |
| DB | SQLite + SQLAlchemy 2.0. Analyst uses a separate read-only connection (`mode=ro`). Money stored as Decimal strings / integer paise (I6). | Zero ops. Exact money. |
| Jobs | In-process asyncio runner + `jobs` table. Phase A concurrency 5. Phase B under a single global lock. | No broker needed. Phase B serialisation gives determinism. |
| Email | Stubbed outbox table + `.eml` inbox in DATA_ROOT + upload | A-15 |
| LLM | Anthropic Python SDK, `claude-opus-5-5`, adaptive thinking, **effort set explicitly on every route** (the default is `medium`) (I9) | One model, fewer variables |
| xlsx / xls / csv | openpyxl (.xlsx), **xlrd (.xls)**, csv stdlib (I9) | Cell provenance |
| docx | python-docx **plus direct OOXML traversal**: body children in document order (paragraphs and tables interleaved) and the `footnotes.xml` part (I9) | python-docx alone skips footnotes and doesn't interleave paragraphs and tables |
| PDF | PyMuPDF (blocks + bbox, page render) | Bboxes, scanned fallback |
| Image | Pillow + **pillow-heif** (.heic) (I9), OpenCV (perspective/deskew/CLAHE), **Tesseract** (system dependency) | Correction + OCR boxes |
| Setup | `make doctor` checks Tesseract, language data and Python deps, with fix hints. Optional Dockerfile with Tesseract preinstalled. (I9, NF-7) | Tesseract is a system dependency |
| SQL safety | sqlglot allowlist | Read-only analyst |
| Export | openpyxl, Jinja2 (Markdown/HTML) | — |
| Tests | pytest, Hypothesis (property tests), Playwright smoke | — |

---

## 4. Frontend

| Screen | Key components | PRD |
|---|---|---|
| Co-pilot | Chat with **file attachments** (brief pack, RFX-9) + RFx editor (incl. reference unit weight + source per line; source citation per line and question) + patch diff + completeness badges + **conformance panel** (Conforms / differences, RFX-10) + RFx header showing `origin` and a transcript link (RFX-11). RFx switcher (primary / **sandbox**; neither changes the canonical spec or the prepared dataset, DL-17/19). | J1, RFX-* |
| Vendors & Inbox | Status chips (**Awaiting response** / Received / Processing / Processed / Failed, SC-10), outbox incl. **clarification requests awaiting approval** (DL-20), deliver, upload, **re-run** per response | J2, J3, J8, J9, EXT-11 |
| Review | Queue (blocking first, then by money at risk). Source viewers: image crop with **both reads side by side**, sheet grid, highlighted text. **Reference panel (DL-20):** the vendor's phrase, reading A (lines + candidate prices + baseline citations), reading B (terms + candidate terms), "Generate clarification request" (template preview → edit → approve → outbox), and "Confirm reading" (prices / terms / both / neither + source note, audited). | J4, J9 |
| Comparison | Grid + basis toggle + canonical badges + flags + baseline column + **Provisional banner** + provenance drawer. Vendor panel shows **Quality / Commercial eligibility separately**. | J5, CMP-* |
| Analyst | Answer blocks + Method/Interpretation/Filters/Exclusions/Assumptions/Caveats + Show work + correction notes | J6 |
| Award | Scenario params (no cap in P0), **formal context**. The NEEDS_REVIEW exclusion is on by default; an override dialog shows a warning, the cell list and money at risk, and requires a reason (audited, DL-16). Results, savings with coverage statements, readiness, memo, stale/superseded markers. | J7 |
| Settings | FX rates (rate, as-of date, source; DL-15), freight estimates, **constant-set versions** (view constants with validation status; activate an existing version, audited; DL-18) | NRM-4/5, PRD §5.11 |

Rules:
- A single `StatusBadge` reads the canonical enum. Excluded statuses render as a chip, never a number.
- The UI does no business arithmetic.
- `EligibilityLabel` is the only component that renders eligibility words. It maps `FAIL→"Failed"`, `UNVERIFIED→"Unverified"`, and nothing else.

---

## 5. Backend

### 5.1 Repository and data layout (I7)
```
<repo>/
  backend/app/
    api/  domain/  db/  llm/  storage/        # storage/ = the ONLY module that opens files
    ingest/{parsers,extract.py,vision.py,reconcile.py,verify.py,match.py,phase_a.py}
    process/{phase_b.py,recompute.py,resolutions.py}
    normalize/{units.py,weight.py,fx.py,freight.py,gst.py,discounts.py,slabs.py,baseline.py,engine.py,money.py}
    validate/{checks_a.py,checks_b.py,status.py}      # status.py = canonical table (PRD §6)
    eligibility/rules.py
    analysis/{views.sql,sql_tool.py,scenario.py,savings.py,charts.py,caveats.py,grounding.py,label_lint.py,analyst.py}
    award/  export/  audit/  mail/  copilot/
  backend/config/{constants/v1.yaml (versioned constant sets),unit_dictionary.yaml,fx.yaml}
  backend/tests/                 # unit/contract tests; NO ground truth here
  frontend/
  app_data/                      # = DATA_ROOT (the app may read/write only here)
    seed/{brief_pack/, canonical_rfx.json, baseline, vendors}   inbox/   storage/   app.db
<sibling, outside the repo>/aerchain-eval/   # = EVAL_ROOT (never configured for the app)
  generator/  truth/  answer_keys/  oracle/  eval_tests/  reports/
```
**Controls:**
1. `storage.safe_path()` resolves symlinks and refuses any path outside `DATA_ROOT`. All app file I/O goes through it.
2. A static test (AST scan) fails the build if any app module calls `open`, `Path.read_*`, `pd.read_*` or `openpyxl.load_workbook` outside `storage/`. It also fails on any reference to `EVAL_ROOT`, `answer_key` or `truth`.
3. At startup the app refuses to run if `EVAL_ROOT` is set in its environment, or if `DATA_ROOT` contains or overlaps `EVAL_ROOT`.
4. The generator writes only *inputs* (RFx seed, baseline, inbox artefacts) into `DATA_ROOT`. Truth specs and answer keys stay in `EVAL_ROOT`.
5. Eval tests run in a separate process that gets `EVAL_ROOT` and talks to the app only through its HTTP API.

### 5.2 Core API
| Method & path | Purpose |
|---|---|
| `POST /rfx/{id}/copilot` (SSE, multipart attachments) · `POST /rfx/{id}/patches/{pid}/apply` · `POST /rfx/{id}/conformance` · `POST /rfx/{id}/approve` · `POST /rfx/load-fallback` | Co-pilot, conformance (RFX-10), labelled seeded fallback (DL-19) |
| `POST /rfx/{id}/send` · `POST /inbox/deliver` · `POST /responses/upload` | Mail stub, upload |
| `POST /responses/{id}/rerun` | P0 basic re-run (EXT-11) |
| `GET /processing/{rfx}` (SSE) | Phase A/B progress, Provisional/Final |
| `GET /comparison?basis=` · `GET /cells/{line}/{vendor}` | Grid (incl. awaiting-vendor columns, SC-10), provenance |
| `GET /vendors/{id}/documents` · `GET /documents/{id}` (metadata + facts) · `GET /documents/{id}/file` (original bytes) · `GET /documents/{id}/view?evidence_ref=` (viewer page with highlight) | Documents openable from the comparison (SC-11) |
| `GET /references/{id}` · `POST /vendors/{id}/clarification-pack` (per-vendor template pack, incl. the reference section) · `PUT /clarification-packs/{id}` (buyer edits) · `POST /clarification-packs/{id}/approve` (→ outbox) · `POST /references/{id}/confirm` | DL-20, DL-32 |
| `GET /review` · `POST /review/{id}/resolve` | Resolutions (→ recompute) |
| `PUT /fx/{ccy}` · `POST /freight-estimates` · `POST /constants/{version}/activate` | Assumptions and constant-set activation (audited → recompute) |
| `GET /eligibility` · `POST /eligibility/override` | Eligibility (→ recompute) |
| `POST /analyst/sessions/{id}/ask` (SSE) | Analyst |
| `POST /scenarios` · `POST /scenarios/{id}/recompute` · `POST /scenarios/{id}/needs-review-override` | Scenarios (formal/exploratory), audited NEEDS_REVIEW override |
| `POST /awards` · `POST /awards/{id}/acknowledge` | Award |
| `GET /exports/...` · `GET /audit` | Exports, audit |

### 5.3 Two-phase processing and recompute (DL-9, B2)
- **Phase A** (`ingest/phase_a.py`) runs per response. It writes raw facts, matches, per-cell normalised values (`phase_a_value`, `phase_a_reasons`) and fingerprints. It never reads another vendor's data.
- **Phase B** (`process/phase_b.py`) runs when the processing set has no response left in `received/processing`. It runs under a global lock, and its inputs are read in a canonical order (line_no, vendor_id):
  1. Leave-one-out peer median per cell, computed from **Phase A** numeric values of other vendors, excluding Phase A UNRESOLVED/NOT_CONVERTIBLE/MISSING.
  2. `checks_b`: UNIT_SUSPECT (≥ 20× or ≤ 1/20× the reference), OUTLIER (outside [0.5×, 2×]), plausibility reference availability (≥ 2 peers, else a same-line awarded baseline, else `PLAUSIBILITY_UNCHECKED` → cap EXTRACTED).
  3. Apply active `Resolution`s (§6.5 of the PRD): sticky. New failures on resolved cells → `NEW_WARNING_AFTER_REVIEW`.
  4. `status.py` precedence → unit status, then landed status.
  5. Eligibility roll-ups per section.
  6. Review items (blocking and advisory).
  7. Comparison snapshot hash; any scenario whose `cells_used` fingerprints changed is marked stale; acknowledged awards affected are marked superseded.
- **Recompute** (`process/recompute.py`): any mutation → re-normalise the affected cells (Phase A normalisation only, no AI) → **full Phase B**. With 150 cells this takes < 2 s (NF-4). There's no partial dependency tracking to get wrong.
- **Provisional state:** while Phase B is pending, `/comparison` returns `provisional: true`. Analyst and award endpoints return 409 "comparison not final".
- **Submissions (DL-23):** an inbound message is matched to (RFx, vendor) by sender and thread. If the vendor already has a Response for that RFx, the message is **added as a submission** to it (no new Response, no revision semantics). Its documents go through Phase A, then the global recompute. The V5 quote email is stored and parsed unchanged.
- **Awaiting vendors (SC-10):**
  - The processing set is defined over **received** responses only. An invited vendor with no response has `Invitation.status = AWAITING_RESPONSE`, **no `NormalizedQuote` rows**, and appears in the comparison payload as `{vendor_id, state: "AWAITING_RESPONSE"}`.
  - Phase B, the scenario engine, savings and the caveat engine read the candidate vendor set as `responded vendors only`. They add `awaiting_response: [vendor_ids]` to every result's exclusions.
  - Nothing ever materialises a zero or a MISSING row for an awaiting vendor. A **property test** checks that no `NormalizedQuote` exists for an awaiting vendor.
  - A late arrival goes through Phase A → global recompute.
- **Determinism test hook:** Phase B is a pure function of (Phase A rows, resolutions, assumptions, config). Tested by permuting the input order.

### 5.4 Money (I6)
The `normalize/money.py` Decimal context: unit prices are quantised to 4 dp; line annual totals = round_half_up(unit × qty, 0); totals = sums of line totals; percentages to 1 dp. No floats in normalisation, scenario, savings or export. The SQL views expose Decimal-as-text plus integer paise, so the analyst's SQL aggregates on exact values.

---

## 6. Document ingestion & OCR

### 6.1 EvidenceUnits
| Format | Parser | Locator |
|---|---|---|
| .eml | stdlib `email`. Body lines. Attachments become child Documents. | line_no |
| .xlsx | openpyxl: every non-empty cell, displayed value, merged ranges, sheet | sheet!cell |
| .xls | xlrd → same unit model | sheet!cell |
| .csv | stdlib csv | row, col |
| .docx | OOXML traversal: `w:body` children in order (`w:p`, `w:tbl`→cells), plus `footnotes.xml` entries as their own units tagged `footnote` | para_idx / tbl,r,c / footnote_id |
| .pdf digital | PyMuPDF blocks + bbox | page, bbox |
| .pdf scanned | render page → image path | page, bbox |
| image | Pillow(+heif) → OpenCV quadrilateral warp (fallback: Hough deskew) → CLAHE → Tesseract lines + word confidences | bbox on corrected image |

Parse failure → Document `FAILED` with a reason. The other documents in the response continue.

### 6.2 Independent photo reads (DL-11, B4)
Two paths start from the **same corrected image** and run in parallel. Neither sees the other's output.

| | Path O (OCR) | Path V (Vision) |
|---|---|---|
| Input to the model | OCR EvidenceUnits as text + RFx context. **No image.** | Corrected image + RFx context. **No OCR text, no OCR boxes.** |
| Output | Line quotes citing OCR unit ids (`value_as_stated` = OCR reading) | Line quotes with `image_read_value`, unit as read, row order index, and an approximate region (row band, top→bottom) |
| Evidence verification | §7.3 (quote must appear in the cited OCR line) | Not applicable (no text units) |

**Reconciliation** (`ingest/reconcile.py`, deterministic):
1. Both paths go through matching (§7.5) independently. Pair rows by matched `rfx_line_id`. Any remaining rows are paired by row order index, and the vertical band must overlap the OCR bbox.
2. For each pair, normalise both numbers (digit grouping, ₹/Rs) and compare value + unit class:
   - **Equal** → keep the Path O fact (OCR evidence, crop = OCR bbox), status cap EXTRACTED.
   - **Different** → `UNRESOLVED (READ_DISAGREEMENT)`, both candidates stored, crop shown.
   - **Only one path has a value** for the line → `UNRESOLVED (READ_SINGLE_SOURCE)`.
   - OCR mean word confidence < 80 on the cited line → at least `UNRESOLVED (LOW_OCR_CONFIDENCE)`, even if the two reads agree.
3. A Path O evidence failure is reported as `EVIDENCE_NOT_FOUND`. A disagreement between paths is **never** reported as `EVIDENCE_NOT_FOUND`.
4. **Request-inspection test:** the Path V request payload contains no OCR strings (asserted on the gateway call log).

---

## 7. AI extraction

### 7.1 LLM gateway (I9)
- Model `claude-opus-5-5`. `thinking: {type: "adaptive"}`. **Explicit effort on every call:** extraction/vision/matching `high`, analyst and co-pilot `medium` (tuned via evals). Sampling parameters are not used (not accepted by the model). Extraction is therefore not deterministic, and the design doesn't need it to be (principle 4).
- Structured outputs (`messages.parse` / `output_config.format`) from the Pydantic schemas. Native citations aren't used, because they're incompatible with structured outputs. EvidenceUnit ids do that job.
- Tools: `strict: true`, `tool_choice: auto` (forced tool choice is not supported on this model).
- `stop_reason` is checked on every response. `refusal`/`max_tokens` → stage FAILED. Server-side refusal fallback is enabled.
- **Retry policy:**
  - Transport/429/5xx: the SDK retries (max 2) with the **identical request body**.
  - Application-level retry of a failed extraction stage re-runs the stage from scratch (a single-shot call, no conversation).
  - **Conversations (analyst, co-pilot) are append-only:** the stored history = the exact `response.content` blocks returned (including thinking blocks), never edited, reordered or trimmed.
  - Regeneration after a grounding/lint failure appends a feedback message (a mid-conversation `system` message) after the rejected answer and requests a new answer. The rejected answer stays in history, marked rejected in our DB.
  - A turn that fails permanently (after retries) is not appended. The session continues from the last successful assistant turn, and the user sees "that question failed — retry".
- Streaming for long calls. Every call is logged in `llm_calls` (route, path, model, prompt_version, input sha, tokens, latency, stop_reason, request summary for the inspection tests).
- Prompts are versioned files. A hygiene test bans dataset vendor names, SKU codes and price literals (the banned list is generated in EVAL_ROOT and passed to the test runner, not stored in the repo).

### 7.2 Extraction schema (abridged)
```
DocumentExtraction {
  line_quotes: [{
    vendor_line_ref, description_as_stated, item_code?,
    price: {value_as_stated, value?, currency_as_stated?, currency_source: STATED|INHERITED_FROM_CONTEXT|NONE, evidence:[unit_id]},
    unit_as_stated?, unit_class, unit_source: STATED|INHERITED_FROM_CONTEXT|NONE,
    unit_inherited_from?: {evidence:[unit_id], quote},          # DL-12
    slabs?: [{min_qty?, max_qty?, value_as_stated, evidence}],  # EXT-14
    quoted_spec?, vendor_box_weight_g?: {value, evidence},
    applies_to_group?: {attribute: "ply", value: int, evidence},
    flags: [ambiguous_unit|illegible|conflicting_values|unclear_scope]
  }],
  document_terms: [{type (incl. TOOLING, ESCALATION), value?, unit?, scope, text, evidence}],  # EXT-13
  references: [{type, scope_text, evidence}],
  questionnaire_answers: [{question_id, answer_value?, answer_text, evidence, attachment_refs}],
  document_facts?: {doc_type?, entity_name?, issue_date?, expiry_date?, standard?, evidence}
}
VisionExtraction { rows: [{row_index, band, description_as_read, image_read_value, unit_as_read?, flags}] }
```
Prompt rules: copy values as stated. Never convert. Null when unsure. Cite everything. For an elliptical price, set `unit_source=INHERITED_FROM_CONTEXT` only when the unit appears earlier in the same sentence or clause, and cite it.

### 7.3 Evidence verification (`verify.py`)
- Cited units exist. `value_as_stated` appears in the cited text (whitespace, Indian grouping and ₹/Rs/INR normalised). The parsed number equals `value`.
- **Inheritance check (DL-12):** the `unit_inherited_from` quote appears in its cited unit. That unit is the same unit as the price, or an adjacent unit in the same message. The quote contains a recognised unit token, and no other unit token sits between the source and the price. Otherwise → `unit_class=UNKNOWN`, `UNRESOLVED (UNIT_UNKNOWN)`.
- Failure → `UNRESOLVED (EVIDENCE_NOT_FOUND)`.

### 7.4 Unit classification cross-check (I9)
`unit_dictionary.yaml` maps known strings to classes. The dictionary agrees → accept. It knows the string and disagrees → UNKNOWN. **It doesn't know the string → no opinion**: the AI class is accepted with the flag `UNIT_DICT_UNSEEN` (which blocks auto-VERIFIED). New strings seen in evals are added to the dictionary only from the generic synthetic set, never from the demo set.

### 7.5 Line matching
Deterministic pre-match (item code, or exact dims + ply) → an AI proposal for the rest (structured) → a one-to-one check (`MATCH_CONFLICT`) → a spec diff using the tolerances in the active constant set → COMPLIANT / ALTERNATE / NOT_RESTATED. **Group expansion** (EXT-8) is deterministic: a group statement {attribute: ply, value} applies to every RFx line with that ply that the vendor didn't price individually, of any item type. The weight-source hierarchy and item-type check happen in normalisation, never here.

---

## 8. Normalisation engine (`normalize/`)

Pure functions, Decimal arithmetic, `engine_version` stamped on each row.

| Step | Module | Rule |
|---|---|---|
| 1 Slab selection | `slabs.py` | The slab containing annual_qty. None or several → `SLAB_AMBIGUOUS` (P0, B6). |
| 2 Qty-unit | `units.py` | ÷100/÷1000/÷12. Flag CONVERTED. UNKNOWN → stop. |
| 3 Weight | `weight.py` | **Weight-source hierarchy** (PRD §5.2, DL-18): (1) `RfxLine.reference_unit_weight_g` → **ASSUMED (REFERENCE_WEIGHT)** (DL-31), trace cites `reference_weight_source`; (2) vendor-stated weight → CONVERTED, cross-checked against the reference (mismatch → NEEDS_REVIEW (WEIGHT_MISMATCH)); (3) estimate from the **active constant set** (RSC blank / flat blank, supported types only) → NEEDS_REVIEW (WEIGHT_ESTIMATED) + METHOD_CONSTANTS assumption; (4) otherwise NOT_CONVERTIBLE; failed weight evidence → UNRESOLVED. Records `weight_source`, `weight_g`, `constant_set_version`. Each constant in the trace carries its validation label. Flute→medium mapping in layer order. Internal-dimension disclosure. | Every per-kg line also records `billed_weight_exposure_per_1pct = 0.01 × annual qty × ₹/box` for the caveat (DL-31).
| 4–5 Discounts | `discounts.py` | Line, then document, within scope. Unclear scope → UNRESOLVED. |
| 6 GST | `gst.py` | Back out at a stated rate. **Vendor silent → apply `Rfx.response_basis.gst_treatment` as ASSUMED (GST_PER_RFX_BASIS), recorded in the assumption ledger (DL-26).** RFx basis undefined or the statement ambiguous → UNRESOLVED (GST_UNCLEAR). The extraction schema distinguishes `gst_statement: SILENT / STATED(text) / AMBIGUOUS(text)`. |
| 7 FX | `fx.py` | ASSUMED (FX_RATE), flag FX. Original currency and amount kept. Trace shows the rate, as-of date and source (DL-15). Records `fx_exposure_per_1pct = 0.01 × INR value` per cell for the V2 exposure disclosure (DL-30). |
| 8 Freight | `freight.py` | Basis table (PRD §5.4), **from this year's response only**. No statement → UNKNOWN. Never reads baseline freight (DL-8). Landed computed only for INCLUDED/STATED/ESTIMATED. |
| 9 Baseline reference | `baseline.py` | **DL-8 + DL-20:** for an ambiguous reference, compute **candidates** for reading A (same vendor_id **and** same `spec_signature` → candidate price; same vendor with a different signature → BASELINE_SPEC_CHANGED; otherwise BASELINE_NOT_FOR_VENDOR, never another vendor's row) and reading B (same vendor's `BaselineTerm` for unstated term types; **never freight**). All affected cells are **UNRESOLVED (REFERENCE_AMBIGUOUS)**, with candidates stored in `Reference.candidates`. **Candidates are applied only when an active `REFERENCE_CONFIRMATION` resolution exists**: "prices" → ASSUMED (BASELINE_REFERENCE); "terms" → `DocumentTerm(CONFIRMED_HISTORICAL)`. Baseline freight is never returned. FREIGHT_BASIS_CHANGED is a caveat only. |
| 10 Annual | `engine.py` | Decimal; rounding per §5.4 |

Trace entry: `{step, label, inputs, op, constants, output, source_refs}`.

---

## 9. Validation & status (`validate/`)

| Phase | Check | Result |
|---|---|---|
| A | evidence / inheritance | UNRESOLVED (EVIDENCE_NOT_FOUND / UNIT_UNKNOWN) |
| A | unit present | UNRESOLVED (UNIT_UNKNOWN) |
| A | photo reconcile | UNRESOLVED (READ_DISAGREEMENT / READ_SINGLE_SOURCE / LOW_OCR_CONFIDENCE) |
| A | arithmetic | NEEDS_REVIEW (ARITHMETIC_MISMATCH) |
| A | intra-response conflict | UNRESOLVED (PRICE_CONFLICT) |
| A | weight mismatch > 10% | NEEDS_REVIEW (WEIGHT_MISMATCH) |
| A | GST / slab / match / baseline | UNRESOLVED (respective codes) |
| **B** | unit magnitude vs leave-one-out reference | UNRESOLVED (UNIT_SUSPECT) + suggestion, **excluded** |
| **B** | outlier | NEEDS_REVIEW (OUTLIER): excluded from formal awards by default, included in exploratory analysis with a warning (DL-16) |
| **B** | no plausibility reference | flag PLAUSIBILITY_UNCHECKED, cap EXTRACTED |

`status.py` holds the canonical table (PRD §6.2–6.4) as data: `{status: {has_number, formal_default, exploratory_default}}`. Scenario, caveat, export and grid code all call `status.includable(cell, context, policy, override?)`:
- `context=formal` + default policy → only VERIFIED/EXTRACTED/ASSUMED are includable.
- `include_needs_review` in formal context requires a valid `override` record (warning + audit) or the call raises.
- `context=exploratory` may include NEEDS_REVIEW on request; the results are tagged `exploratory=true`.

UNRESOLVED/NOT_CONVERTIBLE/MISSING are never includable. **No other module decides inclusion.** Thresholds come from the active constant set (PRD §5.11).

---

## 10. Eligibility (`eligibility/rules.py`)
Per question → **applicability check first** (DL-24/29: line-scoped questions are evaluated per vendor but **excluded from vendor roll-ups**. They produce a `line_gate(vendor, flag)` used by the scenario engine to admit or exclude cells on flagged lines. The primary RFx has no FSC question. `ALL`, or a line flag `food_contact` / `requires_fsc` that is present in the RFx and quoted by the vendor). Not applicable → `NOT_APPLICABLE` (with reason, excluded from roll-ups). Otherwise PASS/FAIL/UNVERIFIED (PRD §5.7). Roll-ups for `quality`, `commercial` and `all_mandatory`. **Only `quality` is used for "cleared the quality questionnaire"** (DL-14). `all_mandatory` is labelled "quality and commercial requirements". Pure function. Label mapping is shared with `label_lint.py`.

---

## 11. Natural-language analysis

### 11.1 Loop
A manual SDK tool loop, ≤ 8 tool calls, `tool_choice: auto`, append-only history (§7.1).

**Tools:**
| Tool | Purpose | Pri |
|---|---|---|
| `query(sql)` | SELECT on approved views → `result_id` | P0 |
| `run_scenario(params)` | Scenario engine + savings → `result_id` with `cells_used` | P0 |
| `get_eligibility(scope, mode)` | Typed eligibility listing with reasons | P0 |
| `get_evidence(evidence_ref)` | Returns **one cited evidence snippet** (≤ 400 chars, marked untrusted vendor content) + document name + locator. Only refs that appear in a fact, answer or quote row are resolvable. (SC-02) | P0 |
| `make_chart(result_id, spec_without_data)` | Bound chart. `charts.py` injects the result rows as the spec's only data source (`data.values`) and **rejects any spec containing inline data, transforms that create values, or fields not in the result** (SC-09). | P0 |
| `export(result_id, fmt)` | File. Written from the stored result rows: Decimal values as text, plus vendor name and id, line number, unit/currency label and status/flag columns, and an Exclusions/Caveats sheet (SC-09). | P0 |
| `fx_sensitivity(ccy, pct)` | — | **P1** (no demo dependency) |

**Steering (NLA-10, I8):** the system prompt and tool descriptions say that award, split, savings and eligibility-filtered cost questions **must** use `run_scenario`. In the analyst, `run_scenario` defaults to the formal policy (NEEDS_REVIEW excluded, DL-16). `include_needs_review` is allowed only with `context=exploratory`, and the answer then carries the "Exploratory — includes N values needing review" label (added by code). The eval checks that every award-type answer's numbers come from `run_scenario` results.

### 11.2 Approved views
`v_lines`, `v_quotes` (canonical status, `includable_formal`, `needs_review`, freight basis, flags, Decimal-as-text + paise), `v_vendors` (quality/commercial/all eligibility, **coverage_count, missing_line_nos**), `v_eligibility` (section, state, reason), `v_terms` (+ `evidence_ref`), `v_assumptions`, `v_baseline` (vendor, awarded, spec_match).

**Document and answer views (SC-02, PRD NLA-11…13):**
| View | Columns | Notes |
|---|---|---|
| `v_questionnaire_answers` | vendor_id, question_id, requirement_key, section, question_text, answer_value, **answer_text (verbatim, ≤ 400 chars)**, state (PASS/FAIL/UNVERIFIED), reason, evidence_ref | One row per vendor × question. Unanswered → answer null, state UNVERIFIED. |
| `v_document_facts` | vendor_id, document_id, document_name, doc_type, standard, certificate_number, entity_name, issue_date, expiry_date, fact_status (EXTRACTED/VERIFIED/NOT_EXTRACTED), evidence_ref | Null = not extracted. Never inferred. |
| `v_certificates` | vendor_id, document_id, standard, certificate_number, entity_name, expiry_date, **valid_on_rfx_date, valid_through_contract_end, entity_matches_vendor** (computed by code), evidence_ref | Derived validity is deterministic |
| `v_evidence_index` | evidence_ref, vendor_id, document_name, locator, kind | **No text column.** Snippets only via `get_evidence`, and only for refs referenced by the views above. |

**Guardrails:**
- There is no view or tool that returns full document text.
- Snippets are capped, wrapped as untrusted vendor content (PRD AI-16), and resolvable only for cited refs.
- Views are read-only on the `mode=ro` connection.
- Every fact row carries an `evidence_ref`.
`v_quotes` exposes `includable_formal` (DL-16) and `needs_review`. The system prompt requires filtering on `includable_formal` unless the user asks for exploratory inclusion. `v_quotes` also exposes `original_currency`, `original_price` (DL-15), `weight_source` and `constant_set_version` (DL-18). The caveat engine independently reports any excluded cells that appear in a result.

### 11.3 Scenario engine & savings (`scenario.py`, `savings.py`)
Params per PRD AWD-1 (no cap in P0; `context` formal/exploratory; default `exclude_needs_review`; **default basis `freight_aware` for formal**).
- **Freight-aware selection (DL-25):** per line, compute K (calculable landed) and U (UNKNOWN freight). Apply PRD §5.4. Emit `freight_status ∈ {ROBUST, FREIGHT_DEPENDENT, FREIGHT_UNKNOWN_ALL}` and `break_even_inr_per_box = best_K − best_U` (Decimal, 4 dp). Savings on dependent lines are flagged as lower bounds.
- **Decision sensitivity (DL-28), `analysis/sensitivity.py`:** for each line, enumerate the uncertain inputs on its candidate cells:
  - (a) UNRESOLVED cells with candidates (unit suggestion, alternative reading, reference candidate): re-run the line's selection with each candidate admitted;
  - (b) excluded NEEDS_REVIEW cells: re-run with the cell included;
  - (c) ASSUMED FX or reference-weight cells: compute the **flip margin %** (the relative change in that value needed to change the winner);
  - (d) unknown freight: the break-even from (DL-25).

  The line is `DECISION_SENSITIVE` if (a) or (b) changes the winner, or (c)/(d) exist with a finite flip margin or break-even. Impact = annual ₹ delta for (a)/(b), margin % for (c), ₹/box for (d). This is pure re-evaluation of the existing per-line selection, with no new model calls. Candidate cells = `status.includable(context, policy, override)` ∧ eligibility(scope, mode) ∧ compliance (alternates per toggle) ∧ basis availability. Per line minimum with the disclosed tie-break. Savings exactly per PRD §5.9 (baseline subset A_b, best-single-vendor comparator by max coverage then total). Output includes coverage statements and `cells_used` with fingerprints.

### 11.4 Caveat engine
Gathers cells used (scenario `cells_used`; SQL results keyed by (rfx_line_id, vendor_id); otherwise the filter scope; otherwise the whole comparison). Reports:
- counts by canonical status;
- assumptions by type;
- mixed freight bases;
- alternates;
- **eligibility exclusions split into Failed / Unverified**;
- any non-includable cell found in a result (marked "excluded value appeared in result");
- **exposures (DL-30/31):** "V2 FX exposure: ₹X per 1% USD/INR move" (sum over V2 cells used); "Billed-weight exposure: ₹Y per 1% weight variance across N per-kg lines";
- **freight dependency and sensitivity (DL-25/28):** freight-dependent lines with break-even; the decision-sensitive count with the top impact;
- **coverage disclosure (SOT EDGE-07):** for every vendor in the result whose `coverage_count` < line count, "V3: 27/30, missing lines 8, 14, 22";
- **fact provenance:** source links for every document-fact or answer row used (NLA-12).

### 11.5 Grounding check
Every narrative numeral must match a tool-result value at displayed precision (PRD §5.10), or a count derived from results. **Extended (NLA-12):**
- dates (any format), certificate numbers and entity names in the narrative must match a value in a result row that carries an `evidence_ref`;
- a claimed fact about a vendor/document with no row (or with a NOT_EXTRACTED row) fails grounding (NLA-13).

Failure → one appended-feedback regeneration (§7.1) → banner + raw tables.

### 11.6 Eligibility label lint (I2)
After grounding: tokenize the narrative. For each vendor name or id mentioned, look within the same sentence for the fail family (fail, failed, failing, rejected, disqualified, "did not clear", "didn't qualify"). If found and the vendor's state in the answer's stated scope ≠ FAIL → regenerate once (appended feedback). If it still fails → a code-generated correction note is attached. The same lint runs on memo rationale paragraphs.

### 11.7 Answer schema
`{narrative, blocks[], method_steps[], basis, interpretation?, filters[], follow_ups[]}` + code-added `{exclusions, assumptions, caveats, grounding, lint}`.

---

## 12. RFx co-pilot
One structured call per turn on an append-only conversation → `{message, questions[], patch[]}`. Patches are validated against the schema (RFX-3/4 rules incl. section and construction completeness). Targets the selected RFx (primary or sandbox). Can't approve or send.

**Brief-pack attachments and deterministic item-master import (RFX-9, DL-27):** attached files are parsed by the same parsers (§6.1) into EvidenceUnits under the RFx.
- For the item master, the co-pilot receives **only the header row plus 3 sample rows** and returns a structured `column → RfxLine field` mapping with confidence. The buyer confirms or edits it.
- `rfx/import_item_master.py` then creates all lines **deterministically** from the cells (no model call), normalises units by rule, cites each source row, and runs the completeness check.
- The co-pilot receives the gap list and asks about the gaps. Questionnaire and terms patches cite checklist and policy units.
- The gateway log must show no model output containing line values.

**Conformance (RFX-10, DL-19):** `rfx/conformance.py` is a pure function of (drafted RFx, `CanonicalRfxSpec`). It compares SKU sets; per SKU: item type, dims, ply, flute, layer GSMs/BF, printing, annual qty, reference weight; questionnaire `requirement_key` set + section + pass rule; response basis. It returns `{conforms, differences[]}`. **The co-pilot never receives the canonical spec** (PRD AI-17). `inbox/deliver` refuses to deliver prepared responses to an RFx whose latest conformance result isn't `conforms=true`.

**Provenance (RFX-11):** the RFx stores `origin`, the transcript id, accepted patches and the conformance result. `POST /rfx/load-fallback` creates an RFx from the canonical spec with `origin = SEEDED_FALLBACK`, which the UI shows as a persistent label.

## 13. Award, export, audit
- Readiness over `cells_used`: non-VERIFIED cells, **any NEEDS_REVIEW override and its cells**, estimated weights, estimated freight, cell overrides, Unverified vendors (inclusive mode), alternates, `NEW_WARNING_AFTER_REVIEW`, stale resolutions, **UNVALIDATED constants used**.
- Award scenarios are always `context=formal`. An exploratory result promoted to Award is recomputed under the formal policy.
- Memo: Jinja2 with scenario numbers. AI rationale paragraphs are grounded and linted.
- Acknowledged awards are immutable. Superseded when inputs change.
- xlsx: Comparison, Sources, Traces, Assumptions (incl. constant-set version and validation labels), Eligibility (Quality and Commercial separately), Exclusions (incl. awaiting vendors and unresolved references), Audit. Excluded and awaiting cells are exported as status text, never as numbers (SC-09/10).
- **Clarification pack (DL-32):** `clarify/pack.py` selects one vendor's important vendor-resolvable items (blocking UNRESOLVED kinds: UNIT/READ/GST/PRICE_CONFLICT/SLAB; FREIGHT for FREIGHT_DEPENDENT or DECISION_SENSITIVE lines; EVIDENCE for Unverified quality questions; REFERENCE; UNCOVERED_LINE), orders them by sensitivity rank, and renders one fixed template per item kind. Same inputs → byte-identical pack; no AI call. Draft → buyer edit/approve → outbox. Resolutions are recorded manually.
- **Reference section (DL-20):** rendered within the pack from `Reference.candidates`: vendor phrase, reading A lines with candidate prices and baseline citations, reading B terms with candidate terms, and two direct questions. No AI call. `ClarificationRequest` moves from draft → approved (buyer) → in_outbox. It never goes to the outbox without approval.

## 14. Configuration & ground-truth isolation (I7)
- **Versioned constant sets (DL-18):** `backend/config/constants/vN.yaml`. Each constant has `{value, unit, validation_status, source, validated_by?, validated_at?}`. Files are immutable once loaded (content hash stored in `ConstantSet`). The active version is a DB setting, changed only through an audited activation. All initial constants are `UNVALIDATED`. UI, trace, export and memo renderers show "approximate engineering constant — not validated" (or "product heuristic — not validated") for any UNVALIDATED constant.
- **FX (DL-15):** `fx.yaml` seeds the USD rate with its as-of date and source label. It is editable in Settings and audited.
- `DATA_ROOT` (= `app_data/`) holds seed, inbox, storage and the DB. It is the only readable root for the app.
- `EVAL_ROOT` (sibling directory outside the repo) holds the generator, truth specs, answer keys, oracle, eval tests and the banned-literal list. It is never set in the app environment.
- Enforcement: `storage.safe_path` guard + startup check + AST static test + eval tests talking to the app over HTTP only (§5.1).
- The M10 perturbation seed is drawn at M10 and recorded in the eval report. It is not used during development.

## 15. Security & privacy
Local only. API key from env. No auth (A-25). Upload type is checked by magic bytes, size ≤ 20 MB. SQL sandbox. Data leaves the machine only for model calls.

## 16. Performance budget
| Stage | Budget |
|---|---|
| Parse | < 3 s/doc |
| Photo correction + OCR | < 5 s |
| Extraction (TEXT or OCR-structuring) | < 60 s/doc |
| **Vision path (parallel with OCR path)** | < 60 s (B4: adds about one call, but in parallel, so little extra wall time) |
| Matching | < 20 s/response |
| Phase A non-AI | < 1 s/response |
| **Phase B + global recompute** | < 2 s |
| Analyst | < 30 s typical |
| Item-master import (mapping call on header + 3 rows, then deterministic import of 30 rows) | mapping < 20 s; import < 1 s (DL-27) |
| Sensitivity analysis (all lines) | < 1 s (deterministic re-evaluation) |
| Conformance check | < 1 s |

## 17. Architecture decisions
| # | Decision | Rationale |
|---|---|---|
| ADR-1 | Python/FastAPI + React/Vite + SQLite | Parsing ecosystem; minimal ops |
| ADR-2 | Fixed pipeline; the analyst is the only loop | Predictable, testable |
| ADR-3 | Own EvidenceUnit ids | Works across formats and with structured outputs |
| ADR-4 | **Independent OCR and vision paths, deterministic reconciliation** | Real independence catches digit errors (DL-11) |
| ADR-5 | **Phase A per response / Phase B global + full recompute** | Order-independent, reproducible statuses (DL-9) |
| ADR-6 | Curated views + typed scenario tool; award questions forced to the scenario tool | Flexibility with correctness |
| ADR-7 | Caveats, inclusion, eligibility labels decided by code | The model can't hide or mislabel uncertainty |
| ADR-8 | Grounding check + label lint, regeneration by appending | Runtime enforcement without breaking conversation integrity |
| ADR-9 | Single model, explicit effort per route | Fewer variables |
| ADR-10 | Stubbed mail, in-process jobs | A-15 |
| ADR-11 | Decimal money with a defined rounding policy | Byte-identical results, exact grounding |
| ADR-12 | DATA_ROOT guard + external EVAL_ROOT | Ground truth unreachable by construction |
| ADR-13 | Inclusion = f(status, context, policy, override) in one module | Formal awards exclude NEEDS_REVIEW by default. Exploration stays possible and labelled (DL-16). |
| ADR-14 | Versioned, hash-pinned constant sets with validation status | Approximations are reproducible and never shown as facts (DL-18) |
| ADR-15 | Live co-pilot RFx + deterministic conformance gate to a canonical spec | One continuous demo flow with a genuine co-pilot, and reliable matching of prepared responses (DL-19) |
| ADR-16 | Structured fact views + capped, cited snippets via `get_evidence`; no full-text access | Whole-comparison Q&A without unrestricted document access or invented facts (SC-02) |
| ADR-17 | Ambiguous references keep both readings, with a template clarification and buyer confirmation | No assumption on genuinely ambiguous text. No AI-invented clarification content. (DL-20) |
| ADR-18 | Awaiting vendors carry no quote rows | Absence can't masquerade as zero or MISSING (SC-10) |
| ADR-19 | Freight-aware award selection with break-even, computed by the scenario engine | Mixed freight bases can't silently decide an award (DL-25) |
| ADR-20 | Decision sensitivity as deterministic re-evaluation of per-line selection | Shows which uncertainty matters without new model calls (DL-28) |
| ADR-21 | AI maps item-master columns; code imports rows | Exact line data; AI used where judgment adds value (DL-27) |
