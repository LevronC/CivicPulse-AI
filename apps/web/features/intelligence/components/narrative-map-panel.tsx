import type { NarrativeMapResponse } from "../../../lib/types";

export function NarrativeMapPanel({ map }: { map: NarrativeMapResponse | null }) {
  if (!map || map.nodes.length === 0) {
    return <p className="text-xs text-gray-500">No narrative connections yet.</p>;
  }

  const titles = Object.fromEntries(map.nodes.map((n) => [n.id, n.title]));

  return (
    <div className="space-y-2 max-h-64 overflow-y-auto">
      <p className="text-[11px] text-gray-500">
        {map.nodes.length} events · {map.edges.length} connections
      </p>
      {map.edges.slice(0, 12).map((edge) => (
        <div
          key={`${edge.source_id}-${edge.target_id}`}
          className="rounded border border-gray-800 bg-gray-900/40 px-2 py-1.5 text-[11px]"
        >
          <p className="text-gray-400 line-clamp-1">{titles[edge.source_id] ?? edge.source_id}</p>
          <p className="text-blue-400/70 text-center">↕ {(edge.weight * 100).toFixed(0)}% related</p>
          <p className="text-gray-400 line-clamp-1">{titles[edge.target_id] ?? edge.target_id}</p>
        </div>
      ))}
    </div>
  );
}
