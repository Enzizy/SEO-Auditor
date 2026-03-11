from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.audit_engine.analyzers.images import analyze_images
from app.audit_engine.analyzers.performance import analyze_page_assets, analyze_pagespeed
from app.audit_engine.analyzers.seo import analyze_page_seo, build_duplicate_sets
from app.audit_engine.crawler.service import WebsiteCrawler
from app.audit_engine.integrations.pagespeed import PageSpeedClient
from app.audit_engine.reporters.service import generate_reports
from app.audit_engine.scoring.service import calculate_scores
from app.audit_engine.types import PageAnalysis
from app.models import AssetRecord, AuditIssue, AuditRun, AuditStatus, PageAuditResult

logger = logging.getLogger(__name__)


def execute_audit_run(db: Session, audit_run: AuditRun) -> AuditRun:
    crawler = WebsiteCrawler()
    pagespeed_client = PageSpeedClient()
    now = datetime.now(timezone.utc)
    audit_run.status = AuditStatus.running
    audit_run.started_at = now
    audit_run.progress_stage = "initializing"
    audit_run.progress_message = "Preparing crawler and audit context."
    db.add(audit_run)
    db.commit()
    db.refresh(audit_run)

    def on_progress(page, crawled_count: int) -> None:
        audit_run.pages_crawled = crawled_count
        audit_run.current_page_url = page.url
        audit_run.progress_stage = "crawling"
        audit_run.progress_message = f"Crawling and parsing page {crawled_count}: {page.url}"
        db.add(audit_run)
        db.commit()

    try:
        audit_run.crawl_started_at = datetime.now(timezone.utc)
        audit_run.progress_stage = "crawling"
        audit_run.progress_message = "Collecting internal links and page content."
        db.add(audit_run)
        db.commit()
        crawled_pages = crawler.crawl(
            start_url=audit_run.start_url,
            max_pages=audit_run.max_pages,
            max_depth=audit_run.max_depth,
            render_mode=audit_run.js_render_mode,
            external_link_check=audit_run.external_link_check,
            on_page=on_progress,
        )
        audit_run.crawl_completed_at = datetime.now(timezone.utc)
        audit_run.analysis_started_at = audit_run.crawl_completed_at
        duplicate_titles, duplicate_descriptions = build_duplicate_sets(crawled_pages)
        page_analyses: list[PageAnalysis] = []
        missing_meta = 0
        missing_alt = 0
        broken_links = 0

        for page in crawled_pages:
            seo_analysis = analyze_page_seo(page, duplicate_titles, duplicate_descriptions)
            image_issues, missing_alt_count = analyze_images(page)
            asset_issues = analyze_page_assets(page)
            seo_analysis.issues.extend(image_issues)
            seo_analysis.issues.extend(asset_issues)
            missing_alt += missing_alt_count
            missing_meta += int(page.meta_description is None)
            broken_links += seo_analysis.broken_internal_links + seo_analysis.broken_external_links
            page_analyses.append(seo_analysis)

        audit_run.progress_stage = "performance"
        audit_run.progress_message = "Requesting homepage PageSpeed Insights data."
        db.add(audit_run)
        db.commit()
        pagespeed_result = pagespeed_client.analyze(audit_run.start_url, audit_run.pagespeed_strategy)
        if page_analyses and pagespeed_result:
            page_analyses[0].pagespeed_score = pagespeed_result.score
            page_analyses[0].issues.extend(analyze_pagespeed(pagespeed_result))

        seo_score, performance_score = calculate_scores(page_analyses, pagespeed_result)
        audit_run.progress_stage = "persisting"
        audit_run.progress_message = "Saving page results, issues, and asset records."
        db.add(audit_run)
        db.commit()
        _persist_results(db, audit_run, page_analyses)
        audit_run.analysis_completed_at = datetime.now(timezone.utc)

        audit_run.reporting_started_at = datetime.now(timezone.utc)
        audit_run.progress_stage = "reporting"
        audit_run.progress_message = "Generating HTML, CSV, and PDF reports."
        db.add(audit_run)
        db.commit()
        artifacts = generate_reports(
            audit_run=audit_run,
            website=audit_run.website,
            page_analyses=page_analyses,
            pagespeed_result=pagespeed_result,
            seo_score=seo_score,
            performance_score=performance_score,
        )

        audit_run.status = AuditStatus.completed
        audit_run.reporting_completed_at = datetime.now(timezone.utc)
        audit_run.completed_at = audit_run.reporting_completed_at
        audit_run.pages_crawled = len(crawled_pages)
        audit_run.seo_score = seo_score
        audit_run.performance_score = performance_score
        audit_run.report_html_path = artifacts.html_path
        audit_run.report_pdf_path = artifacts.pdf_path
        audit_run.report_csv_path = artifacts.csv_path
        audit_run.current_page_url = None
        audit_run.progress_stage = "completed"
        audit_run.progress_message = "Audit finished successfully."
        audit_run.total_issues = sum(len(analysis.issues) for analysis in page_analyses)
        audit_run.broken_links = broken_links
        audit_run.missing_meta_descriptions = missing_meta
        audit_run.missing_alt_images = missing_alt
        db.add(audit_run)
        db.commit()
        db.refresh(audit_run)
        return audit_run
    except Exception as exc:  # pragma: no cover - orchestration guards
        logger.exception("audit_run_failed", extra={"audit_run_id": audit_run.id})
        audit_run.status = AuditStatus.failed
        audit_run.completed_at = datetime.now(timezone.utc)
        if audit_run.progress_stage == "crawling" and audit_run.crawl_completed_at is None:
            audit_run.crawl_completed_at = audit_run.completed_at
        elif audit_run.progress_stage in {"performance", "persisting"} and audit_run.analysis_completed_at is None:
            audit_run.analysis_completed_at = audit_run.completed_at
        elif audit_run.progress_stage == "reporting" and audit_run.reporting_completed_at is None:
            audit_run.reporting_completed_at = audit_run.completed_at
        audit_run.current_page_url = None
        audit_run.progress_stage = "failed"
        audit_run.progress_message = "Audit failed before completion."
        audit_run.error_message = str(exc)
        db.add(audit_run)
        db.commit()
        raise


def _persist_results(db: Session, audit_run: AuditRun, page_analyses: list[PageAnalysis]) -> None:
    for analysis in page_analyses:
        page_result = PageAuditResult(
            audit_run_id=audit_run.id,
            url=analysis.page.url,
            status_code=analysis.page.status_code,
            title=analysis.page.title,
            meta_description=analysis.page.meta_description,
            h1_count=analysis.page.h1_count,
            word_count=analysis.page.word_count,
            internal_links_count=analysis.page.internal_links_count,
            external_links_count=analysis.page.external_links_count,
            broken_links_count=analysis.broken_internal_links + analysis.broken_external_links,
            pagespeed_score=analysis.pagespeed_score,
            issues_count=len(analysis.issues),
            missing_alt_count=sum(1 for image in analysis.page.images if not image.alt_text),
        )
        db.add(page_result)
        db.flush()

        for issue in analysis.issues:
            db.add(
                AuditIssue(
                    audit_run_id=audit_run.id,
                    page_result_id=page_result.id,
                    issue_type=issue.issue_type,
                    severity=issue.severity,
                    message=issue.message,
                    recommendation=issue.recommendation,
                )
            )

        for image in analysis.page.images:
            db.add(
                AssetRecord(
                    page_result_id=page_result.id,
                    asset_url=image.url,
                    asset_type="image",
                    size_bytes=image.size_bytes,
                    format=image.format,
                    is_optimized=(image.format or "").lower() == "webp",
                    width=image.width,
                    height=image.height,
                    compression_suggestion="Compress or resize"
                    if image.size_bytes and image.size_bytes > 250_000
                    else None,
                )
            )
        for asset in analysis.page.assets:
            db.add(
                AssetRecord(
                    page_result_id=page_result.id,
                    asset_url=asset.url,
                    asset_type=asset.asset_type,
                    size_bytes=asset.size_bytes,
                    format=asset.format,
                    is_optimized=bool(asset.size_bytes and asset.size_bytes < 200_000),
                )
            )
    db.commit()
