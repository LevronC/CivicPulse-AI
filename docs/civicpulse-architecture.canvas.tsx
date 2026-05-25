import {
  Button,
  CollapsibleSection,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  computeDAGLayout,
  useCanvasState,
  useHostTheme,
} from "cursor/canvas";

type DiagramSpec = {
  id: string;
  title: string;
  caption: string;
  nodes: Array<{ id: string }>;
  edges: Array<{ from: string; to: string }>;
  labels: Record<string, string>;
  direction?: "vertical" | "horizontal";
  nodeWidth?: number;
  nodeHeight?: number;
};

const PIPELINE: DiagramSpec = {
  id: "pipeline",
  title: "End-to-end data pipeline",
  caption: "Source: RSS / NewsAPI / GDELT · GRAPH_MODE=true · May 23 ship",
  nodes: [
    { id: "sources" },
    { id: "ingest" },
    { id: "dedupe" },
    { id: "articles" },
    { id: "enrich" },
    { id: "nlp" },
    { id: "graph" },
    { id: "lifecycle" },
    { id: "graphdb" },
    { id: "projector" },
    { id: "events" },
    { id: "api" },
    { id: "ui" },
    { id: "sse" },
  ],
  edges: [
    { from: "sources", to: "ingest" },
    { from: "ingest", to: "dedupe" },
    { from: "dedupe", to: "articles" },
    { from: "articles", to: "enrich" },
    { from: "enrich", to: "nlp" },
    { from: "nlp", to: "graph" },
    { from: "graph", to: "lifecycle" },
    { from: "lifecycle", to: "graphdb" },
    { from: "graphdb", to: "projector" },
    { from: "projector", to: "events" },
    { from: "events", to: "api" },
    { from: "api", to: "ui" },
    { from: "api", to: "sse" },
    { from: "sse", to: "ui" },
  ],
  labels: {
    sources: "RSS · NewsAPI · GDELT",
    ingest: "POST /ingest",
    dedupe: "URL dedupe",
    articles: "PostgreSQL articles",
    enrich: "POST /enrich",
    nlp: "NLP pipeline",
    graph: "EventGraphService",
    lifecycle: "Lifecycle engine",
    graphdb: "Graph tables + links",
    projector: "EventProjector",
    events: "events projection",
    api: "REST APIs",
    ui: "Next.js dashboard",
    sse: "GET /events/stream",
  },
};

const ENRICHMENT: DiagramSpec = {
  id: "enrichment",
  title: "NLP enrichment stages",
  caption: "Per article · EMBEDDING_MODEL=all-MiniLM-L6-v2 (384-dim) or heuristic fallback",
  direction: "horizontal",
  nodeWidth: 118,
  nodeHeight: 40,
  nodes: [
    { id: "raw" },
    { id: "summary" },
    { id: "topic" },
    { id: "sentiment" },
    { id: "entities" },
    { id: "embed" },
    { id: "done" },
  ],
  edges: [
    { from: "raw", to: "summary" },
    { from: "summary", to: "topic" },
    { from: "topic", to: "sentiment" },
    { from: "sentiment", to: "entities" },
    { from: "entities", to: "embed" },
    { from: "embed", to: "done" },
  ],
  labels: {
    raw: "ArticleRecord",
    summary: "Summarize",
    topic: "Classify topic",
    sentiment: "Sentiment",
    entities: "Extract entities",
    embed: "Embedding",
    done: "ArticleEnriched",
  },
};

const LIFECYCLE: DiagramSpec = {
  id: "lifecycle",
  title: "Event graph lifecycle mutations",
  caption: "Thresholds: attach 0.40 · merge 0.72 · stale 72h",
  nodes: [
    { id: "article" },
    { id: "match" },
    { id: "create" },
    { id: "attach" },
    { id: "merge" },
    { id: "split" },
    { id: "decay" },
    { id: "active" },
    { id: "stale" },
    { id: "archived" },
  ],
  edges: [
    { from: "article", to: "match" },
    { from: "match", to: "create" },
    { from: "match", to: "attach" },
    { from: "attach", to: "active" },
    { from: "create", to: "active" },
    { from: "active", to: "merge" },
    { from: "active", to: "split" },
    { from: "active", to: "decay" },
    { from: "decay", to: "stale" },
    { from: "stale", to: "archived" },
    { from: "merge", to: "active" },
    { from: "split", to: "active" },
  ],
  labels: {
    article: "Enriched article",
    match: "Similarity match",
    create: "CREATE event",
    attach: "ATTACH article",
    merge: "MERGE events",
    split: "SPLIT event",
    decay: "DECAY check",
    active: "active",
    stale: "stale",
    archived: "archived",
  },
};

const INTELLIGENCE: DiagramSpec = {
  id: "intelligence",
  title: "Intelligence layer pathways",
  caption: "P2 ranking + P3 product unlock · reads graph, writes related_to edges",
  nodes: [
    { id: "graph" },
    { id: "centrality" },
    { id: "velocity" },
    { id: "ranking" },
    { id: "pulse" },
    { id: "breaking" },
    { id: "similarity" },
    { id: "edges" },
    { id: "narrative" },
    { id: "entities" },
    { id: "explorer" },
  ],
  edges: [
    { from: "graph", to: "centrality" },
    { from: "graph", to: "velocity" },
    { from: "centrality", to: "ranking" },
    { from: "velocity", to: "ranking" },
    { from: "ranking", to: "pulse" },
    { from: "velocity", to: "breaking" },
    { from: "graph", to: "breaking" },
    { from: "graph", to: "similarity" },
    { from: "similarity", to: "edges" },
    { from: "edges", to: "narrative" },
    { from: "graph", to: "entities" },
    { from: "entities", to: "explorer" },
  ],
  labels: {
    graph: "Event graph",
    centrality: "Entity centrality",
    velocity: "Article velocity",
    ranking: "EventRankingEngine",
    pulse: "GET /pulse",
    breaking: "GET /breaking",
    similarity: "SimilarityEdgeService",
    edges: "related_to edges",
    narrative: "GET /narrative-map",
    entities: "Entity index",
    explorer: "GET /entities",
  },
};

const SCHEMA: DiagramSpec = {
  id: "schema",
  title: "PostgreSQL graph schema (v3)",
  caption: "Graph = source of truth · events table = read projection",
  direction: "horizontal",
  nodeWidth: 130,
  nodeHeight: 36,
  nodes: [
    { id: "articles" },
    { id: "links" },
    { id: "events_g" },
    { id: "entities" },
    { id: "rels" },
    { id: "snapshots" },
    { id: "events_p" },
  ],
  edges: [
    { from: "articles", to: "links" },
    { from: "links", to: "events_g" },
    { from: "events_g", to: "entities" },
    { from: "events_g", to: "rels" },
    { from: "events_g", to: "snapshots" },
    { from: "events_g", to: "events_p" },
  ],
  labels: {
    articles: "articles",
    links: "article_event_links",
    events_g: "events (graph cols)",
    entities: "entities",
    rels: "event_relationships",
    snapshots: "event_snapshots",
    events_p: "events projection",
  },
};

const DIAGRAMS = [PIPELINE, ENRICHMENT, LIFECYCLE, INTELLIGENCE, SCHEMA];

function FlowDiagram({ spec }: { spec: DiagramSpec }) {
  const theme = useHostTheme();
  const layout = computeDAGLayout({
    nodes: spec.nodes,
    edges: spec.edges,
    direction: spec.direction ?? "vertical",
    nodeWidth: spec.nodeWidth ?? 148,
    nodeHeight: spec.nodeHeight ?? 38,
    rankGap: 52,
    nodeGap: 28,
    padding: 20,
  });

  const nw = spec.nodeWidth ?? 148;
  const nh = spec.nodeHeight ?? 38;

  return (
    <Stack gap={8}>
      <div style={{ overflowX: "auto", width: "100%" }}>
        <svg
          width={layout.width}
          height={layout.height}
          viewBox={`0 0 ${layout.width} ${layout.height}`}
          role="img"
          aria-label={spec.title}
        >
          <defs>
            <marker
              id={`arrow-${spec.id}`}
              markerWidth="8"
              markerHeight="8"
              refX="7"
              refY="3"
              orient="auto"
            >
              <path d="M0,0 L0,6 L7,3 z" fill={theme.stroke.secondary} />
            </marker>
          </defs>
          {layout.edges.map((edge) => (
            <line
              key={`${edge.from}-${edge.to}`}
              x1={edge.sourceX}
              y1={edge.sourceY}
              x2={edge.targetX}
              y2={edge.targetY}
              stroke={edge.isBackEdge ? theme.stroke.tertiary : theme.stroke.secondary}
              strokeWidth={1.5}
              strokeDasharray={edge.isBackEdge ? "4 3" : undefined}
              markerEnd={`url(#arrow-${spec.id})`}
            />
          ))}
          {layout.nodes.map((node) => {
            const label = spec.labels[node.id] ?? node.id;
            const accent =
              node.id === "graph" ||
              node.id === "lifecycle" ||
              node.id === "ranking" ||
              node.id === "pulse";
            return (
              <g key={node.id}>
                <rect
                  x={node.x}
                  y={node.y}
                  width={nw}
                  height={nh}
                  rx={5}
                  fill={accent ? theme.fill.secondary : theme.fill.tertiary}
                  stroke={accent ? theme.accent.primary : theme.stroke.primary}
                  strokeWidth={accent ? 1.5 : 1}
                />
                <text
                  x={node.x + nw / 2}
                  y={node.y + nh / 2 + 4}
                  textAnchor="middle"
                  fill={theme.text.primary}
                  fontSize={11}
                  fontFamily="ui-monospace, monospace"
                >
                  {label.length > 22 ? `${label.slice(0, 20)}…` : label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <Text tone="secondary" size="small">
        {spec.caption}
      </Text>
    </Stack>
  );
}

const API_ROWS: string[][] = [
  ["POST /ingest", "Fetch + dedupe articles", "API key"],
  ["POST /enrich", "Run NLP on pending articles", "API key"],
  ["POST /events/rebuild", "Graph sync + projection", "API key"],
  ["GET /events", "Paginated event feed", "Public"],
  ["GET /events/{id}", "Event + linked articles", "Public"],
  ["GET /events/stream", "SSE live updates", "Public"],
  ["GET /intelligence/pulse", "Ranked global pulse", "Public"],
  ["GET /intelligence/breaking", "Accelerating stories", "Public"],
  ["GET /intelligence/narrative-map", "Event nodes + edges", "Public"],
  ["GET /intelligence/entities", "Top entities", "Public"],
  ["GET /intelligence/entities/{name}", "Entity drill-down", "Public"],
  ["POST /intelligence/strengthen-edges", "Rebuild similarity graph", "API key"],
  ["POST /intelligence/sync", "Process unlinked articles", "API key"],
];

const RANKING_ROWS: string[][] = [
  ["Impact score", "25%", "Article volume + source diversity"],
  ["Velocity score", "30%", "Non-linear article arrival rate"],
  ["Recency", "20%", "Hours since last update"],
  ["Entity centrality", "15%", "Connection density in entity graph"],
  ["Source diversity", "10%", "Distinct outlets covering event"],
];

const UI_ROWS: string[][] = [
  ["Global Pulse", "/intelligence/pulse", "Ranked events with velocity + centrality"],
  ["Breaking Stories", "/intelligence/breaking", "Accelerating / new narratives"],
  ["Entity Explorer", "/intelligence/entities", "Click entity → linked events"],
  ["Narrative Map", "/intelligence/narrative-map", "related_to edge list"],
  ["Event Feed", "/events", "Filterable card grid"],
  ["Live stream", "/events/stream", "SSE connection indicator"],
];

export default function CivicPulseArchitecture() {
  const [active, setActive] = useCanvasState<string>("diagram", "pipeline");
  const spec = DIAGRAMS.find((d) => d.id === active) ?? PIPELINE;

  return (
    <Stack gap={24}>
      <Stack gap={6}>
        <H1>CivicPulse AI — Architecture</H1>
        <Text tone="secondary">
          Visual map of pipelines, graph mutations, intelligence pathways, and API
          surface shipped May 23, 2026.
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value="58" label="Articles (demo run)" />
        <Stat value="50" label="Graph-linked events" />
        <Stat value="105" label="Unit tests" />
        <Stat value="13" label="Intelligence + core routes" tone="success" />
      </Grid>

      <Divider />

      <Stack gap={10}>
        <H2>System diagrams</H2>
        <Row gap={8} wrap>
          {DIAGRAMS.map((d) => (
            <Button
              key={d.id}
              variant={active === d.id ? "primary" : "secondary"}
              onClick={() => setActive(d.id)}
            >
              {d.title.split(" ")[0]}
            </Button>
          ))}
        </Row>
        <H3>{spec.title}</H3>
        <FlowDiagram spec={spec} />
      </Stack>

      <Divider />

      <CollapsibleSection
        title="Pulse ranking formula"
        subtitle="EventRankingEngine.score_event()"
        defaultOpen
      >
        <Table headers={["Signal", "Weight", "Source"]} rows={RANKING_ROWS} />
      </CollapsibleSection>

      <CollapsibleSection title="API routes" subtitle="FastAPI · apps/api/src/routes/">
        <Table headers={["Route", "Purpose", "Auth"]} rows={API_ROWS} />
      </CollapsibleSection>

      <CollapsibleSection title="Dashboard panels" subtitle="Next.js · apps/web/">
        <Table headers={["Panel", "API", "Behavior"]} rows={UI_ROWS} />
      </CollapsibleSection>

      <Divider />

      <Stack gap={8}>
        <H2>Mutation → projection loop</H2>
        <Row gap={8} wrap>
          <Pill tone="info">create</Pill>
          <Pill tone="info">attach</Pill>
          <Pill tone="info">merge</Pill>
          <Pill tone="info">split</Pill>
          <Pill tone="warning">decay</Pill>
          <Text tone="secondary" size="small">
            → article_event_links + event_relationships → EventProjector.reconcile() →
            events table → /events + /intelligence/*
          </Text>
        </Row>
        <Text tone="secondary" size="small">
          Enrichment auto-triggers graph mutations when GRAPH_MODE=true. Batch rebuild
          delegates to /intelligence/sync + projection.
        </Text>
      </Stack>
    </Stack>
  );
}
