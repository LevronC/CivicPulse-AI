"""Tests for Neon/Vercel database URL resolution."""

from src.config.database_url import normalize_database_url, resolve_database_url


def test_normalize_postgres_scheme(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    url = normalize_database_url("postgres://u:p@host/db?sslmode=require")
    assert url.startswith("postgresql+psycopg://")


def test_empty_database_url_falls_back_to_postgres_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("POSTGRES_URL", "postgresql://u:p@host/neondb?sslmode=require")
    url = resolve_database_url()
    assert url == "postgresql+psycopg://u:p@host/neondb?sslmode=require"


def test_quoted_empty_database_url_is_ignored(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", '""')
    monkeypatch.setenv("POSTGRES_URL", "postgresql://u:p@host/neondb")
    url = resolve_database_url()
    assert "neondb" in url
