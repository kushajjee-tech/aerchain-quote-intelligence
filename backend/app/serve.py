"""Single-process server for the hosted demo: the API under /api (as the Vite dev proxy does locally) and the built
React app for every other path, with the client-side routes falling back to index.html."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import REPO_ROOT
from app.main import create_app

DIST = REPO_ROOT / "frontend" / "dist"


def create_public_app(dist: Path = DIST) -> FastAPI:
    public = FastAPI(title="Quote Intelligence (demo)", docs_url=None, redoc_url=None, openapi_url=None)
    public.mount("/api", create_app())
    if (dist / "assets").is_dir():
        public.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @public.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = (dist / path).resolve()
        if path and f.is_file() and dist.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(dist / "index.html")

    return public
