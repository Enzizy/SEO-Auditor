from __future__ import annotations

import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.audit_engine.types import PageSpeedResult
from app.config import get_settings

logger = logging.getLogger(__name__)


class PageSpeedClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.client = httpx.Client(timeout=httpx.Timeout(settings.request_timeout_seconds))

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def analyze(self, url: str, strategy: str) -> PageSpeedResult | None:
        params = {"url": url, "strategy": strategy, "category": ["performance", "seo"]}
        if self.settings.pagespeed_api_key:
            params["key"] = self.settings.pagespeed_api_key
        try:
            response = self.client.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed", params=params)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # pragma: no cover - remote API variability
            logger.warning("pagespeed_failed", extra={"url": url, "error": str(exc)})
            return None

        lighthouse = payload.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        audits = lighthouse.get("audits", {})
        score = categories.get("performance", {}).get("score")
        render_blocking = [
            item.get("url")
            for item in audits.get("render-blocking-resources", {}).get("details", {}).get("items", [])
            if item.get("url")
        ]
        opportunities = []
        for audit_key in ("unused-javascript", "unused-css-rules", "offscreen-images"):
            audit = audits.get(audit_key, {})
            if audit.get("title"):
                opportunities.append(audit["title"])
        return PageSpeedResult(
            url=url,
            strategy=strategy,
            score=(score * 100) if score is not None else None,
            render_blocking_resources=render_blocking,
            opportunities=opportunities,
            raw=payload,
        )
