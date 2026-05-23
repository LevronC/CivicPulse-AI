"use client";

import type { EventFilters, SentimentLabel, Topic } from "../../../lib/types";

const TOPICS: { value: Topic | ""; label: string }[] = [
  { value: "", label: "All topics" },
  { value: "politics", label: "Politics" },
  { value: "disaster", label: "Disaster" },
  { value: "technology", label: "Technology" },
  { value: "economics", label: "Economics" },
  { value: "conflict", label: "Conflict" },
  { value: "other", label: "Other" },
];

const SENTIMENTS: { value: SentimentLabel | ""; label: string }[] = [
  { value: "", label: "All sentiment" },
  { value: "positive", label: "Positive" },
  { value: "neutral", label: "Neutral" },
  { value: "negative", label: "Negative" },
];

export function EventFilterBar({
  filters,
  onChange,
}: {
  filters: EventFilters;
  onChange: (filters: EventFilters) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <select
        value={filters.topic || ""}
        onChange={(e) =>
          onChange({ ...filters, topic: (e.target.value || undefined) as Topic | undefined })
        }
        className="rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        {TOPICS.map((t) => (
          <option key={t.value} value={t.value}>
            {t.label}
          </option>
        ))}
      </select>

      <select
        value={filters.sentiment || ""}
        onChange={(e) =>
          onChange({
            ...filters,
            sentiment: (e.target.value || undefined) as SentimentLabel | undefined,
          })
        }
        className="rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        {SENTIMENTS.map((s) => (
          <option key={s.value} value={s.value}>
            {s.label}
          </option>
        ))}
      </select>
    </div>
  );
}
