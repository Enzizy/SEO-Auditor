from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import AuditIssue, AuditRun, AuditStatus, IssueSeverity, PageAuditResult, WebsiteProject
from app.schemas.audit import AuditCreateForm, AuditStatusPayload
from app.services.execution import dispatch_audit_run
from app.services.projects import get_or_create_project


def create_audit_job(db: Session, form: AuditCreateForm) -> AuditRun:
    project = get_or_create_project(db, str(form.website_url), form.project_label)
    audit_run = AuditRun(
        website_id=project.id,
        start_url=str(form.website_url),
        status=AuditStatus.queued,
        pagespeed_strategy=form.pagespeed_strategy,
        max_pages=form.max_pages,
        max_depth=form.max_depth,
        js_render_mode=form.js_render_mode,
        external_link_check=form.external_link_check,
    )
    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)
    return audit_run


def enqueue_audit_run(db: Session, audit_run: AuditRun) -> AuditRun:
    audit_run.job_id = dispatch_audit_run(audit_run.id)
    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)
    return audit_run


def get_audit_run(db: Session, audit_id: int) -> AuditRun | None:
    statement = (
        select(AuditRun)
        .where(AuditRun.id == audit_id)
        .options(
            selectinload(AuditRun.website),
            selectinload(AuditRun.page_results).selectinload(PageAuditResult.assets),
            selectinload(AuditRun.issues).selectinload(AuditIssue.page_result),
        )
    )
    return db.scalar(statement)


def get_audit_status(db: Session, audit_id: int) -> AuditStatusPayload | None:
    audit_run = db.get(AuditRun, audit_id)
    if audit_run is None:
        return None
    return AuditStatusPayload(
        audit_id=audit_run.id,
        status=audit_run.status,
        pages_crawled=audit_run.pages_crawled,
        total_issues=audit_run.total_issues,
        current_page_url=audit_run.current_page_url,
        progress_stage=audit_run.progress_stage,
        progress_message=audit_run.progress_message,
        seo_score=audit_run.seo_score,
        performance_score=audit_run.performance_score,
        report_ready=bool(audit_run.report_html_path and audit_run.report_pdf_path and audit_run.report_csv_path),
        error_message=audit_run.error_message,
        completed_at=audit_run.completed_at,
    )


def get_report_path(audit_run: AuditRun, report_format: str) -> str:
    candidates = {
        "html": audit_run.report_html_path,
        "pdf": audit_run.report_pdf_path,
        "csv": audit_run.report_csv_path,
    }
    if report_format not in candidates or not candidates[report_format]:
        raise FileNotFoundError(f"Unknown or unavailable report format: {report_format}")
    return str(candidates[report_format])


def get_dashboard_metrics(db: Session) -> dict:
    total_audits = db.scalar(select(func.count(AuditRun.id))) or 0
    websites_tracked = db.scalar(select(func.count(WebsiteProject.id))) or 0
    completed_audits = db.scalar(select(func.count(AuditRun.id)).where(AuditRun.status == AuditStatus.completed)) or 0
    running_audits = db.scalar(
        select(func.count(AuditRun.id)).where(AuditRun.status.in_([AuditStatus.queued, AuditStatus.running]))
    ) or 0
    critical_issues = db.scalar(
        select(func.count(AuditIssue.id)).where(AuditIssue.severity == IssueSeverity.critical)
    ) or 0
    average_scores = db.execute(
        select(func.avg(AuditRun.seo_score), func.avg(AuditRun.performance_score)).where(
            AuditRun.status == AuditStatus.completed
        )
    ).one()
    recent_audits = db.scalars(
        select(AuditRun)
        .options(selectinload(AuditRun.website))
        .order_by(AuditRun.created_at.desc())
        .limit(8)
    ).all()
    return {
        "total_audits": total_audits,
        "websites_tracked": websites_tracked,
        "completed_audits": completed_audits,
        "running_audits": running_audits,
        "critical_issues": critical_issues,
        "average_seo_score": round(float(average_scores[0] or 0), 1),
        "average_performance_score": round(float(average_scores[1] or 0), 1),
        "recent_audits": recent_audits,
    }


def get_audit_history(
    db: Session,
    status: str | None = None,
    project: str | None = None,
    query: str | None = None,
) -> list[AuditRun]:
    statement = select(AuditRun).options(selectinload(AuditRun.website)).join(WebsiteProject).order_by(AuditRun.created_at.desc())
    if status:
        statement = statement.where(AuditRun.status == AuditStatus(status))
    if project:
        statement = statement.where(WebsiteProject.label.ilike(f"%{project}%"))
    if query:
        statement = statement.where(
            WebsiteProject.label.ilike(f"%{query}%") | AuditRun.start_url.ilike(f"%{query}%")
        )
    return db.scalars(statement).all()


def get_report_library(db: Session, query: str | None = None) -> list[AuditRun]:
    statement = (
        select(AuditRun)
        .where(AuditRun.status == AuditStatus.completed)
        .options(selectinload(AuditRun.website))
        .join(WebsiteProject)
        .order_by(AuditRun.completed_at.desc().nullslast(), AuditRun.created_at.desc())
    )
    if query:
        statement = statement.where(
            WebsiteProject.label.ilike(f"%{query}%") | AuditRun.start_url.ilike(f"%{query}%")
        )
    return db.scalars(statement).all()


def get_history_overview(db: Session) -> dict[str, int]:
    return {
        "total": db.scalar(select(func.count(AuditRun.id))) or 0,
        "completed": db.scalar(select(func.count(AuditRun.id)).where(AuditRun.status == AuditStatus.completed)) or 0,
        "running": db.scalar(
            select(func.count(AuditRun.id)).where(AuditRun.status.in_([AuditStatus.running, AuditStatus.queued]))
        ) or 0,
        "failed": db.scalar(select(func.count(AuditRun.id)).where(AuditRun.status == AuditStatus.failed)) or 0,
    }


def get_recent_activity(db: Session, limit: int = 6) -> list[AuditRun]:
    return db.scalars(
        select(AuditRun).options(selectinload(AuditRun.website)).order_by(AuditRun.created_at.desc()).limit(limit)
    ).all()


def get_report_overview(db: Session) -> dict[str, int]:
    completed = db.scalars(select(AuditRun).where(AuditRun.status == AuditStatus.completed)).all()
    return {
        "total": len(completed),
        "html": sum(1 for audit in completed if audit.report_html_path),
        "csv": sum(1 for audit in completed if audit.report_csv_path),
        "pdf": sum(1 for audit in completed if audit.report_pdf_path),
    }


def build_issue_breakdown(audit_run: AuditRun) -> dict[str, int]:
    return {
        "critical": sum(1 for issue in audit_run.issues if issue.severity == IssueSeverity.critical),
        "warning": sum(1 for issue in audit_run.issues if issue.severity == IssueSeverity.warning),
        "info": sum(1 for issue in audit_run.issues if issue.severity == IssueSeverity.info),
    }


def build_issue_type_summary(audit_run: AuditRun, limit: int = 6) -> list[tuple[str, int]]:
    issue_counts: dict[str, int] = {}
    for issue in audit_run.issues:
        issue_counts[issue.issue_type] = issue_counts.get(issue.issue_type, 0) + 1
    return sorted(issue_counts.items(), key=lambda item: item[1], reverse=True)[:limit]


def build_phase_timings(audit_run: AuditRun) -> dict[str, str]:
    return {
        "crawl": _format_duration(audit_run.crawl_started_at, audit_run.crawl_completed_at),
        "analysis": _format_duration(audit_run.analysis_started_at, audit_run.analysis_completed_at),
        "reporting": _format_duration(audit_run.reporting_started_at, audit_run.reporting_completed_at),
        "total": _format_duration(audit_run.started_at, audit_run.completed_at),
    }


def _format_duration(start, end) -> str:
    if start is None or end is None:
        return "-"
    seconds = max(int((end - start).total_seconds()), 0)
    minutes, rem = divmod(seconds, 60)
    if minutes and rem:
        return f"{minutes}m {rem}s"
    if minutes:
        return f"{minutes}m"
    return f"{rem}s"
