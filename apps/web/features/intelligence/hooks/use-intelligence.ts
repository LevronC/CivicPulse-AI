"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "../../../lib/api-client";
import type {
  BreakingStoryItem,
  EntityIntelligenceResponse,
  GlobalPulseItem,
  NarrativeMapResponse,
  TopEntityItem,
} from "../../../lib/types";

export function useIntelligence() {
  const [pulse, setPulse] = useState<GlobalPulseItem[]>([]);
  const [breaking, setBreaking] = useState<BreakingStoryItem[]>([]);
  const [entities, setEntities] = useState<TopEntityItem[]>([]);
  const [narrativeMap, setNarrativeMap] = useState<NarrativeMapResponse | null>(null);
  const [entityDetail, setEntityDetail] = useState<EntityIntelligenceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [pulseRes, breakingRes, entitiesRes, mapRes] = await Promise.all([
        api.intelligence.pulse(8),
        api.intelligence.breaking(6),
        api.intelligence.topEntities(10),
        api.intelligence.narrativeMap(25),
      ]);
      setPulse(pulseRes.items);
      setBreaking(breakingRes.items);
      setEntities(entitiesRes.items);
      setNarrativeMap(mapRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load intelligence");
    } finally {
      setLoading(false);
    }
  }, []);

  const exploreEntity = useCallback(async (name: string) => {
    try {
      const detail = await api.intelligence.entity(name);
      setEntityDetail(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Entity not found");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return {
    pulse,
    breaking,
    entities,
    narrativeMap,
    entityDetail,
    loading,
    error,
    refetch: load,
    exploreEntity,
    clearEntity: () => setEntityDetail(null),
  };
}
