"""Settings (M5b): FX rates and constant-set versions. Every change is audited and re-normalises (VAL-5)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.process.run import renormalize_all
from app.settings_ import registry as reg

router = APIRouter(prefix="/settings")


@router.get("/fx")
def get_fx(request: Request):
    return {k: {**v, "rate": str(v["rate"])} for k, v in reg.fx_rates(request.app.state.session_factory).items()}


class FxBody(BaseModel):
    rate_to_inr: str
    as_of: str
    source: str
    actor: str = "buyer"


@router.put("/fx/{currency}")
def put_fx(currency: str, body: FxBody, request: Request):
    st = request.app.state
    try:
        reg.set_fx(st.session_factory, currency, body.rate_to_inr, body.as_of, body.source, body.actor)
    except (ValueError, ArithmeticError) as e:
        raise HTTPException(422, str(e))
    return {"recomputed": renormalize_all(st.session_factory, st.storage, body.actor, f"FX {currency.upper()} set")}


@router.get("/constants")
def get_constants(request: Request):
    return reg.all_constant_sets(request.app.state.session_factory)


class NewSetBody(BaseModel):
    base_version: str
    new_version: str
    changes: dict[str, str]
    reason: str
    actor: str = "buyer"


@router.post("/constants")
def new_set(body: NewSetBody, request: Request):
    try:
        cs = reg.create_constant_set(request.app.state.session_factory, body.base_version, body.changes, body.new_version,
                                     body.actor, body.reason)
    except (ValueError, ArithmeticError) as e:
        raise HTTPException(422, str(e))
    return {"version": cs.version, "hash": cs.content_hash}


class ActivateBody(BaseModel):
    reason: str
    actor: str = "buyer"


@router.post("/constants/{version}/activate")
def activate(version: str, body: ActivateBody, request: Request):
    st = request.app.state
    try:
        reg.activate_constant_set(st.session_factory, version, body.actor, body.reason)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"active": version, "recomputed": renormalize_all(st.session_factory, st.storage, body.actor, f"constants {version}")}
