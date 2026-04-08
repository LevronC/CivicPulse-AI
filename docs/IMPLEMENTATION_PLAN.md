# CivicPulse AI Implementation Plan

## 1) Objective
Deliver a production-ready real-time event intelligence platform that ingests global news, enriches content with NLP, clusters stories into canonical events, and serves low-latency event streams to a web dashboard.

## 2) Scope
### In scope
- Multi-source ingestion and normalization pipeline.
- NLP enrichment (summary, topic, sentiment, entities, embeddings).
- Event clustering and impact scoring engine.
- API + realtime delivery (REST + SSE/WebSocket).
- Web dashboard with event feed, filters, and detail views.
- CI/CD, observability, auth baseline, and operational runbooks.

### Out of scope (initial release)
- Advanced historical cluster lineage graph.
- Multi-tenant organization/workspace model.
- Human-in-the-loop annotation tooling.
- Full incident command automation.

## 3) Success Criteria (Release Gate)
- P95 `/events` API latency <= 400 ms under expected load.
- Ingestion freshness: median source-to-API availability <= 3 minutes.
- Enrichment success rate >= 99% excluding upstream provider outages.
- Event cluster precision/recall baseline agreed and tracked weekly.
- Dashboard uptime target >= 99.5% monthly.
- Mean time to detection (MTTD) <= 5 minutes via synthetic checks + alerts.

## 4) Architecture Execution Order
1. Build deterministic contracts first (`packages/shared`) to prevent schema drift.
2. Stand up data plane (`infra` + `apps/api` persistence contracts).
3. Implement ingestion and idempotency controls.
4. Add enrichment workers with retry, backoff, and DLQ.
5. Implement event builder and scoring logic.
6. Expose API + realtime streams.
7. Integrate web dashboard and UX states.
8. Harden production controls (auth, secrets, tracing, canary, rollback).

## 5) Detailed Workstreams
### A. Shared Contract and Data Model
### Deliverables
- Canonical `Article`, `EnrichedArticle`, `Event`, and `EventUpdate` schema.
- Strict validation for API IO and queue message payloads.
- Versioned schema migration policy.

### Tasks
- Define strongly typed schema package and serialization format.
- Add compatibility tests to prevent breaking downstream consumers.
- Define event lifecycle states (`draft`, `active`, `stale`, `archived`).
- Add migration templates for field evolution and deprecation windows.

### Acceptance criteria
- All services compile against shared types without local redefinition.
- Backward compatibility tests pass for at least one previous schema version.

### B. Ingestion Pipeline (`apps/workers` + `apps/api`)
### Deliverables
- Source connector framework with per-source adapters.
- Deduplication and idempotent ingest writes.
- Retry policy and dead-letter queue processing.

### Tasks
- Implement source polling schedule and fetch timeouts.
- Normalize source payloads to canonical article structure.
- Add dedupe key strategy (URL canonicalization + title hash + time window).
- Add idempotency key checks at storage boundary.
- Persist ingest metrics (fetched, accepted, deduped, failed).

### Acceptance criteria
- Duplicate submission rate <= 1% under replay tests.
- Worker can recover from transient source/API failures automatically.

### C. NLP Enrichment Pipeline
### Deliverables
- Enrichment orchestrator with stage-level status tracking.
- Stage outputs: summary, topic classification, sentiment, entities, embeddings.
- Fallback behavior for partial provider failures.

### Tasks
- Define stage contract: input/output/error envelope for each enrichment step.
- Implement queue-driven stage execution and retry with exponential backoff.
- Persist per-stage provenance metadata (model/provider/version/latency).
- Add quality checks (minimum summary length, entity count sanity, embedding dim).
- Add dead-letter replay CLI for failed enrichments.

### Acceptance criteria
- Stage-level telemetry available in logs/metrics dashboards.
- Partial enrichment still produces consumable records with explicit nullability.

### D. Event Builder and Impact Engine
### Deliverables
- Clustering algorithm producing canonical event groups.
- Impact score model combining volume, source diversity, and negative signal.
- Rebuild scheduler + incremental update mode.

### Tasks
- Start with embedding + temporal proximity clustering.
- Implement merge/split rules with deterministic tie-breakers.
- Build impact score function and calibration dataset.
- Add event confidence and rationale fields for explainability.
- Emit event update notifications when material changes occur.

### Acceptance criteria
- Cluster outputs remain stable across repeated runs on same input.
- Score distribution sanity checks pass (no saturation at extremes).

### E. API and Realtime Delivery (`apps/api`)
### Deliverables
- REST endpoints for events, filters, detail, and health.
- SSE/WebSocket channel for near-real-time updates.
- API rate limiting and auth middleware.

### Tasks
- Implement `/events` query contract (pagination, filtering, sorting).
- Add response cache strategy for common read paths.
- Add stream fanout with reconnection cursor support.
- Add auth boundary for dashboard users (JWT-based baseline).
- Add request/response structured logging with correlation IDs.

### Acceptance criteria
- Reconnect clients can resume from cursor without full refresh.
- P95 latency and stream delivery SLOs pass load tests.

### F. Web Dashboard (`apps/web`)
### Deliverables
- Event feed, filtering, sentiment views, and event detail panel.
- Realtime UI updates with optimistic/consistent rendering strategy.
- Error/loading/empty states and accessibility baseline.

### Tasks
- Build API client with typed contracts from shared package.
- Implement event list virtualization for high-volume feeds.
- Wire filters and URL state synchronization.
- Integrate SSE/WebSocket subscription and fallback polling mode.
- Add UX observability: frontend errors, key page interaction timings.

### Acceptance criteria
- Dashboard remains responsive under high update frequency.
- All core views meet accessibility checks for keyboard and contrast baseline.

### G. Reliability, Security, and Operations
### Deliverables
- CI/CD with build, test, and migration gates.
- Tracing, metrics, alerts, and on-call runbook.
- Secrets management and key rotation procedures.

### Tasks
- Add pipeline checks: lint, unit, integration, contract, smoke tests.
- Define SLOs and alert thresholds for ingest/enrich/event/API.
- Add canary rollout workflow and rollback automation.
- Implement secret rotation checklist and environment segregation.
- Add synthetic checks for source ingest, enrichment flow, and API read path.

### Acceptance criteria
- On-call can diagnose and mitigate critical incidents via runbook in < 15 min.
- Canary promotes automatically only after health criteria pass.

## 6) Milestone Schedule (8 Weeks)
### Week 1-2: Foundation
- Finalize shared schema contracts and migration policy.
- Provision local infra and baseline SQL schema.
- Set up CI baseline and test harness skeleton.

### Week 3-4: Pipeline Core
- Implement ingestion connectors + dedupe + idempotency.
- Stand up enrichment orchestration with telemetry.
- Validate end-to-end article -> enriched article flow.

### Week 5-6: Event Intelligence + API
- Implement clustering + scoring and event update stream.
- Ship `/events` with filtering/pagination + health endpoints.
- Load-test API and optimize hot paths.

### Week 7: Frontend + Realtime
- Integrate dashboard with typed API contracts.
- Add realtime updates, fallback mode, and UX hardening.
- Run cross-browser and accessibility checks.

### Week 8: Production Hardening
- Complete auth, secrets, tracing, and alerting.
- Execute canary deploy, chaos-lite failure drills, rollback test.
- Final release review against all success criteria.

## 7) Dependency Map
- Shared schema must be stable before full API/web integration.
- Ingestion persistence must be in place before enrichment orchestration.
- Enrichment outputs are required before event clustering quality tuning.
- Event API contract must freeze before final frontend polish.
- Observability must be implemented before canary promotion.

## 8) Testing Strategy
### Unit
- Normalizers, dedupe logic, scoring components, serialization.

### Integration
- Worker -> DB -> enrichment -> event builder chain.
- API query correctness on seeded datasets.

### Contract
- Shared package schema snapshots and backward compatibility checks.

### Load and resilience
- Burst ingest tests, API concurrency tests, stream fanout tests.
- Failure injection: provider timeout, queue lag, partial DB outage.

### End-to-end
- Critical user flows: open dashboard, filter events, live update, view details.

## 9) Risk Register and Mitigation
- **Provider instability**: add fallback providers, circuit breaker, and DLQ replay.
- **Schema drift**: enforce shared package ownership and contract CI checks.
- **Hot partition/event storms**: backpressure controls and stream throttling.
- **Latency regression**: profile hot endpoints; cache + pagination enforcement.
- **Low clustering quality**: weekly evaluation dataset and threshold tuning loop.

## 10) Operational Runbooks (Minimum Set)
- Ingestion stalled: diagnose source health, queue lag, and worker throughput.
- Enrichment failures: inspect provider metrics, replay DLQ, validate credentials.
- Event stream lagging: inspect clustering runtime, queue depth, and API fanout.
- API latency spike: trace slow queries, cache miss ratio, connection pool health.
- Emergency rollback: execute canary rollback playbook and incident timeline capture.

## 11) Definition of Done
- All scoped deliverables complete with passing automated tests.
- SLO dashboards and alerts are live with verified signal quality.
- Runbooks are documented and exercised once in simulation.
- Security baseline (auth + secret handling + audit logging) is enforced.
- Stakeholder demo confirms core product workflow and reliability targets.
