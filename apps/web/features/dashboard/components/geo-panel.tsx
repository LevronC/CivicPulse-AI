import type { EventSummary } from "../../../lib/types";
import { TopicBadge } from "../../../ui/status-badge";

/**
 * Geo-context panel showing event locations.
 *
 * This is a placeholder for a proper map integration (Mapbox, Leaflet).
 * For now it renders a coordinate list with topic context to demonstrate
 * the data flow. The component interface won't change when a real map
 * library is integrated.
 */
export function GeoPanel({ events }: { events: EventSummary[] }) {
  if (events.length === 0) return null;

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">
        Event Locations
      </h3>
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {events.map((e) => (
          <div
            key={e.id}
            className="flex items-center justify-between text-xs py-1 border-b border-gray-800/50 last:border-0"
          >
            <div className="flex items-center gap-2 min-w-0">
              <TopicBadge topic={e.topic} />
              <span className="text-gray-300 truncate">{e.title}</span>
            </div>
            <span className="text-gray-600 font-mono shrink-0 ml-2">
              {e.latitude.toFixed(2)}, {e.longitude.toFixed(2)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
