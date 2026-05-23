"""Tests for article deduplication and ID generation."""

from src.services.ingestion.dedupe import generate_article_id


class TestArticleIdGeneration:
    def test_deterministic_output(self) -> None:
        id1 = generate_article_id("https://example.com/a", "Title A")
        id2 = generate_article_id("https://example.com/a", "Title A")
        assert id1 == id2

    def test_different_urls_produce_different_ids(self) -> None:
        id1 = generate_article_id("https://example.com/a", "Title")
        id2 = generate_article_id("https://example.com/b", "Title")
        assert id1 != id2

    def test_different_titles_produce_different_ids(self) -> None:
        id1 = generate_article_id("https://example.com/a", "Title A")
        id2 = generate_article_id("https://example.com/a", "Title B")
        assert id1 != id2

    def test_case_insensitive(self) -> None:
        id1 = generate_article_id("https://example.com/a", "Title A")
        id2 = generate_article_id("HTTPS://EXAMPLE.COM/A", "TITLE A")
        assert id1 == id2

    def test_whitespace_trimmed(self) -> None:
        id1 = generate_article_id("https://example.com/a", "Title A")
        id2 = generate_article_id("  https://example.com/a  ", "  Title A  ")
        assert id1 == id2

    def test_id_length(self) -> None:
        aid = generate_article_id("https://example.com/a", "Title")
        assert len(aid) == 16
