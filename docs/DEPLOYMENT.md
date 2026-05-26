# Deployment

Detailed execution plan: see `docs/IMPLEMENTATION_PLAN.md`.

## Architecture on Vercel

Both CivicPulse services deploy to Vercel as separate projects:

| Project | Root directory | Production URL |
|---------|----------------|----------------|
| **web** | `apps/web` | https://web-levroncs-projects.vercel.app (or your alias) |
| **civicpulse-api** | `apps/api` | https://civicpulse-api.vercel.app |

The dashboard proxies `/api/*` → `API_URL` (set to the API project URL).

```
Browser → web (Vercel) → /api proxy → civicpulse-api (Vercel) → PostgreSQL (Neon)
```

**Important:** The API uses `EMBEDDING_MODEL=heuristic` on Vercel (ML deps exceed serverless limits). Connect **Neon Postgres** via Vercel Marketplace and set `DATABASE_URL` on the `civicpulse-api` project.

## Deploy dashboard to Vercel

### Option A — Git integration (recommended)

1. Push this repo to GitHub.
2. Import the repo at [vercel.com/new](https://vercel.com/new).
3. Set **Root Directory** to `apps/web`.
4. Add environment variables:

| Variable | Environment | Required | Example |
|----------|-------------|----------|---------|
| `API_URL` | Production, Preview | Yes | `https://your-api.railway.app` |
| `API_KEY` | Production, Preview | If API requires key | your-secret-key |
| `NEXT_PUBLIC_API_URL` | — | No | Leave empty to use `/api` proxy |

5. Deploy. Vercel runs `npm run build` inside `apps/web`.

### Option B — Vercel CLI

```bash
npm i -g vercel
cd apps/web
vercel link          # first time only
vercel env add API_URL
vercel env add API_KEY
vercel               # preview
vercel --prod        # production
```

## Deploy API (required for live data)

The FastAPI backend is **not** deployed to Vercel (ML embeddings, SSE, long-running enrich jobs).

### Minimal API deploy (Railway example)

1. Create a Railway project with **PostgreSQL**.
2. Deploy `apps/api` as a Python service:
   - Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Root directory: `apps/api`
3. Set environment variables from `.env.example` (use `DATABASE_URL` from Railway Postgres).
4. For faster cold starts on small hosts, set `EMBEDDING_MODEL=heuristic`.
5. Copy the public API URL into Vercel as `API_URL`.

### CORS

When using the `/api` proxy (recommended), the browser never calls the API directly — CORS is not required for the dashboard.

If you set `NEXT_PUBLIC_API_URL` to the API host instead, add your Vercel domain to `CORS_ORIGINS` on the API.

## Local development

- Use `docker-compose.yml` for Postgres, Redis, and MinIO.
- Start API with Uvicorn and web with Next.js (see README).
- Web proxy defaults to `http://localhost:8000` via `API_URL`.

## Production hardening

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
