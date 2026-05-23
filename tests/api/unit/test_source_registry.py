from __future__ import annotations

from src.config.settings import Settings, SourceSettings
from src.services.ingestion.registry import build_source_adapters


def test_registry_falls_back_to_mock_when_no_real_provider_is_configured() -> None:
    settings = Settings(sources=SourceSettings(enabled_providers=[]))

    adapters = build_source_adapters(settings)

    assert [adapter.source_name for adapter in adapters] == ["mock"]


def test_registry_builds_configured_rss_and_gdelt_adapters() -> None:
    settings = Settings(
        sources=SourceSettings(
            enabled_providers=["rss", "gdelt"],
            rss_feeds=["https://example.com/rss"],
        )
    )

    adapters = build_source_adapters(settings)

    assert [adapter.source_name for adapter in adapters] == ["rss", "gdelt"]
