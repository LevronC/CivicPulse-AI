import type { EventSummary } from "../../../lib/types";

export function SentimentSnapshot({ events }: { events: EventSummary[] }) {
  const counts = {
    positive: events.filter((e) => e.sentiment === "positive").length,
    neutral: events.filter((e) => e.sentiment === "neutral").length,
    negative: events.filter((e) => e.sentiment === "negative").length,
  };
  const total = events.length || 1;

  const segments = [
    { label: "Positive", count: counts.positive, color: "bg-green-500", text: "text-green-300" },
    { label: "Neutral", count: counts.neutral, color: "bg-gray-500", text: "text-gray-300" },
    { label: "Negative", count: counts.negative, color: "bg-red-500", text: "text-red-300" },
  ];

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">
        Sentiment Distribution
      </h3>

      <div className="flex h-2 rounded-full overflow-hidden bg-gray-800 mb-4">
        {segments.map((s) => (
          <div
            key={s.label}
            className={`${s.color} transition-all duration-500`}
            style={{ width: `${(s.count / total) * 100}%` }}
          />
        ))}
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        {segments.map((s) => (
          <div key={s.label}>
            <div className={`text-lg font-bold ${s.text}`}>{s.count}</div>
            <div className="text-xs text-gray-500">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
