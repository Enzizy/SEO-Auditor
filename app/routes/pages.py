from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app import db as db_state
from app.config import get_settings
from app.models import AuditStatus
from app.schemas.audit import AuditCreateForm
from app.services.audits import (
    create_audit_job,
    build_issue_breakdown,
    build_issue_type_summary,
    build_phase_timings,
    enqueue_audit_run,
    get_audit_history,
    get_audit_run,
    get_audit_status,
    get_dashboard_metrics,
    get_history_overview,
    get_recent_activity,
    get_report_overview,
    get_report_library,
    get_report_path,
)
from app.services.report_storage import ReportStorage

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
router = APIRouter(tags=["pages"])


def _base_context(request: Request, page_title: str, active_nav: str, **kwargs) -> dict:
    return {
        "request": request,
        "page_title": page_title,
        "active_nav": active_nav,
        "app_name": get_settings().app_name,
        **kwargs,
    }


def _severity_class(severity: str) -> str:
    return {
        "critical": "bg-rose-100 text-rose-700 border border-rose-200",
        "warning": "bg-amber-100 text-amber-700 border border-amber-200",
        "info": "bg-sky-100 text-sky-700 border border-sky-200",
    }.get(severity, "bg-slate-100 text-slate-700 border border-slate-200")


def _status_class(status: str) -> str:
    return {
        "completed": "bg-emerald-100 text-emerald-700",
        "running": "bg-amber-100 text-amber-700",
        "queued": "bg-slate-100 text-slate-700",
        "failed": "bg-rose-100 text-rose-700",
    }.get(status, "bg-slate-100 text-slate-700")


templates.env.globals["severity_class"] = _severity_class
templates.env.globals["status_class"] = _status_class


@router.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/dashboard")
def dashboard(request: Request):
    with db_state.SessionLocal() as db:
        metrics = get_dashboard_metrics(db)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=_base_context(request, "Dashboard", "dashboard", **metrics),
    )


@router.get("/audits/new")
def new_audit(request: Request):
    settings = get_settings()
    return templates.TemplateResponse(
        request=request,
        name="new_audit.html",
        context=_base_context(
            request,
            "New Audit",
            "new_audit",
            defaults={
                "max_pages": settings.crawler_default_max_pages,
                "max_depth": settings.crawler_default_max_depth,
                "pagespeed_strategy": settings.pagespeed_strategy,
                "js_render_mode": "auto",
                "external_link_check": True,
            },
            errors={},
            values={},
        ),
    )


@router.post("/audits")
def create_audit(
    request: Request,
    website_url: str = Form(...),
    project_label: str = Form(...),
    max_pages: int = Form(...),
    max_depth: int = Form(...),
    pagespeed_strategy: str = Form(...),
    js_render_mode: str = Form(...),
    external_link_check: bool = Form(False),
):
    try:
        payload = AuditCreateForm(
            website_url=website_url,
            project_label=project_label,
            max_pages=max_pages,
            max_depth=max_depth,
            pagespeed_strategy=pagespeed_strategy,
            js_render_mode=js_render_mode,
            external_link_check=external_link_check,
        )
    except ValidationError as exc:
        settings = get_settings()
        return templates.TemplateResponse(
            request=request,
            name="new_audit.html",
            status_code=422,
            context=_base_context(
                request,
                "New Audit",
                "new_audit",
                defaults={
                    "max_pages": settings.crawler_default_max_pages,
                    "max_depth": settings.crawler_default_max_depth,
                    "pagespeed_strategy": settings.pagespeed_strategy,
                    "js_render_mode": "auto",
                    "external_link_check": True,
                },
                values={
                    "website_url": website_url,
                    "project_label": project_label,
                    "max_pages": max_pages,
                    "max_depth": max_depth,
                    "pagespeed_strategy": pagespeed_strategy,
                    "js_render_mode": js_render_mode,
                    "external_link_check": external_link_check,
                },
                errors={error["loc"][-1]: error["msg"] for error in exc.errors()},
            ),
        )

    with db_state.SessionLocal() as db:
        audit_run = create_audit_job(db, payload)
        enqueue_audit_run(db, audit_run)
    return RedirectResponse(url=f"/audits/{audit_run.id}", status_code=303)


@router.get("/audits/{audit_id}")
def audit_detail(
    request: Request,
    audit_id: int,
    tab: str = Query(default="overview"),
    issue_severity: str | None = Query(default=None),
    page_query: str | None = Query(default=None),
):
    with db_state.SessionLocal() as db:
        audit_run = get_audit_run(db, audit_id)
        if audit_run is None:
            raise HTTPException(status_code=404, detail="Audit run not found")

        if audit_run.status in {AuditStatus.queued, AuditStatus.running}:
            return templates.TemplateResponse(
                request=request,
                name="audit_progress.html",
                context=_base_context(request, f"Audit #{audit_run.id}", "history", audit=audit_run),
            )

        page_results = audit_run.page_results
        issues = audit_run.issues
        if issue_severity:
            issues = [issue for issue in issues if issue.severity.value == issue_severity]
        if page_query:
            page_results = [page for page in page_results if page_query.lower() in page.url.lower()]

        image_assets = [asset for page in audit_run.page_results for asset in page.assets if asset.asset_type == "image"]
        performance_assets = [asset for page in audit_run.page_results for asset in page.assets if asset.asset_type != "image"]
        issue_breakdown = build_issue_breakdown(audit_run)
        issue_type_summary = build_issue_type_summary(audit_run)
        phase_timings = build_phase_timings(audit_run)

    return templates.TemplateResponse(
        request=request,
        name="audit_results.html",
        context=_base_context(
            request,
            f"Audit #{audit_id}",
            "history",
            audit=audit_run,
            tab=tab,
            page_results=page_results,
            issues=issues,
            image_assets=image_assets,
            performance_assets=performance_assets,
            issue_breakdown=issue_breakdown,
            issue_type_summary=issue_type_summary,
            phase_timings=phase_timings,
            issue_severity=issue_severity,
            page_query=page_query,
        ),
    )


@router.get("/audits/{audit_id}/status")
def audit_status(audit_id: int):
    with db_state.SessionLocal() as db:
        payload = get_audit_status(db, audit_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Audit run not found")
        return payload


@router.get("/audits/{audit_id}/reports")
def audit_report(audit_id: int, format: str = Query(default="html", pattern="^(html|pdf|csv)$")):
    with db_state.SessionLocal() as db:
        audit_run = get_audit_run(db, audit_id)
        if audit_run is None:
            raise HTTPException(status_code=404, detail="Audit run not found")
        path = get_report_path(audit_run, format)
    media_type = {
        "html": "text/html",
        "pdf": "application/pdf",
        "csv": "text/csv",
    }[format]
    storage = ReportStorage()
    try:
        content, media_type = storage.open(path, media_type)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found") from None
    filename = f"audit-{audit_id}.{format}"
    headers = {"Content-Disposition": f'inline; filename="{filename}"'} if format == "html" else {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }
    return Response(content=content, media_type=media_type, headers=headers)


@router.get("/history")
def history(
    request: Request,
    status: str | None = Query(default=None, pattern="^(queued|running|completed|failed)$"),
    project: str | None = Query(default=None),
    query: str | None = Query(default=None),
):
    with db_state.SessionLocal() as db:
        audits = get_audit_history(db, status=status, project=project, query=query)
        overview = get_history_overview(db)
        recent_activity = get_recent_activity(db)
        history_timings = {audit.id: build_phase_timings(audit) for audit in audits}
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context=_base_context(
            request,
            "Audit History",
            "history",
            audits=audits,
            overview=overview,
            recent_activity=recent_activity,
            history_timings=history_timings,
            filters={"status": status or "", "project": project or "", "query": query or ""},
        ),
    )


@router.get("/reports")
def reports_page(request: Request, query: str | None = Query(default=None)):
    with db_state.SessionLocal() as db:
        audits = get_report_library(db, query=query)
        overview = get_report_overview(db)
        report_timings = {audit.id: build_phase_timings(audit) for audit in audits}
    return templates.TemplateResponse(
        request=request,
        name="reports_index.html",
        context=_base_context(
            request,
            "Reports",
            "reports",
            audits=audits,
            overview=overview,
            report_timings=report_timings,
            filters={"query": query or ""},
        ),
    )
