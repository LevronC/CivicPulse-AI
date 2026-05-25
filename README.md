# CivicPulse AI

Real-time global event intelligence platform. CivicPulse ingests news streams, enriches articles with NLP, builds a **living event graph** of emerging stories, and serves ranked intelligence to analysts through a Next.js dashboard.

```
RSS / NewsAPI / GDELT
        │
        ▼
   Ingest + dedupe ──► PostgreSQL (articles)
        │
        ▼
   NLP enrichment ───► summary · topic · sentiment · entities · embeddings
        │
        ▼
   Event graph ───────► create · attach · merge · split · decay
        │                    │
        ▼                    ▼
   SQL projection      related_to edges + entity graph
   (events table)              │
        │                      ▼
        └──────────► /events + /intelligence/* ──► Dashboard + SSE
```

## Features

### Ingestion & enrichment
- Multi-source adapters: **RSS**, **NewsAPI**, **GDELT**
- URL/content deduplication and normalized article storage
- Pluggable NLP pipeline: summarization, topic classification, sentiment, entity extraction
- Real embeddings via `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim) or heuristic fallbacks

### Living event graph
- Incremental graph mutations instead of batch-only rebuilds (`GRAPH_MODE=true`)
- Articles linked to canonical events through similarity, topic, and temporal signals
- Event lifecycle: draft → active → stale → archived → merged
- SQL projection keeps the `events` table read-optimized while the graph is the source of truth

### Intelligence layer
- **Global pulse** — ranked events weighted by velocity, recency, source diversity, and entity centrality
- **Breaking stories** — fast-growing or newly forming narratives
- **Entity explorer** — top entities and event clusters per entity
- **Narrative map** — cross-event `related_to` edges for story connection discovery
- Similarity edge strengthener to densify the event graph over time

### Dashboard & realtime
- Next.js dashboard: event feed, pulse, breaking stories, entity explorer, narrative map, sentiment/geo panels
- SSE event stream for live updates
- API key auth on mutating routes, rate limiting on public reads

## Tech stack

| Layer | Stack |
|-------|-------|
| API | FastAPI, SQLAlchemy, Pydantic |
| NLP | sentence-transformers, heuristic model backends |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Data | PostgreSQL, Redis, MinIO (local via Docker) |
| Worker | Python task queue loop (retry + DLQ) |
| CI | GitHub Actions — pytest, lint, Next.js build |

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose

## Quickstart

### 1. Clone and configure

```bash
git clone https://github.com/LevronC/CivicPulse-AI.git
cd CivicPulse-AI

cp .env.example .env
scripts/setup-git-hooks.sh   # optional: enforce human-only commit attribution
```

### 2. Start infrastructure

```bash
docker compose up -d
```

Starts PostgreSQL, Redis, and MinIO.

### 3. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt

cd apps/web && npm install && cd ../..
```

### 4. Run services

Use **separate terminals**:

```bash
# Terminal 1 — API
source .venv/bin/activate
cd apps/api
uvicorn main:app --reload
```

```bash
# Terminal 2 — Web dashboard
cd apps/web
npm run dev
```

```bash
# Terminal 3 — Worker (optional)
source .venv/bin/activate
cd apps/workers
python worker.py
```

Open **http://localhost:3000** (dashboard) · API docs at **http://localhost:8000/docs**

### 5. Run the pipeline (first time)

All mutating requests require `x-api-key: dev-api-key` (see `.env.example`).

```bash
curl -X POST http://localhost:8000/ingest  -H 'x-api-key: dev-api-key'
curl -X POST http://localhost:8000/enrich  -H 'x-api-key: dev-api-key'
curl -X POST http://localhost:8000/events/rebuild -H 'x-api-key: dev-api-key'
```

Re-runs are idempotent — already-ingested articles are deduplicated and already-enriched articles are skipped.

Optional: strengthen cross-event similarity edges after bulk ingest:

```bash
curl -X POST http://localhost:8000/intelligence/strengthen-edges -H 'x-api-key: dev-api-key'
```

## API reference

### Core

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | — | Service and database health |
| `POST` | `/ingest` | key | Fetch articles from configured sources |
| `POST` | `/enrich` | key | Run NLP pipeline on pending articles |
| `POST` | `/events/rebuild` | key | Graph sync + SQL projection (when `GRAPH_MODE=true`) |
| `GET` | `/events` | — | Paginated event feed with filters |
| `GET` | `/events/{id}` | — | Event detail with linked articles |
| `GET` | `/events/stream` | — | SSE stream of graph/event updates |

### Intelligence

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/intelligence/pulse` | — | Ranked global event pulse |
| `GET` | `/intelligence/breaking` | — | Breaking / accelerating stories |
| `GET` | `/intelligence/emerging` | — | Alias for breaking stories |
| `GET` | `/intelligence/entities` | — | Top entities by event coverage |
| `GET` | `/intelligence/entities/{name}` | — | Events and articles for one entity |
| `GET` | `/intelligence/narrative-map` | — | Event nodes + related_to edges |
| `GET` | `/intelligence/events/{id}/evolution` | — | Event snapshot timeline |
| `POST` | `/intelligence/sync` | key | Process unlinked articles into graph |
| `POST` | `/intelligence/strengthen-edges` | key | Recompute similarity edges |

## Configuration

Key environment variables (full list in `.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `SOURCE_PROVIDERS` | `["rss"]` | Ingestion sources: `rss`, `newsapi`, `gdelt` |
| `RSS_FEEDS` | NYT World | RSS feed URLs |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Embedding backend (`heuristic` for no ML deps) |
| `GRAPH_MODE` | `true` | Use living event graph as source of truth |
| `GRAPH_ATTACH_THRESHOLD` | `0.40` | Min similarity to attach article to event |
| `GRAPH_MERGE_THRESHOLD` | `0.72` | Min similarity to merge events |
| `API_KEY` | `dev-api-key` | Key for protected routes |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API base URL for the web app |

## Project structure

```
apps/
  api/          FastAPI service — ingest, enrich, events, intelligence, SSE
  web/          Next.js dashboard and intelligence UI
  workers/      Background task worker
infra/
  schema.sql              Base PostgreSQL schema
  migrations/             Incremental migrations (event graph v3)
packages/shared/          Cross-service TypeScript + JSON schemas
tests/                    pytest unit tests (105+)
docs/                     Architecture, deployment, implementation plan
```

## Development

### Run tests

```bash
source .venv/bin/activate
pytest tests/ -q
```

### Lint & build (matches CI)

```bash
cd apps/web && npm run lint && npm run build
```

### Apply database migrations

After starting Docker, apply graph schema additions:

```bash
docker compose exec postgres psql -U civicpulse -d civicpulse -f /path/to/infra/migrations/v3_event_graph.sql
```

Or run the SQL file against your local Postgres instance directly.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — data flow and component boundaries
- [Architecture diagrams](docs/ARCHITECTURE_DIAGRAMS.md) — mermaid pipeline, graph, and intelligence pathways
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md) — phased delivery checklist
- [Deployment](docs/DEPLOYMENT.md) — production deployment notes

## License

Private / portfolio project. See repository owner for usage terms.
