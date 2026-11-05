from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict:
    with request.app.state.engine.connect() as conn:
        conn.execute(text("select 1"))
    return {"status": "ok", "data_root": str(request.app.state.settings.data_root.name)}
