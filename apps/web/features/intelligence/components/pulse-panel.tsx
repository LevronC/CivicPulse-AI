import type { GlobalPulseItem } from "../../../lib/types";
import { TopicBadge } from "../../../ui/status-badge";

export function PulsePanel({ items }: { items: GlobalPulseItem[] }) {
  if (items.length === 0) {
    return <p className="text-xs text-gray-500">No ranked events available.</p>;
  }

  return (
    <ol className="space-y-2">
      {items.map((item) => (
        <li
          key={item.event.id}
          className="rounded-lg border border-gray-800 bg-gray-900/40 p-3"
        >
          <div className="flex items-start gap-2">
            <span className="text-xs font-mono text-blue-400 shrink-0">#{item.rank}</span>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-gray-100 line-clamp-2">{item.event.title}</p>
              <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-gray-500">
                <TopicBadge topic={item.event.topic} />
                <span>score {item.event.intelligence_score.toFixed(0)}</span>
                <span>vel {item.velocity_score.toFixed(0)}</span>
                <span>cent {Math.round(item.entity_centrality * 100)}%</span>
              </div>
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
