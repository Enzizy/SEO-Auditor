from __future__ import annotations

import re
from collections import Counter


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "with",
    "your",
}


def tokenize_text(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9']+", text) if len(token) > 2]


def keyword_density(text: str, limit: int = 8) -> list[tuple[str, float]]:
    tokens = [token for token in tokenize_text(text) if token not in STOP_WORDS]
    if not tokens:
        return []
    counts = Counter(tokens)
    total = len(tokens)
    return [(word, round((count / total) * 100, 2)) for word, count in counts.most_common(limit)]

