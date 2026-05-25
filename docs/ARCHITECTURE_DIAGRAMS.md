# CivicPulse AI — Architecture Diagrams

Visual reference for pipelines, graph mutations, intelligence pathways, and API surface.

For an interactive tabbed view in Cursor, open [`civicpulse-architecture.canvas.tsx`](civicpulse-architecture.canvas.tsx) as a Canvas beside the chat.

## End-to-end data pipeline

```mermaid
flowchart TB
  subgraph sources [Sources]
    RSS[RSS feeds]
    NewsAPI[NewsAPI]
    GDELT[GDELT]
  end

  subgraph ingest [Ingestion]
    POST_INGEST["POST /ingest"]
    Dedupe[URL dedupe]
    Articles[(articles)]
  end

  subgraph enrich [Enrichment]
    POST_ENRICH["POST /enrich"]
    NLP[NLP pipeline]
    Enriched[ArticleEnriched]
  end

  subgraph graph [Living event graph]
    EGS[EventGraphService]
    Life[LifecycleEngine]
    GraphDB[(graph tables + links)]
    Proj[EventProjector]
    Events[(events projection)]
  end

  subgraph delivery [Delivery]
    API[REST APIs]
    Intel["/intelligence/*"]
    SSE["/events/stream"]
    Web[Next.js dashboard]
  end

  RSS --> POST_INGEST
  NewsAPI --> POST_INGEST
  GDELT --> POST_INGEST
  POST_INGEST --> Dedupe --> Articles
  Articles --> POST_ENRICH --> NLP --> Enriched
  Enriched --> EGS --> Life --> GraphDB
  GraphDB --> Proj --> Events
  Events --> API
  GraphDB --> Intel
  API --> Web
  Intel --> Web
  SSE --> Web
```

## NLP enrichment stages

Per article: summarize → classify topic → sentiment → extract entities → embed (`all-MiniLM-L6-v2`, 384-dim).

```mermaid
flowchart LR
  Raw[ArticleRecord] --> Sum[Summarize]
  Sum --> Topic[Classify topic]
  Topic --> Sent[Sentiment]
  Sent --> Ent[Extract entities]
  Ent --> Emb[Embedding]
  Emb --> Done[ArticleEnriched]
```

## Event graph lifecycle

Thresholds: attach **0.40** · merge **0.72** · stale **72h**

```mermaid
flowchart TD
  A[Enriched article arrives] --> B{Best match score?}
  B -->|below 0.40| C[CREATE new event]
  B -->|≥ 0.40| D[ATTACH to event]
  D --> E[Update centroid + entities]
  C --> E
  E --> F{Merge candidate ≥ 0.72?}
  F -->|yes| G[MERGE events]
  F -->|no| H{Split variance high?}
  H -->|yes| I[SPLIT event]
  G --> J[active]
  I --> J
  H -->|no| J
  J --> K{Inactive 72h+?}
  K -->|yes| L[stale → archived]
```

Mutations write to `article_event_links` and `event_relationships`. `EventProjector.reconcile()` materializes the read-optimized `events` table.

## Intelligence layer

```mermaid
flowchart LR
  G[Event graph] --> C[Entity centrality]
  G --> V[Velocity]
  C --> R[EventRankingEngine]
  V --> R
  R --> P["GET /pulse"]
  V --> B["GET /breaking"]
  G --> S[SimilarityEdgeService]
  S --> E[related_to edges]
  E --> N["GET /narrative-map"]
  G --> ENT[Entity index]
  ENT --> X["GET /entities"]
```

### Pulse ranking weights

| Signal | Weight | Source |
|--------|--------|--------|
| Impact score | 25% | Article volume + source diversity |
| Velocity score | 30% | Non-linear article arrival rate |
| Recency | 20% | Hours since last update |
| Entity centrality | 15% | Connection density in entity graph |
| Source diversity | 10% | Distinct outlets covering event |

## PostgreSQL graph schema (v3)

Graph is source of truth; `events` table is the SQL projection.

```mermaid
flowchart LR
  articles[(articles)] --> links[article_event_links]
  links --> events_g[events graph cols]
  events_g --> entities[(entities)]
  events_g --> rels[event_relationships]
  events_g --> snaps[event_snapshots]
  events_g --> events_p[events projection]
```

## API routes

| Route | Purpose | Auth |
|-------|---------|------|
| `POST /ingest` | Fetch + dedupe articles | API key |
| `POST /enrich` | Run NLP on pending articles | API key |
| `POST /events/rebuild` | Graph sync + projection | API key |
| `GET /events` | Paginated event feed | Public |
| `GET /events/{id}` | Event + linked articles | Public |
| `GET /events/stream` | SSE live updates | Public |
| `GET /intelligence/pulse` | Ranked global pulse | Public |
| `GET /intelligence/breaking` | Accelerating stories | Public |
| `GET /intelligence/narrative-map` | Event nodes + edges | Public |
| `GET /intelligence/entities` | Top entities | Public |
| `GET /intelligence/entities/{name}` | Entity drill-down | Public |
| `POST /intelligence/strengthen-edges` | Rebuild similarity graph | API key |
| `POST /intelligence/sync` | Process unlinked articles | API key |

## Dashboard panels

| Panel | API | Behavior |
|-------|-----|----------|
| Global Pulse | `/intelligence/pulse` | Ranked events with velocity + centrality |
| Breaking Stories | `/intelligence/breaking` | Accelerating / new narratives |
| Entity Explorer | `/intelligence/entities` | Click entity → linked events |
| Narrative Map | `/intelligence/narrative-map` | `related_to` edge list |
| Event Feed | `/events` | Filterable card grid |
| Live stream | `/events/stream` | SSE connection indicator |
