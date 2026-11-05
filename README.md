# Kill the Quote Spreadsheet — corrugated packaging RFx prototype

An AI co-pilot drafts the RFx, five vendors reply in five formats, the system reads every reply into one
normalised side-by-side comparison, a natural-language analyst answers questions over it, and the flow ends in an
audited award recommendation. AI reads; deterministic code calculates; every number traces to its source.

## Run it (macOS)
Requirements: Python 3.14, Node 20+, Tesseract (`brew install tesseract`), Google Chrome (dataset rendering only),
an Anthropic API key with credit.

```bash
make setup                      # Python venv + frontend packages
echo "ANTHROPIC_API_KEY=..." > .env   # never committed (.gitignore)
make reset && make llm-smoke    # fresh database + one tiny live call
make demo-prepare               # once before a demo: full live flow on the demo data (~10 min, ~$2)
make start                      # backend :8010 + frontend http://localhost:5173 (Ctrl+C stops both)
```

## What to look at
The UI is a sidebar app over one RFx (selector in the top bar; the seeded fixture is marked **Demo / evaluation RFx**).
Every figure on screen comes from the backend; nothing is invented to fill the page.

| Route | Module | What it shows |
|---|---|---|
| `/` | Home | RFx health metrics, blockers ("Needs your attention"), other exceptions, supplier tracker, progress, activity (audit events only) |
| `/copilot` | Co-pilot | **Ask**: RFx-grounded assistant (needs the API key) · **RFx drafting**: brief → mapping → questionnaire → approve → send → read |
| `/vendors`, `/vendors/:id` | Vendors & Inbox | Supplier list with filters and upload; detail tabs Overview · Inbox & correspondence · Documents (original-file preview) · Quoted items |
| `/review` | Review | Findings derived from eligibility, cell statuses and coverage; Confirm / Reject / Request clarification / Mark not applicable, audited with history |
| `/comparison` | Comparison | Sticky-SKU grid, as-quoted beside normalised ₹/box, FX/discount/slab/freight/GST breakdown per row, By SKU / By supplier / Exceptions only, XLSX export |
| `/analyst` | Analyst | Deterministic analytics (spend estimate, demand, coverage, baseline variance, exceptions) and a what-if scenario |
| `/award` | Award | Allocation from the award engine; **Save recommendation** is blocked while an open blocker affects the allocation, and needs a reason |
| `/settings` | Settings | RFx metadata (editable, audited), evaluation criteria, commercial policy, FX and conversion constants, audit log and exports |

An **Ask AI** button on every screen opens the RFx assistant in a side panel (Ctrl/Cmd+J). It sends what you are looking at (supplier, comparison line, finding, award) with the question, shares one conversation with the Co-pilot page, and offers optional browser voice input and read-aloud.

Without an API key everything except the assistant, AI drafting steps and reading new responses works on the
existing database. Tests: `make test` (backend) and `npm --prefix frontend test` (routes, blocker logic, no false zeros).

## Repository map
- `backend/app` — FastAPI app: ingestion and extraction, normalisation, validation, analysis, award.
- `backend/tests` — `make test`.
- `frontend/src` — React UI.
- `app_data/seed`, `app_data/inbox` — the generated demo dataset (buyer brief pack, canonical RFx, vendor emails).
- `docs/` — requirements catalogue (`00_source_of_truth.md`), PRD, architecture, runbook (`10_demo_runbook.md`),
  deliverables (`deliverables/one_page_note.pdf`, `deliverables/recording_script.md`).

Ground truth and the dataset generator live in a separate evaluation workspace outside this repository; the app
refuses to start if it can see them.

## Disclosed deviations (owner-approved)
- V4's "phone photo" is an **AI-generated image**, labelled as such; it is read by OCR only, so its values stay
  unresolved until confirmed (`docs/12_phone_photo_capture_kit.md` §8).
- The dataset realism review was **AI-written and checked by the owner**, not an independent buyer
  (`docs/11_dataset_realism_review.md` §7).
