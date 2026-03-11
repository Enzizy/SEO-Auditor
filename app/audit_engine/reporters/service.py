from __future__ import annotations

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from app.audit_engine.types import AuditArtifacts, PageAnalysis, PageSpeedResult
from app.config import BASE_DIR
from app.models.audit_run import AuditRun
from app.models.website_project import WebsiteProject
from app.services.report_storage import ReportStorage


def generate_reports(
    audit_run: AuditRun,
    website: WebsiteProject,
    page_analyses: list[PageAnalysis],
    pagespeed_result: PageSpeedResult | None,
    seo_score: float,
    performance_score: float,
) -> AuditArtifacts:
    environment = Environment(
        loader=FileSystemLoader(str(BASE_DIR / "app" / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = environment.get_template("reports/report.html")
    html_output = template.render(
        audit=audit_run,
        website=website,
        analyses=page_analyses,
        pagespeed=pagespeed_result,
        seo_score=seo_score,
        performance_score=performance_score,
    )
    storage = ReportStorage()
    html_report = storage.save_text(audit_run.id, "report.html", html_output, "text/html")
    pdf_bytes = HTML(string=html_output, base_url=str(BASE_DIR)).write_pdf()
    pdf_report = storage.save_bytes(audit_run.id, "report.pdf", pdf_bytes, "application/pdf")

    rows = []
    for analysis in page_analyses:
        rows.append(
            {
                "url": analysis.page.url,
                "status_code": analysis.page.status_code,
                "title": analysis.page.title,
                "meta_description": analysis.page.meta_description,
                "issues_count": len(analysis.issues),
                "broken_internal_links": analysis.broken_internal_links,
                "broken_external_links": analysis.broken_external_links,
                "pagespeed_score": analysis.pagespeed_score,
                "keywords": ", ".join(f"{word}:{density}%" for word, density in analysis.keyword_density[:5]),
            }
        )
    csv_output = pd.DataFrame(rows).to_csv(index=False)
    csv_report = storage.save_text(audit_run.id, "report.csv", csv_output, "text/csv")

    return AuditArtifacts(
        html_path=html_report.location,
        pdf_path=pdf_report.location,
        csv_path=csv_report.location,
    )
