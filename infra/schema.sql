-- CivicPulse AI database schema
-- Version: 2
-- Changes from v1: added lifecycle, confidence, model_version columns

CREATE TABLE IF NOT EXISTS articles (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  url TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  published_at TIMESTAMPTZ NOT NULL,
  language TEXT NOT NULL DEFAULT 'en',
  inserted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC);

CREATE TABLE IF NOT EXISTS article_enrichment (
  article_id TEXT PRIMARY KEY REFERENCES articles(id) ON DELETE CASCADE,
  summary TEXT NOT NULL,
  topic TEXT NOT NULL,
  sentiment TEXT NOT NULL,
  entities JSONB NOT NULL DEFAULT '[]',
  embedding JSONB NOT NULL DEFAULT '[]',
  model_version TEXT NOT NULL DEFAULT 'heuristic-v1',
  enriched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_enrichment_topic ON article_enrichment(topic);

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  topic TEXT NOT NULL,
  sentiment TEXT NOT NULL,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  impact_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  article_ids JSONB NOT NULL DEFAULT '[]',
  lifecycle TEXT NOT NULL DEFAULT 'active',
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_impact ON events(impact_score DESC);
CREATE INDEX IF NOT EXISTS idx_events_topic ON events(topic);
CREATE INDEX IF NOT EXISTS idx_events_lifecycle ON events(lifecycle);
