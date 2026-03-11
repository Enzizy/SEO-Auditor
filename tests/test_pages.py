from __future__ import annotations

from app import db as db_state
from app.models import AuditRun


def test_dashboard_renders(client) -> None:
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Joyno SEO Auditor Tool" in response.text


def test_create_audit_enqueues_job(client) -> None:
    response = client.post(
        "/audits",
        data={
            "website_url": "https://example.com",
            "project_label": "Example Project",
            "max_pages": 10,
            "max_depth": 1,
            "pagespeed_strategy": "mobile",
            "js_render_mode": "auto",
            "external_link_check": "true",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers["location"]
    assert location.startswith("/audits/")

    with db_state.SessionLocal() as db:
        audit = db.query(AuditRun).first()
        assert audit is not None
        assert audit.job_id == "inline-audit-test"


def test_audit_status_endpoint_returns_payload(client) -> None:
    client.post(
        "/audits",
        data={
            "website_url": "https://example.com",
            "project_label": "Example Project",
            "max_pages": 10,
            "max_depth": 1,
            "pagespeed_strategy": "mobile",
            "js_render_mode": "auto",
            "external_link_check": "true",
        },
        follow_redirects=False,
    )
    response = client.get("/audits/1/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["audit_id"] == 1
    assert "progress_stage" in payload
    assert "progress_message" in payload


def test_reports_page_renders(client) -> None:
    response = client.get("/reports")
    assert response.status_code == 200
    assert "Audit report exports" in response.text


def test_history_page_filters_render(client) -> None:
    response = client.get("/history?status=queued&query=example")
    assert response.status_code == 200
    assert "Audit history dashboard" in response.text
