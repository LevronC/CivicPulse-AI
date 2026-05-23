/**
 * Shared TypeScript types for the CivicPulse platform.
 *
 * These are the cross-service contract types. Both the web app
 * and any future TypeScript services should import from here
 * to ensure type consistency across the platform.
 */

export type Topic =
  | "politics"
  | "disaster"
  | "technology"
  | "economics"
  | "conflict"
  | "other";

export type SentimentLabel = "positive" | "neutral" | "negative";
export type EventLifecycle = "draft" | "active" | "stale" | "archived";

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

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  next_cursor: string | null;
}
