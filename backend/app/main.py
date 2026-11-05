"""FastAPI application factory (M0 skeleton)."""
from __future__ import annotations

from fastapi import FastAPI

from app.api.health import router as health_router
from app.analysis.views import ensure_views
from app.api.analyst import router as analyst_router
from app.api.comparison import router as comparison_router
from app.api.rfx import router as rfx_router
from app.api.review import packs_router, router as review_router
from app.api.scenarios import router as scenario_router
from app.api.settings import router as settings_router
from app.api.exports import router as exports_router
from app.api.documents import router as documents_router
from app.api.overview import router as overview_router
from app.config import Settings, load_settings, startup_check
from app.db.session import init_db, make_engine, make_session_factory
from app.storage import Storage


def create_app(settings: Settings | None = None, env: dict[str, str] | None = None) -> FastAPI:
    settings = settings or load_settings(env)
    startup_check(settings, env)  # refuses to start if evaluation material could be visible
    storage = Storage(settings.data_root)
    engine = make_engine(settings.db_url)
    init_db(engine)
    ensure_views(engine)
    app = FastAPI(title="Quote Intelligence", version="0.1.0")
    app.state.settings = settings
    app.state.storage = storage
    app.state.engine = engine
    app.state.session_factory = make_session_factory(engine)
    from fastapi.responses import JSONResponse
    from app.llm.gateway import LLMError, LLMUnavailable

    @app.exception_handler(LLMError)
    def _llm_error(request, exc: LLMError):  # a model problem is reported plainly, never as a 500
        return JSONResponse(status_code=503 if isinstance(exc, LLMUnavailable) else 502,
                            content={"detail": f"{type(exc).__name__}: {exc}"})

    app.include_router(health_router)
    app.include_router(rfx_router)
    app.include_router(comparison_router)
    app.include_router(scenario_router)
    app.include_router(analyst_router)
    app.include_router(review_router)
    app.include_router(packs_router)
    app.include_router(settings_router)
    app.include_router(exports_router)
    app.include_router(documents_router)
    app.include_router(overview_router)

    def gateway_factory():  # lazy: the app starts without an API key; model routes need one
        from app.llm.gateway import LLMGateway
        return LLMGateway(app.state.session_factory, model=settings.llm_model, use_fallbacks=settings.llm_use_fallbacks)

    app.state.gateway_factory = gateway_factory
    return app
