from __future__ import annotations

import re


SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_-]?key|token|password|secret)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~-]+", re.IGNORECASE),
    re.compile(r"\b(?:sk|pk)_[A-Za-z0-9]{16,}\b"),
)


def contains_sensitive_data(content: str) -> bool:
    return any(pattern.search(content) for pattern in SECRET_PATTERNS)
