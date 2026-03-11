from __future__ import annotations

from app.audit_engine.parsers.html_parser import parse_page


def test_parse_page_extracts_core_fields() -> None:
    html = """
    <html>
      <head>
        <title>Home</title>
        <meta name="description" content="Demo description" />
        <link rel="stylesheet" href="/styles.css" />
      </head>
      <body>
        <h1>Heading</h1>
        <a href="/about">About</a>
        <img src="/image.jpg" alt="Hero" width="200" height="100" />
        <script src="/app.js"></script>
      </body>
    </html>
    """

    parsed = parse_page("https://example.com", html, "example.com")

    assert parsed["title"] == "Home"
    assert parsed["meta_description"] == "Demo description"
    assert parsed["h1_count"] == 1
    assert len(parsed["links"]) == 1
    assert parsed["links"][0].is_internal is True
    assert len(parsed["images"]) == 1
    assert len(parsed["assets"]) == 2

