from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.audit_engine.parsers.html_parser import parse_page
from app.audit_engine.types import AssetResource, CrawledPage, ImageResource, LinkResource
from app.audit_engine.utils.url_tools import get_domain, normalize_url
from app.config import get_settings

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - optional in some environments
    sync_playwright = None


ProgressCallback = Callable[[CrawledPage, int], None]


class WebsiteCrawler:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.timeout = httpx.Timeout(settings.request_timeout_seconds)
        self.client = httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": settings.crawler_user_agent},
        )

    def crawl(
        self,
        start_url: str,
        max_pages: int,
        max_depth: int,
        render_mode: str,
        external_link_check: bool,
        on_page: ProgressCallback | None = None,
    ) -> list[CrawledPage]:
        base_domain = get_domain(start_url)
        queue: deque[tuple[str, int]] = deque([(start_url, 0)])
        visited: set[str] = set()
        pages: list[CrawledPage] = []
        link_status_cache: dict[str, int | None] = {}
        asset_probe_cache: dict[str, tuple[int | None, str | None]] = {}

        while queue and len(pages) < max_pages:
            current_url, depth = queue.popleft()
            normalized_url = normalize_url(current_url)
            if normalized_url in visited:
                continue
            visited.add(normalized_url)

            response = self._fetch_html(current_url, render_mode)
            if response is None:
                continue

            parsed = parse_page(response["url"], response["html"], base_domain)
            links = [
                LinkResource(
                    url=link.url,
                    normalized_url=link.normalized_url,
                    is_internal=link.is_internal,
                    status_code=self._check_link_status(link.url, link_status_cache)
                    if link.is_internal or external_link_check
                    else None,
                )
                for link in parsed["links"]
            ]
            images = [self._enrich_image(image, asset_probe_cache) for image in parsed["images"]]
            assets = [self._enrich_asset(asset, asset_probe_cache) for asset in parsed["assets"]]

            page = CrawledPage(
                url=response["url"],
                normalized_url=normalize_url(response["url"]),
                depth=depth,
                status_code=response["status_code"],
                html=response["html"],
                title=parsed["title"],
                meta_description=parsed["meta_description"],
                h1_count=parsed["h1_count"],
                word_count=parsed["word_count"],
                text_content=parsed["text_content"],
                links=links,
                images=images,
                assets=assets,
            )
            pages.append(page)
            if on_page:
                on_page(page, len(pages))

            if depth >= max_depth:
                continue
            for link in links:
                if link.is_internal and link.normalized_url not in visited:
                    queue.append((link.url, depth + 1))

        return pages

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    def _request(self, url: str, method: str = "GET") -> httpx.Response:
        return self.client.request(method, url)

    def _fetch_html(self, url: str, render_mode: str) -> dict | None:
        try:
            response = self._request(url)
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                return None
            html = response.text
            if render_mode == "on" or (render_mode == "auto" and _should_render_with_js(html)):
                rendered = self._render_with_playwright(url)
                if rendered:
                    html = rendered
            return {"url": str(response.url), "status_code": response.status_code, "html": html}
        except Exception as exc:  # pragma: no cover - network variability
            logger.warning("crawler_fetch_failed", extra={"url": url, "error": str(exc)})
            return None

    def _check_link_status(self, url: str, cache: dict[str, int | None]) -> int | None:
        normalized = normalize_url(url)
        if normalized in cache:
            return cache[normalized]
        try:
            response = self._request(url, method="HEAD")
            status_code = response.status_code
            if status_code >= 400 or status_code == 405:
                status_code = self._request(url, method="GET").status_code
        except Exception:  # pragma: no cover - network variability
            status_code = None
        cache[normalized] = status_code
        return status_code

    def _probe_asset(self, url: str, cache: dict[str, tuple[int | None, str | None]]) -> tuple[int | None, str | None]:
        normalized = normalize_url(url)
        if normalized in cache:
            return cache[normalized]
        try:
            response = self._request(url, method="HEAD")
            size = int(response.headers.get("content-length", "0")) or None
            content_type = response.headers.get("content-type", "").split(";")[0] or None
        except Exception:  # pragma: no cover - network variability
            size, content_type = None, None
        cache[normalized] = (size, content_type)
        return size, content_type

    def _enrich_image(
        self,
        image: ImageResource,
        cache: dict[str, tuple[int | None, str | None]],
    ) -> ImageResource:
        size_bytes, content_type = self._probe_asset(image.url, cache)
        image.size_bytes = size_bytes
        image.format = _asset_format(image.url, content_type)
        return image

    def _enrich_asset(
        self,
        asset: AssetResource,
        cache: dict[str, tuple[int | None, str | None]],
    ) -> AssetResource:
        size_bytes, content_type = self._probe_asset(asset.url, cache)
        asset.size_bytes = size_bytes
        asset.format = _asset_format(asset.url, content_type)
        return asset

    def _render_with_playwright(self, url: str) -> str | None:
        if sync_playwright is None:
            return None
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=self.settings.request_timeout_seconds * 1000)
                html = page.content()
                browser.close()
                return html
        except Exception as exc:  # pragma: no cover - browser/runtime variability
            logger.warning("playwright_render_failed", extra={"url": url, "error": str(exc)})
            return None


def _should_render_with_js(html: str) -> bool:
    return html.count("<script") > 6 and len(html) < 80_000


def _asset_format(url: str, content_type: str | None) -> str | None:
    if content_type:
        return content_type.split("/")[-1]
    if "." in url.rsplit("/", maxsplit=1)[-1]:
        return url.rsplit(".", maxsplit=1)[-1].lower()
    return None
