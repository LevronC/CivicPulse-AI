"""
Article deduplication utilities.

Generates deterministic article IDs from URL + title to prevent
duplicate persistence during replay storms or concurrent ingestion.
The SHA-256 prefix provides sufficient collision resistance for
the expected article volume while keeping IDs human-readable in logs.
"""

import hashlib


def generate_article_id(url: str, title: str) -> str:
    """
    Deterministic article ID from URL and title.

    Using both URL and title handles edge cases where different
    sources publish the same story at different URLs, or the same
    URL serves different content over time.
    """
    key = f"{url.strip().lower()}:{title.strip().lower()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
