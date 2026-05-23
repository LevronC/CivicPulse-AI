import type { BreakingStoryItem } from "../../../lib/types";
import { TopicBadge } from "../../../ui/status-badge";

const SIGNAL_LABELS: Record<string, string> = {
  accelerating: "Accelerating",
  rapid_growth: "Rapid growth",
  new_story: "New story",
  developing: "Developing",
  emerging: "Emerging",
};

export function BreakingStoriesPanel({ items }: { items: BreakingStoryItem[] }) {
  if (items.length === 0) {
    return (
      <p className="text-xs text-gray-500">No breaking stories detected in the current window.</p>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <article
          key={item.event.id}
          className="rounded-lg border border-amber-900/40 bg-amber-950/20 p-3"
        >
          <div className="flex items-start justify-between gap-2 mb-1">
            <h4 className="text-sm font-medium text-amber-100 line-clamp-2">{item.event.title}</h4>
            <span className="shrink-0 text-[10px] uppercase tracking-wide text-amber-400 font-semibold">
              {SIGNAL_LABELS[item.signal] ?? item.signal}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-gray-400">
            <TopicBadge topic={item.event.topic} />
            <span>score {item.breaking_score.toFixed(0)}</span>
            <span>vel {item.velocity.toFixed(2)}</span>
            <span>+{item.article_growth} articles</span>
          </div>
        </article>
      ))}
    </div>
  );
}
