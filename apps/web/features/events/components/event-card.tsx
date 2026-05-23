import type { EventSummary } from "../../../lib/types";
import { ImpactBar } from "../../../ui/impact-bar";
import { SentimentBadge, TopicBadge } from "../../../ui/status-badge";

export function EventCard({
  event,
  onClick,
}: {
  event: EventSummary;
  onClick?: () => void;
}) {
  return (
    <article
      onClick={onClick}
      className="group rounded-lg border border-gray-800 bg-gray-900/50 p-4 hover:border-gray-700 hover:bg-gray-900/80 transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <h3 className="text-sm font-semibold text-gray-100 group-hover:text-white line-clamp-2">
          {event.title}
        </h3>
        <span className="shrink-0 text-xs text-gray-500 font-mono">
          {event.article_count} article{event.article_count !== 1 ? "s" : ""}
        </span>
      </div>

      <p className="text-xs text-gray-400 mb-3 line-clamp-2">{event.summary}</p>

      <div className="mb-2">
        <ImpactBar score={event.impact_score} />
      </div>

      <div className="flex items-center gap-2">
        <TopicBadge topic={event.topic} />
        <SentimentBadge sentiment={event.sentiment} />
        <span className="ml-auto text-xs text-gray-600">
          {event.latitude.toFixed(1)}, {event.longitude.toFixed(1)}
        </span>
      </div>
    </article>
  );
}
