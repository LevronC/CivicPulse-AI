CREATE TABLE IF NOT EXISTS articles (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  url TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  published_at TIMESTAMPTZ NOT NULL,
  language TEXT NOT NULL,
  inserted_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS article_enrichment (
  article_id TEXT PRIMARY KEY REFERENCES articles(id),
  summary TEXT NOT NULL,
  topic TEXT NOT NULL,
  sentiment TEXT NOT NULL,
  entities JSONB NOT NULL,
  embedding JSONB NOT NULL,
  enriched_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  topic TEXT NOT NULL,
  sentiment TEXT NOT NULL,
  latitude DOUBLE PRECISION NOT NULL,
  longitude DOUBLE PRECISION NOT NULL,
  impact_score DOUBLE PRECISION NOT NULL,
  article_ids JSONB NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL
);
