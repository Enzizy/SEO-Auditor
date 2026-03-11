from __future__ import annotations

import pandas as pd
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from weasyprint import HTML

from app.audit_engine.types import AuditArtifacts, PageAnalysis, PageSpeedResult
from app.config import BASE_DIR
from app.models.audit_run import AuditRun
from app.models.website_project import WebsiteProject
from app.services.report_storage import ReportStorage


FALLBACK_REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Joyno SEO Auditor Tool Report</title>
  <style>
    body { font-family: Arial, sans-serif; color: #0f172a; margin: 32px; }
    h1, h2, h3 { margin: 0 0 12px; }
    .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 24px 0; }
    .card { border: 1px solid #dbe3eb; border-radius: 12px; padding: 16px; background: #f8fafc; }
    table { width: 100%; border-collapse: collapse; margin-top: 18px; }
    th, td { border: 1px solid #e2e8f0; padding: 10px; text-align: left; font-size: 12px; vertical-align: top; }
    th { background: #f8fafc; }
    .issue { margin-bottom: 12px; border: 1px solid #e2e8f0; padding: 12px; border-radius: 10px; }
  </style>
</head>
<body>
  <h1>Joyno SEO Auditor Tool Report</h1>
  <p><strong>Project:</strong> {{ website.label }}</p>
  <p><strong>Domain:</strong> {{ website.domain }}</p>
  <p><strong>Audit ID:</strong> {{ audit.id }}</p>

  <div class="grid">
    <div class="card"><strong>SEO Score</strong><br>{{ seo_score }}</div>
    <div class="card"><strong>Performance Score</strong><br>{{ performance_score }}</div>
    <div class="card"><strong>Pages Crawled</strong><br>{{ analyses|length }}</div>
    <div class="card"><strong>Strategy</strong><br>{{ audit.pagespeed_strategy }}</div>
  </div>

  <h2>Page Summary</h2>
  <table>
    <thead>
      <tr>
        <th>URL</th>
        <th>Title</th>
        <th>Status</th>
        <th>Issues</th>
      </tr>
    </thead>
    <tbody>
      {% for analysis in analyses %}
        <tr>
          <td>{{ analysis.page.url }}</td>
          <td>{{ analysis.page.title or 'Missing title' }}</td>
          <td>{{ analysis.page.status_code or '-' }}</td>
          <td>{{ analysis.issues|length }}</td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
</body>
</html>"""


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
    try:
        template = environment.get_template("reports/report.html")
    except TemplateNotFound:
        template = environment.from_string(FALLBACK_REPORT_TEMPLATE)
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
