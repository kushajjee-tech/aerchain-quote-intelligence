"""Application configuration and the startup isolation check (PRD NF-9, architecture §5.1/§14).

This is the only module allowed to mention the evaluation-root environment variable name,
because it must refuse to start when that variable is visible to the app.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = REPO_ROOT / "app_data"
# Sibling directory that holds generator and evaluation keys. Never readable by the app.
DEFAULT_EVAL_ROOT_HINT = REPO_ROOT.parent / "aerchain-eval"
_EVAL_ENV_VAR = "EVAL_ROOT"


FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"   # the built UI, served by app.serve in the hosted demo


def frontend_assets_dir() -> str | None:
    d = FRONTEND_DIST / "assets"
    return str(d) if d.is_dir() else None


def frontend_file(path: str) -> str:
    """A file of the built UI, or index.html for client-side routes. Never resolves outside the dist folder."""
    root = FRONTEND_DIST.resolve()
    f = (root / path).resolve()
    return str(f) if path and f.is_file() and root in f.parents else str(root / "index.html")


class StartupIsolationError(RuntimeError):
    """Raised when the app could see evaluation material."""


@dataclass(frozen=True)
class Settings:
    data_root: Path
    eval_root_hint: Path
    db_url: str
    llm_model: str = "claude-opus-5-5"
    llm_use_fallbacks: bool = True
    # The buyer-facing assistant (analyst) runs on a cheaper model; extraction and drafting keep llm_model.
    # Its numbers are computed by tools and checked by grounding, so the model only plans and writes.
    analyst_model: str = "claude-haiku-5-5"

    @property
    def db_path(self) -> Path:
        return self.data_root / "app.db"


def load_settings(env: dict[str, str] | None = None) -> Settings:
    env = dict(os.environ if env is None else env)
    data_root = Path(env.get("APP_DATA_ROOT", str(DEFAULT_DATA_ROOT))).resolve()
    eval_hint = Path(env.get("APP_EVAL_ROOT_HINT", str(DEFAULT_EVAL_ROOT_HINT))).resolve()
    db_url = env.get("APP_DB_URL", f"sqlite:///{data_root / 'app.db'}")
    return Settings(
        data_root=data_root,
        eval_root_hint=eval_hint,
        db_url=db_url,
        llm_model=env.get("APP_LLM_MODEL", "claude-opus-5-5"),
        llm_use_fallbacks=env.get("APP_LLM_FALLBACKS", "1") != "0",
        analyst_model=env.get("APP_ANALYST_MODEL", "claude-haiku-5-5"),
    )


def _overlaps(a: Path, b: Path) -> bool:
    a, b = a.resolve(), b.resolve()
    return a == b or a in b.parents or b in a.parents


def startup_check(settings: Settings, env: dict[str, str] | None = None) -> None:
    """Refuse to run if evaluation material could be reachable (architecture §5.1 control 3)."""
    env = dict(os.environ if env is None else env)
    if env.get(_EVAL_ENV_VAR):
        raise StartupIsolationError(
            f"{_EVAL_ENV_VAR} is set in the application environment; evaluation material must "
            "never be visible to the running app."
        )
    if _overlaps(settings.data_root, settings.eval_root_hint):
        raise StartupIsolationError(
            f"DATA_ROOT {settings.data_root} overlaps the evaluation root {settings.eval_root_hint}."
        )
    if _overlaps(settings.data_root, REPO_ROOT / "backend"):
        raise StartupIsolationError("DATA_ROOT must not overlap application code.")
