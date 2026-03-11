from __future__ import annotations

from datetime import datetime, timezone

from app.db import SessionLocal
from app.models import AssetRecord, AuditIssue, AuditRun, AuditStatus, IssueSeverity, PageAuditResult
from app.services.projects import get_or_create_project


def main() -> None:
    with SessionLocal() as db:
        project = get_or_create_project(db, "https://example.com", "Example Client")
        existing = db.query(AuditRun).filter(AuditRun.website_id == project.id).first()
        if existing:
            print("Seed data already exists.")
            return

        audit = AuditRun(
            website_id=project.id,
            start_url="https://example.com",
            status=AuditStatus.completed,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            pages_crawled=3,
            seo_score=84.0,
            performance_score=72.0,
            pagespeed_strategy="mobile",
            max_pages=10,
            max_depth=2,
            total_issues=3,
            broken_links=1,
            missing_meta_descriptions=1,
            missing_alt_images=2,
        )
        db.add(audit)
        db.flush()

        page = PageAuditResult(
            audit_run_id=audit.id,
            url="https://example.com",
            status_code=200,
            title="Example Domain",
            meta_description=None,
            h1_count=1,
            word_count=180,
            internal_links_count=4,
            external_links_count=1,
            broken_links_count=1,
            pagespeed_score=72.0,
            issues_count=3,
            missing_alt_count=2,
        )
        db.add(page)
        db.flush()

        db.add_all(
            [
                AuditIssue(
                    audit_run_id=audit.id,
                    page_result_id=page.id,
                    issue_type="missing_meta_description",
                    severity=IssueSeverity.warning,
                    message="Homepage is missing a meta description.",
                    recommendation="Write a unique meta description for the homepage.",
                ),
                AuditIssue(
                    audit_run_id=audit.id,
                    page_result_id=page.id,
                    issue_type="broken_internal_links",
                    severity=IssueSeverity.critical,
                    message="Detected 1 broken internal link.",
                    recommendation="Update the broken link target or redirect it.",
                ),
                AuditIssue(
                    audit_run_id=audit.id,
                    page_result_id=page.id,
                    issue_type="missing_alt_text",
                    severity=IssueSeverity.warning,
                    message="Detected 2 images without ALT text.",
                    recommendation="Add ALT text to informative images.",
                ),
                AssetRecord(
                    page_result_id=page.id,
                    asset_url="https://example.com/wp-content/uploads/hero.jpg",
                    asset_type="image",
                    size_bytes=412000,
                    format="jpg",
                    is_optimized=False,
                    width=None,
                    height=None,
                    compression_suggestion="Compress or resize",
                ),
            ]
        )
        db.commit()
        print("Seed data created.")


if __name__ == "__main__":
    main()
