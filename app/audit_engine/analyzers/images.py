from __future__ import annotations

from app.audit_engine.types import CrawledPage, IssuePayload
from app.config import get_settings
from app.models.audit_issue import IssueSeverity


def analyze_images(page: CrawledPage) -> tuple[list[IssuePayload], int]:
    settings = get_settings()
    issues: list[IssuePayload] = []
    missing_alt_count = 0

    for image in page.images:
        if not image.alt_text:
            missing_alt_count += 1
        if image.size_bytes and image.size_bytes > settings.safe_large_image_bytes:
            issues.append(
                IssuePayload(
                    issue_type="large_image",
                    severity=IssueSeverity.warning,
                    message=f"Large image detected: {image.url}",
                    recommendation="Compress the image, resize it, or deliver a modern responsive variant.",
                    page_url=page.url,
                )
            )
        if image.format and image.format.lower() != "webp":
            issues.append(
                IssuePayload(
                    issue_type="non_webp_image",
                    severity=IssueSeverity.info,
                    message=f"Image is not served as WebP: {image.url}",
                    recommendation="Consider converting images to WebP or AVIF where browser support allows.",
                    page_url=page.url,
                )
            )
        if image.width is None or image.height is None:
            issues.append(
                IssuePayload(
                    issue_type="missing_image_dimensions",
                    severity=IssueSeverity.info,
                    message=f"Image is missing width/height attributes: {image.url}",
                    recommendation="Set width and height attributes to reduce layout shifts.",
                    page_url=page.url,
                )
            )

    if missing_alt_count:
        issues.append(
            IssuePayload(
                issue_type="missing_alt_text",
                severity=IssueSeverity.warning,
                message=f"Detected {missing_alt_count} image(s) without ALT text.",
                recommendation="Add descriptive ALT text to meaningful images.",
                page_url=page.url,
            )
        )

    return issues, missing_alt_count

