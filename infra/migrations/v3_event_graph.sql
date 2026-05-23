-- CivicPulse AI schema migration v3: Event Graph
-- Run after schema.sql: psql -U civicpulse -d civicpulse -f infra/migrations/v3_event_graph.sql

ALTER TABLE events ADD COLUMN IF NOT EXISTS centroid_embedding JSONB NOT NULL DEFAULT '[]';
ALTER TABLE events ADD COLUMN IF NOT EXISTS entity_set JSONB NOT NULL DEFAULT '[]';
ALTER TABLE events ADD COLUMN IF NOT EXISTS velocity DOUBLE PRECISION NOT NULL DEFAULT 0.0;
ALTER TABLE events ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMPTZ;
ALTER TABLE events ADD COLUMN IF NOT EXISTS last_article_at TIMESTAMPTZ;
ALTER TABLE events ADD COLUMN IF NOT EXISTS parent_event_id TEXT REFERENCES events(id);
ALTER TABLE events ADD COLUMN IF NOT EXISTS article_count INT NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_events_velocity ON events(velocity DESC);
CREATE INDEX IF NOT EXISTS idx_events_last_article ON events(last_article_at DESC);

CREATE TABLE IF NOT EXISTS entities (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  normalized_name TEXT NOT NULL UNIQUE,
  entity_type TEXT NOT NULL DEFAULT 'unknown',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_entities_normalized ON entities(normalized_name);

CREATE TABLE IF NOT EXISTS event_entities (
  event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  mention_count INT NOT NULL DEFAULT 1,
  PRIMARY KEY (event_id, entity_id)
);

CREATE TABLE IF NOT EXISTS event_relationships (
  id TEXT PRIMARY KEY,
  source_event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  target_event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  relationship_type TEXT NOT NULL,
  weight DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_event_rel_source ON event_relationships(source_event_id);
CREATE INDEX IF NOT EXISTS idx_event_rel_target ON event_relationships(target_event_id);

CREATE TABLE IF NOT EXISTS article_event_links (
  article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  similarity DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  linked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (article_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_article_event_event ON article_event_links(event_id);

CREATE TABLE IF NOT EXISTS event_snapshots (
  id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  article_count INT NOT NULL,
  sentiment TEXT NOT NULL,
  impact_score DOUBLE PRECISION NOT NULL,
  velocity DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  entity_set JSONB NOT NULL DEFAULT '[]',
  snapshot_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_event_time ON event_snapshots(event_id, snapshot_at DESC);
