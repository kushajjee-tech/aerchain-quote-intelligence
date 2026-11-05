from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.analysis.analyst import Analyst, to_dict

router = APIRouter(prefix="/analyst")


class AskBody(BaseModel):
    rfx_id: int
    question: str
    session_id: str | None = None


@router.post("/ask")
def ask(body: AskBody, request: Request):
    st = request.app.state
    session_id = body.session_id or f"analyst-{uuid.uuid4().hex[:12]}"
    from app.process.run import awarded_baseline_rows
    gw = st.gateway_factory()
    gw.model = st.settings.analyst_model          # cheaper model for the assistant (APP_ANALYST_MODEL)
    if "haiku" in gw.model:
        gw.use_fallbacks = False                  # Haiku has no server-side refusal fallback
    analyst = Analyst(gw, st.session_factory, str(st.settings.db_path), body.rfx_id,
                      awarded_baseline_rows(st.session_factory, st.storage, body.rfx_id))
    out = to_dict(analyst.ask(session_id, body.question))
    from app.db.models import AnalystAnswerRecord
    with st.session_factory.begin() as s:
        rec = AnalystAnswerRecord(rfx_id=body.rfx_id, session_id=session_id, question=body.question,
                                  answer=json.loads(json.dumps(out, default=str)))
        s.add(rec)
        s.flush()
        answer_id = rec.id
    return {"session_id": session_id, "answer_id": answer_id, **out}


@router.get("/answers/{answer_id}/export")
def export_table(answer_id: int, request: Request, index: int = -1, fmt: str = "xlsx"):
    """EXP-3: the tool-result table of a stored answer (index into its results), with caveats and exclusions."""
    from fastapi import HTTPException, Response
    from app.db.models import AnalystAnswerRecord
    from app.export.xlsx import table_csv, table_workbook
    with request.app.state.session_factory() as s:
        rec = s.get(AnalystAnswerRecord, answer_id)
        if rec is None:
            raise HTTPException(404, "no such answer")
        a = rec.answer
    tables = a.get("tables") or []
    if not tables:
        raise HTTPException(404, "this answer has no table")
    try:
        t = tables[index]
    except IndexError:
        raise HTTPException(404, "no such table")
    if fmt == "csv":
        return Response(table_csv(t["columns"], t["rows"], a.get("caveats") or {}), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="analyst-{answer_id}.csv"'})
    return Response(table_workbook(t["columns"], t["rows"], a.get("caveats") or {}, a.get("exclusions") or []),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="analyst-{answer_id}.xlsx"'})
