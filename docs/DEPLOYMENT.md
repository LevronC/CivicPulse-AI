# Deployment

Detailed execution plan: see `docs/IMPLEMENTATION_PLAN.md`.

## Local development
- Use `docker-compose.yml` for Postgres, Redis, and MinIO.
- Start API with Uvicorn and web with Next.js.

## Production shape
- API + worker containerized and deployed separately.
- Queue can be upgraded from in-process deque to Redis streams/Kafka.
- Vector store can be upgraded from in-memory embeddings to Pinecone/Weaviate.
- Add managed PostgreSQL and object storage in cloud.

## Hardening checklist
- Rotate API keys and secrets via secret manager.
- Add JWT auth for dashboard users.
- Add structured logs and distributed tracing.
- Add canary deployment and rollback strategy.
- Add synthetic checks for ingest, enrich, and event pipeline health.

## Release readiness gates
- **Pre-deploy**: lint, unit, integration, and contract tests passing in CI.
- **Canary**: ingest freshness, enrichment success, and `/events` latency thresholds hold for canary window.
- **Promotion**: no critical alerts and synthetic checks remain green for full pipeline.
- **Post-deploy**: verify dashboards, stream continuity, and rollback path integrity.
