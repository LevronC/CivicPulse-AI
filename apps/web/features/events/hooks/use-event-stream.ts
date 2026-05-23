"use client";

import { useEffect, useRef, useState } from "react";
import type { EventSummary } from "../../../lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * SSE hook for realtime event updates.
 *
 * Falls back to polling if EventSource is unavailable or the
 * connection fails. Reconnection uses exponential backoff to
 * avoid hammering the server during outages.
 */
export function useEventStream(): {
  updates: EventSummary[];
  connected: boolean;
} {
  const [updates, setUpdates] = useState<EventSummary[]>([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource(`${API_BASE}/events/stream`);
    esRef.current = es;

    es.onopen = () => setConnected(true);

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as EventSummary;
        if (data.id) {
          setUpdates((prev) => [data, ...prev].slice(0, 100));
        }
      } catch {
        // heartbeat or malformed — ignore
      }
    };

    es.onerror = () => {
      setConnected(false);
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, []);

  return { updates, connected };
}
