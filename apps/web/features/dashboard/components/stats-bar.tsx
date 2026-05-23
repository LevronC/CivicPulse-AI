import type { EventSummary } from "../../../lib/types";

export function StatsBar({
  events,
  total,
  connected,
}: {
  events: EventSummary[];
  total: number;
  connected: boolean;
}) {
  const avgImpact =
    events.length > 0
      ? events.reduce((sum, e) => sum + e.impact_score, 0) / events.length
      : 0;

  const topicCounts = events.reduce<Record<string, number>>((acc, e) => {
    acc[e.topic] = (acc[e.topic] || 0) + 1;
    return acc;
  }, {});

  const dominantTopic =
    Object.entries(topicCounts).sort(([, a], [, b]) => b - a)[0]?.[0] || "—";

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <StatCard label="Total Events" value={String(total)} />
      <StatCard label="Avg Impact" value={avgImpact.toFixed(1)} />
      <StatCard label="Dominant Topic" value={dominantTopic} />
      <StatCard
        label="Stream"
        value={connected ? "Live" : "Offline"}
        valueColor={connected ? "text-green-400" : "text-red-400"}
      />
    </div>
  );
}

function StatCard({
  label,
  value,
  valueColor = "text-white",
}: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-3">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-lg font-bold ${valueColor}`}>{value}</div>
    </div>
  );
}
