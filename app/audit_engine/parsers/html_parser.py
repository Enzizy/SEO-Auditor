from __future__ import annotations

from bs4 import BeautifulSoup

from app.audit_engine.types import AssetResource, ImageResource, LinkResource
from app.audit_engine.utils.text import tokenize_text
from app.audit_engine.utils.url_tools import ensure_absolute_url, is_same_domain, normalize_url


def parse_page(url: str, html: str, base_domain: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_tag.get("content", "").strip() if meta_tag and meta_tag.get("content") else None
    h1_count = len(soup.find_all("h1"))
    text_content = " ".join(soup.stripped_strings)
    word_count = len(tokenize_text(text_content))

    links: list[LinkResource] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute_url = ensure_absolute_url(url, href)
        links.append(
            LinkResource(
                url=absolute_url,
                normalized_url=normalize_url(absolute_url),
                is_internal=is_same_domain(absolute_url, base_domain),
            )
        )

    images: list[ImageResource] = []
    for img in soup.find_all("img", src=True):
        src = img.get("src", "").strip()
        if not src:
            continue
        absolute_url = ensure_absolute_url(url, src)
        images.append(
            ImageResource(
                url=absolute_url,
                normalized_url=normalize_url(absolute_url),
                alt_text=img.get("alt"),
                width=_parse_int(img.get("width")),
                height=_parse_int(img.get("height")),
            )
        )

    assets: list[AssetResource] = []
    for script in soup.find_all("script", src=True):
        src = script.get("src", "").strip()
        if src:
            absolute_url = ensure_absolute_url(url, src)
            assets.append(AssetResource(url=absolute_url, normalized_url=normalize_url(absolute_url), asset_type="script"))
    for css in soup.find_all("link", href=True):
        rel = " ".join(css.get("rel", []))
        if "stylesheet" in rel:
            absolute_url = ensure_absolute_url(url, css.get("href", "").strip())
            assets.append(AssetResource(url=absolute_url, normalized_url=normalize_url(absolute_url), asset_type="stylesheet"))

    return {
        "title": title,
        "meta_description": meta_description,
        "h1_count": h1_count,
        "word_count": word_count,
        "text_content": text_content,
        "links": links,
        "images": images,
        "assets": assets,
    }


def _parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None
