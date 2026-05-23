"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../../../lib/api-client";
import type { EventFilters, EventSummary } from "../../../lib/types";

interface UseEventsState {
  events: EventSummary[];
  total: number;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useEvents(filters: EventFilters = {}): UseEventsState {
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.events.list(filters, { limit: 50 });
      setEvents(data.items);
      setTotal(data.total);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`${err.code}: ${err.message}`);
      } else {
        setError("Failed to load events. Is the API running?");
      }
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [filters.topic, filters.sentiment, filters.min_impact]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { events, total, loading, error, refetch: fetch };
}
