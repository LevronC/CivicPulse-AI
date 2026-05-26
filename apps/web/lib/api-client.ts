/**
 * Typed API client for the CivicPulse backend.
 *
 * All API calls go through this module to ensure:
 * - Consistent error handling
 * - Type-safe responses
 * - Centralized base URL configuration
 * - Request/response logging in development
 */

import type {
  BreakingStoryItem,
  EntityIntelligenceResponse,
  EventDetail,
  EventFilters,
  EventSummary,
  GlobalPulseItem,
  NarrativeMapResponse,
  PaginatedResponse,
  TopEntityItem,
} from "./types";
import { getApiBase } from "./api-base";

const API_BASE = getApiBase();

class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      body?.error?.code || "UNKNOWN",
      body?.error?.message || res.statusText
    );
  }

  return res.json() as Promise<T>;
}

export const api = {
  events: {
    list(
      filters: EventFilters = {},
      pagination: { offset?: number; limit?: number } = {}
    ): Promise<PaginatedResponse<EventSummary>> {
      const params = new URLSearchParams();
      if (filters.topic) params.set("topic", filters.topic);
      if (filters.sentiment) params.set("sentiment", filters.sentiment);
      if (filters.min_impact) params.set("min_impact", String(filters.min_impact));
      if (pagination.offset) params.set("offset", String(pagination.offset));
      if (pagination.limit) params.set("limit", String(pagination.limit));

      const qs = params.toString();
      return request<PaginatedResponse<EventSummary>>(
        `/events${qs ? `?${qs}` : ""}`
      );
    },

    detail(eventId: string): Promise<EventDetail> {
      return request<EventDetail>(`/events/${eventId}`);
    },
  },

  health(): Promise<{ status: string; database: string }> {
    return request("/health");
  },

  intelligence: {
    pulse(limit = 10): Promise<{ items: GlobalPulseItem[] }> {
      return request(`/intelligence/pulse?limit=${limit}`);
    },

    breaking(limit = 8): Promise<{ items: BreakingStoryItem[]; count: number }> {
      return request(`/intelligence/breaking?limit=${limit}`);
    },

    narrativeMap(limit = 30): Promise<NarrativeMapResponse> {
      return request(`/intelligence/narrative-map?limit=${limit}`);
    },

    topEntities(limit = 12): Promise<{ items: TopEntityItem[]; count: number }> {
      return request(`/intelligence/entities?limit=${limit}`);
    },

    entity(name: string): Promise<EntityIntelligenceResponse> {
      return request(`/intelligence/entities/${encodeURIComponent(name)}`);
    },
  },
};

export { ApiError };
