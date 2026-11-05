PY := $(CURDIR)/.venv/bin/python
export PYTHONPATH := $(CURDIR)/backend

# Local secrets: ANTHROPIC_API_KEY=... in .env (gitignored). Loaded into make's environment, never echoed.
-include .env
export ANTHROPIC_API_KEY

.PHONY: start demo-prepare setup dev test doctor reset frontend-build eval-m1a generate-m1a llm-smoke live-slice eval-live review-pack

setup:
	python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm install

# Start backend (port 8010) + frontend (http://localhost:5173); Ctrl+C stops both.
start:
	@test -d frontend/node_modules || (cd frontend && npm install)
	@bash -c 'trap "kill 0" EXIT; $(PY) -m uvicorn app.main:create_app --factory --app-dir backend --port 8010 & cd frontend && npm run dev -- --port 5173'

# One-time before a demo (live model, ~10 min): fresh database, then the full buyer flow on the real data.
demo-prepare:
	$(PY) backend/scripts/reset_db.py
	$(PY) backend/scripts/live_slice.py --in-place --out $(abspath $(CURDIR)/../aerchain-live-runs)/demo_prepare.json

dev:
	$(PY) -m uvicorn app.main:create_app --factory --reload --app-dir backend --port 8010

test:
	cd backend && $(PY) -m pytest -q

doctor:
	$(PY) backend/scripts/doctor.py

reset:
	$(PY) backend/scripts/reset_db.py

frontend-build:
	cd frontend && npm run build

# Ground-truth workspace lives OUTSIDE the repo (architecture §5.1). EVAL_ROOT is set only here.
EVAL_ROOT ?= $(abspath $(CURDIR)/../aerchain-eval)
generate-m1a:
	EVAL_ROOT=$(EVAL_ROOT) PYTHONPATH= $(PY) -I $(EVAL_ROOT)/generator/generate.py --seed 20261104 --data-root $(CURDIR)/app_data --eval-root $(EVAL_ROOT)

eval-m1a:
	cd $(EVAL_ROOT) && EVAL_ROOT=$(EVAL_ROOT) APP_REPO=$(CURDIR) PYTHONPATH= $(PY) -m pytest -q eval_tests

# --- live model validation (needs ANTHROPIC_API_KEY) -------------------------------------------
llm-smoke:
	$(PY) backend/scripts/llm_smoke.py

LIVE_OUT ?= $(abspath $(CURDIR)/../aerchain-live-runs)/live_slice.json
live-slice:
	$(PY) backend/scripts/live_slice.py --out $(LIVE_OUT)

eval-live:
	cd $(EVAL_ROOT) && EVAL_ROOT=$(EVAL_ROOT) PYTHONPATH= $(PY) -I $(EVAL_ROOT)/live/check_live_slice.py $(LIVE_OUT)

REVIEW_PACK ?= $(abspath $(CURDIR)/../aerchain-review-pack)
review-pack:
	PYTHONPATH= $(PY) -I $(EVAL_ROOT)/generator/review_pack.py --data-root $(CURDIR)/app_data --checklist $(CURDIR)/docs/11_dataset_realism_review.md --out $(REVIEW_PACK)
