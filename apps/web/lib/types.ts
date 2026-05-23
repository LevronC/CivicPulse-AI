/**
 * Shared TypeScript types matching the backend Pydantic contracts.
 *
 * These types are the frontend's single source of truth for all API
 * data shapes. They must stay in sync with packages/shared/schemas
 * and apps/api/src/contracts/.
 */

export type Topic =
  | "politics"
  | "disaster"
  | "technology"
  | "economics"
  | "conflict"
  | "other";

export type SentimentLabel = "positive" | "neutral" | "negative";

export type EventLifecycle = "draft" | "active" | "stale" | "archived" | "merged";

export interface EventGraphNode {
  id: string;
  title: string;
  summary: string;
  topic: Topic;
  sentiment: SentimentLabel;
  lifecycle: EventLifecycle;
  impact_score: number;
  confidence: number;
  velocity: number;
  article_count: number;
  entity_set: string[];
  intelligence_score: number;
  updated_at: string;
}

export interface GlobalPulseItem {
  event: EventGraphNode;
  rank: number;
  velocity: number;
  recency_hours: number;
  source_diversity: number;
  entity_centrality: number;
  velocity_score: number;
}

export interface BreakingStoryItem {
  event: EventGraphNode;
  breaking_score: number;
  velocity: number;
  article_growth: number;
  hours_active: number;
  signal: string;
}

export interface EntityRecord {
  id: string;
  name: string;
  normalized_name: string;
  entity_type: string;
  created_at: string;
}

export interface TopEntityItem {
  entity: EntityRecord;
  event_count: number;
  total_articles: number;
}

export interface NarrativeMapNode {
  id: string;
  title: string;
  topic: Topic;
  velocity: number;
  article_count: number;
  entity_centrality: number;
  intelligence_score: number;
}

export interface NarrativeMapEdge {
  source_id: string;
  target_id: string;
  relationship_type: string;
  weight: number;
  label: string;
}

export interface NarrativeMapResponse {
  nodes: NarrativeMapNode[];
  edges: NarrativeMapEdge[];
  generated_at: string;
}

export interface EntityIntelligenceResponse {
  entity: EntityRecord;
  events: EventGraphNode[];
  total_articles: number;
}

export interface EventSummary {
  id: string;
  title: string;
  summary: string;
  topic: Topic;
  sentiment: SentimentLabel;
  latitude: number;
  longitude: number;
  impact_score: number;
  article_count: number;
  lifecycle: EventLifecycle;
  updated_at: string;
}

export interface EventRecord {
  id: string;
  title: string;
  summary: string;
  topic: Topic;
  sentiment: SentimentLabel;
  latitude: number;
  longitude: number;
  impact_score: number;
  article_ids: string[];
  lifecycle: EventLifecycle;
  confidence: number;
  updated_at: string;
}

export interface ArticleRecord {
  id: string;
  source: string;
  url: string;
  title: string;
  body: string;
  published_at: string;
  language: string;
  inserted_at: string;
}

export interface EventDetail {
  event: EventRecord;
  articles: ArticleRecord[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  next_cursor: string | null;
}

export interface EventFilters {
  topic?: Topic;
  sentiment?: SentimentLabel;
  min_impact?: number;
}
