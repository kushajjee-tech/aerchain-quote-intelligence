"""Single-process server for the hosted demo: the API under /api (as the Vite dev proxy does locally) and the built
React app for every other path, with client-side routes falling back to index.html. File paths are resolved in
app.config (the only module besides storage allowed to touch the filesystem)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import frontend_assets_dir, frontend_file
from app.main import create_app


def create_public_app() -> FastAPI:
    public = FastAPI(title="Quote Intelligence (demo)", docs_url=None, redoc_url=None, openapi_url=None)
    public.mount("/api", create_app())
    assets = frontend_assets_dir()
    if assets:
        public.mount("/assets", StaticFiles(directory=assets), name="assets")

    @public.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        return FileResponse(frontend_file(path))

    return public
