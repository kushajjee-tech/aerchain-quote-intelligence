"""`make doctor`: preflight check of system dependencies (PRD NF-7)."""
from __future__ import annotations

import importlib
import os
import shutil
import sys

REQUIRED_PY = ["fastapi", "sqlalchemy", "pydantic", "anthropic", "openpyxl", "docx", "httpx", "pytest"]
problems: list[str] = []
print(f"python {sys.version.split()[0]}")
for mod in REQUIRED_PY:
    try:
        importlib.import_module(mod)
        print(f"  ok   {mod}")
    except ImportError:
        problems.append(f"python package missing: {mod} (pip install -r backend/requirements.txt)")
for tool, needed_by in [("tesseract", "M3 OCR path"), ("node", "frontend"), ("npm", "frontend")]:
    if shutil.which(tool):
        print(f"  ok   {tool}")
    else:
        problems.append(f"{tool} not found (needed by {needed_by}); macOS: brew install {tool}")
if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("ANTHROPIC_AUTH_TOKEN"):
    problems.append("no ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN: live model calls (@live tests) cannot run")
if os.environ.get("EVAL_ROOT"):
    problems.append("EVAL_ROOT is set in this shell; the app will refuse to start (isolation, NF-9)")
print("\n".join(f"  WARN {p}" for p in problems) or "  all checks passed")
sys.exit(0)
