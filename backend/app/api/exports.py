"""Export endpoints (EXP-1/2, AUD-1)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import select

from app.analysis.scenario import ScenarioParams, run_scenario
from app.api.comparison import build_grid
from app.db.models import AuditEvent, AwardDecision, EligibilityResult, NormalizedQuote, Question, Rfx, RfxLine, Scenario, Vendor
from app.domain.enums import ASSUMPTION_REASONS
from app.export.html import memo_html
from app.export.xlsx import audit_csv, comparison_workbook
from app.settings_.registry import active_constant_set, fx_rates

router = APIRouter()
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _attach(data: bytes, media: str, name: str) -> Response:
    return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/rfx/{rfx_id}/export.xlsx")
def export_comparison(rfx_id: int, request: Request, basis: str = "unit"):
    sf = request.app.state.session_factory
    with sf() as s:
        rfx = s.get(Rfx, rfx_id)
        if rfx is None:
            raise HTTPException(404, "no such RFx")
        lines = {l.id: l.line_no for l in s.scalars(select(RfxLine).where(RfxLine.rfx_id == rfx_id))}
        names = {v.id: v.name for v in s.scalars(select(Vendor))}
        prov = [{"line_no": lines[q.rfx_line_id], "vendor": names[q.vendor_id], "status": q.unit_status,
                 "source": next((t for t in q.trace if t.get("step") == "evidence"), None), "trace": q.trace,
                 "assumptions": [r for r in q.unit_reasons or [] if r in ASSUMPTION_REASONS]}
                for q in s.scalars(select(NormalizedQuote).where(NormalizedQuote.rfx_line_id.in_(list(lines))))]
        qs = {q.id: q for q in s.scalars(select(Question).where(Question.rfx_id == rfx_id))}
        elig = sorted(({"vendor": names[e.vendor_id], "section": qs[e.question_id].section, "no": qs[e.question_id].no,
                        "key": qs[e.question_id].requirement_key, "state": e.state, "reason": e.reason}
                       for e in s.scalars(select(EligibilityResult).where(EligibilityResult.question_id.in_(list(qs))))),
                      key=lambda e: (e["vendor"], e["section"], e["no"]))
        title = rfx.title
    prov.sort(key=lambda p: (p["line_no"], p["vendor"]))
    excl = run_scenario(sf, rfx_id, ScenarioParams())["exclusions"] if lines else []
    settings = {"fx": {k: {**v, "rate": str(v["rate"])} for k, v in fx_rates(sf).items()},
                "constant_set": active_constant_set(sf).version}
    data = comparison_workbook(build_grid(sf, rfx_id, basis), prov, elig, excl, settings)
    return _attach(data, XLSX, f"comparison-rfx{rfx_id}.xlsx")


def _memo(sf, scenario_id: int) -> tuple[str, str]:
    from app.award.memo import render_memo
    from app.analysis.scenario import readiness_items
    with sf() as s:
        sc = s.get(Scenario, scenario_id)
        if sc is None:
            raise HTTPException(404, "no such scenario")
        title = s.get(Rfx, sc.rfx_id).title if sc.rfx_id else "RFx"
        ad = s.scalar(select(AwardDecision).where(AwardDecision.scenario_id == sc.id, AwardDecision.acknowledged_at.is_not(None),
                                                  AwardDecision.superseded.is_(False)).order_by(AwardDecision.id.desc()))
        if ad is not None and not sc.stale:
            return ad.memo, title
        snap, rfx_id = sc.result_snapshot, sc.rfx_id
    return render_memo(title, scenario_id, snap, readiness=readiness_items(sf, rfx_id, snap) if rfx_id else []), title


@router.get("/scenarios/{scenario_id}/memo.md")
def memo_md(scenario_id: int, request: Request):
    md, _ = _memo(request.app.state.session_factory, scenario_id)
    return _attach(md.encode("utf-8"), "text/markdown; charset=utf-8", f"award-memo-{scenario_id}.md")


@router.get("/scenarios/{scenario_id}/memo.html")
def memo_page(scenario_id: int, request: Request):
    md, title = _memo(request.app.state.session_factory, scenario_id)
    return Response(memo_html(md, f"Award memo — {title}"), media_type="text/html; charset=utf-8")


@router.get("/rfx/{rfx_id}/audit.csv")
def audit_export(rfx_id: int, request: Request):
    with request.app.state.session_factory() as s:
        ev = [{"id": e.id, "at": e.at.isoformat(), "actor": e.actor, "action": e.action, "target": e.target, "before": e.before,
               "after": e.after, "reason": e.reason} for e in s.scalars(select(AuditEvent).order_by(AuditEvent.id))
              if (e.target or {}).get("rfx_id") in (rfx_id, None)]
    return _attach(audit_csv(ev), "text/csv", f"audit-rfx{rfx_id}.csv")
