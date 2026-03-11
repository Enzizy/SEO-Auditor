from __future__ import annotations

from urllib.parse import urljoin, urlparse, urlunparse


def ensure_absolute_url(base_url: str, maybe_relative: str) -> str:
    return urljoin(base_url, maybe_relative)


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    normalized = parsed._replace(scheme=scheme.lower(), netloc=netloc, path=path, params="", query="", fragment="")
    return urlunparse(normalized)


def get_domain(url: str) -> str:
    return urlparse(url).netloc.lower()


def is_same_domain(candidate_url: str, base_domain: str) -> bool:
    return get_domain(candidate_url) == base_domain.lower()

