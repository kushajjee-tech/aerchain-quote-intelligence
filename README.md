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
- **Co-pilot**: draft the RFx live from the brief pack (`app_data/seed/brief_pack`), or load the labelled seeded fallback.
- **Comparison**: 30 lines × 5 vendors, one status per value, eligibility and documents per vendor; click any cell for its source.
- **Review**: decision-sensitive items first; accept, correct, override (audited); clarification packs.
- **Analyst**: grounded answers with tables, charts, caveats and exports.
- **Award**: freight-aware cheapest-per-line, readiness check, acknowledgement, memo.

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
