import type { TopEntityItem, EntityIntelligenceResponse } from "../../../lib/types";

export function EntityExplorer({
  entities,
  detail,
  onSelect,
  onClear,
}: {
  entities: TopEntityItem[];
  detail: EntityIntelligenceResponse | null;
  onSelect: (name: string) => void;
  onClear: () => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5">
        {entities.map((item) => (
          <button
            key={item.entity.id}
            type="button"
            onClick={() => onSelect(item.entity.name)}
            className="rounded-full border border-gray-700 bg-gray-900 px-2.5 py-1 text-[11px] text-gray-300 hover:border-blue-600 hover:text-blue-300 transition-colors"
          >
            {item.entity.name}
            <span className="ml-1 text-gray-500">({item.event_count})</span>
          </button>
        ))}
      </div>

      {detail && (
        <div className="rounded-lg border border-gray-800 bg-gray-900/60 p-3">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-semibold text-gray-100">{detail.entity.name}</h4>
            <button
              type="button"
              onClick={onClear}
              className="text-[11px] text-gray-500 hover:text-gray-300"
            >
              Close
            </button>
          </div>
          <p className="text-[11px] text-gray-400 mb-2">
            {detail.events.length} events · {detail.total_articles} articles
          </p>
          <ul className="space-y-1.5 max-h-40 overflow-y-auto">
            {detail.events.map((event) => (
              <li key={event.id} className="text-xs text-gray-300 line-clamp-1">
                [{event.article_count}] {event.title}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
