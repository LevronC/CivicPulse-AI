"use client";

import { useState } from "react";
import type { EventFilters } from "../lib/types";
import { useEvents } from "../features/events/hooks/use-events";
import { useEventStream } from "../features/events/hooks/use-event-stream";
import { useIntelligence } from "../features/intelligence/hooks/use-intelligence";
import { EventCard } from "../features/events/components/event-card";
import { EventFilterBar } from "../features/events/components/event-filters";
import { BreakingStoriesPanel } from "../features/intelligence/components/breaking-stories-panel";
import { EntityExplorer } from "../features/intelligence/components/entity-explorer";
import { NarrativeMapPanel } from "../features/intelligence/components/narrative-map-panel";
import { PulsePanel } from "../features/intelligence/components/pulse-panel";
import { SentimentSnapshot } from "../features/dashboard/components/sentiment-snapshot";
import { StatsBar } from "../features/dashboard/components/stats-bar";
import { GeoPanel } from "../features/dashboard/components/geo-panel";
import { LoadingSpinner } from "../ui/loading";
import { ErrorState, EmptyState } from "../ui/error-state";

export default function DashboardPage() {
  const [filters, setFilters] = useState<EventFilters>({});
  const { events, total, loading, error, refetch } = useEvents(filters);
  const { connected } = useEventStream();
  const intelligence = useIntelligence();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold">Event Dashboard</h2>
          <p className="text-sm text-gray-400 mt-0.5">
            Live intelligence feed for global events
          </p>
        </div>
        <EventFilterBar filters={filters} onChange={setFilters} />
      </div>

      <StatsBar events={events} total={total} connected={connected} />

      <section className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-gray-800 bg-gray-950/50 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">
            Global Pulse
          </h3>
          {intelligence.loading ? (
            <LoadingSpinner text="Loading pulse..." />
          ) : (
            <PulsePanel items={intelligence.pulse} />
          )}
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-950/50 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-500/80 mb-3">
            Breaking Stories
          </h3>
          {intelligence.loading ? (
            <LoadingSpinner text="Scanning..." />
          ) : (
            <BreakingStoriesPanel items={intelligence.breaking} />
          )}
        </div>

        <div className="rounded-xl border border-gray-800 bg-gray-950/50 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">
            Entity Explorer
          </h3>
          {intelligence.loading ? (
            <LoadingSpinner text="Loading entities..." />
          ) : (
            <EntityExplorer
              entities={intelligence.entities}
              detail={intelligence.entityDetail}
              onSelect={intelligence.exploreEntity}
              onClear={intelligence.clearEntity}
            />
          )}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <section>
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Events ({total})
            </h3>

            {loading && <LoadingSpinner text="Loading events..." />}
            {error && <ErrorState message={error} onRetry={refetch} />}
            {!loading && !error && events.length === 0 && (
              <EmptyState message="No events match your filters." />
            )}
            {!loading && !error && events.length > 0 && (
              <div className="grid gap-3 sm:grid-cols-2">
                {events.map((event) => (
                  <EventCard key={event.id} event={event} />
                ))}
              </div>
            )}
          </section>
        </div>

        <aside className="space-y-4">
          <section className="rounded-xl border border-gray-800 bg-gray-950/50 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">
              Narrative Map
            </h3>
            <NarrativeMapPanel map={intelligence.narrativeMap} />
          </section>
          <SentimentSnapshot events={events} />
          <GeoPanel events={events} />
        </aside>
      </div>
    </div>
  );
}
