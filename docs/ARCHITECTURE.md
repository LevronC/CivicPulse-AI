# Architecture

Detailed execution plan: see `docs/IMPLEMENTATION_PLAN.md`.

## Data flow
1. Ingestion workers fetch source articles.
2. API de-duplicates and stores normalized article records.
3. NLP pipeline enriches each article with summary/topic/sentiment/entities/embedding.
4. Event builder clusters related articles and computes impact score.
5. Frontend consumes `/events` and subscribes to SSE/WebSocket updates.

## Components
- `apps/api`: ingest/enrich/event APIs and realtime streams.
- `apps/workers`: queue-like orchestration with retry and DLQ behavior.
- `apps/web`: Next.js dashboard views (map-like coordinate panel, feed, sentiment).
- `packages/shared`: cross-service schema contract.
- `infra`: SQL schema and local infrastructure definitions.

## Event model
- Event lifecycle in this baseline is rebuild-oriented.
- Cluster merge/split behavior can be evolved by adding historical cluster linking and temporal overlap scoring.
- Impact score currently combines volume, source diversity, and negative signal weighting.

## Implementation checkpoints
- **Contract-first gate**: all services use `packages/shared` event/article contracts before feature wiring.
- **Pipeline gate**: ingestion + enrichment flow completes with retries, DLQ, and metrics before API scale tests.
- **Intelligence gate**: clustering and impact scoring calibrated on a fixed evaluation dataset.
- **Delivery gate**: `/events` REST + SSE/WebSocket stream provide cursor-based continuity.
- **Hardening gate**: auth, tracing, synthetic checks, canary, and rollback procedure validated.
