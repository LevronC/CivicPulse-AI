# CivicPulse AI

Real-time global event intelligence platform that ingests news streams, enriches them with NLP, clusters emerging stories into canonical events, and serves a dashboard for analysts.

## Tech stack
- Backend: FastAPI (Python)
- Worker: Python queue loop (retry + DLQ simulation)
- Frontend: Next.js
- Data infra: PostgreSQL + Redis + MinIO (local Docker)

## Quickstart
1. Copy `.env.example` to `.env`.
2. Start infrastructure:
   - `docker compose up -d`
3. Run API:
   - `cd apps/api && pip install -r requirements.txt`
   - `uvicorn main:app --reload`
4. Run worker:
   - `cd apps/workers && python worker.py`
5. Run web:
   - `cd apps/web && npm install && npm run dev`

## API sequence (first run)
- `POST /ingest` with header `x-api-key: dev-api-key`
- `POST /enrich`
- `POST /events/rebuild`
- `GET /events`

## Included capabilities
- Source ingestion + de-duplication
- Summarization, topic classification, sentiment, entity extraction, embeddings (baseline heuristics)
- Event clustering and impact scoring
- Event feed/detail endpoints
- SSE + WebSocket realtime endpoints
- Public endpoint rate limiting + API key protection on mutating routes

## Portfolio metrics to track
- Articles ingested/day
- Enrichment latency per article
- Event detection latency
- API p95 for event feed/detail
- Cost per 1,000 enriched articles
