from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from os import getenv
from typing import Any, AsyncIterator

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket
from fastapi.responses import StreamingResponse

from services.events import cluster_articles, to_event
from services.ingestion import dedupe_articles, mock_news_batch
from services.nlp import enrich_article

load_dotenv()
app = FastAPI(title="CivicPulse API", version="0.1.0")

STATE: dict[str, Any] = {
    "articles": {},
    "enriched": {},
    "events": {},
    "event_updates": deque(maxlen=500),
}
RATE_LIMIT_BUCKETS: dict[str, list[datetime]] = defaultdict(list)
MAX_REQ_PER_MIN = 60


def require_api_key(x_api_key: str = Header(default="")) -> None:
    expected = getenv("API_KEY", "dev-api-key")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")


def rate_limit(client: str) -> None:
    now = datetime.now(timezone.utc)
    recent = [t for t in RATE_LIMIT_BUCKETS[client] if now - t < timedelta(minutes=1)]
    if len(recent) >= MAX_REQ_PER_MIN:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    recent.append(now)
    RATE_LIMIT_BUCKETS[client] = recent


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest", dependencies=[Depends(require_api_key)])
def ingest() -> dict[str, Any]:
    incoming = mock_news_batch()
    new_rows = dedupe_articles(incoming, set(STATE["articles"].keys()))
    for row in new_rows:
        STATE["articles"][row["id"]] = row
    return {"ingested": len(new_rows), "total_articles": len(STATE["articles"])}


@app.post("/enrich", dependencies=[Depends(require_api_key)])
def enrich() -> dict[str, Any]:
    for aid, article in STATE["articles"].items():
        if aid not in STATE["enriched"]:
            STATE["enriched"][aid] = enrich_article(article)
    return {"enriched": len(STATE["enriched"])}


@app.post("/events/rebuild", dependencies=[Depends(require_api_key)])
def rebuild_events() -> dict[str, Any]:
    clusters = cluster_articles(list(STATE["enriched"].values()))
    events = [to_event(i, c) for i, c in enumerate(clusters, start=1)]
    STATE["events"] = {e["id"]: e for e in events}
    for event in events:
        STATE["event_updates"].append(event)
    return {"events": len(events)}


@app.get("/events")
def list_events(
    topic: str | None = Query(default=None),
    sentiment: str | None = Query(default=None),
    min_impact: float = Query(default=0.0),
) -> dict[str, Any]:
    rate_limit("public-events")
    events = list(STATE["events"].values())
    if topic:
        events = [e for e in events if e["topic"] == topic]
    if sentiment:
        events = [e for e in events if e["sentiment"] == sentiment]
    events = [e for e in events if e["impact_score"] >= min_impact]
    events.sort(key=lambda e: e["impact_score"], reverse=True)
    return {"items": events}


@app.get("/events/{event_id}")
def event_detail(event_id: str) -> dict[str, Any]:
    event = STATE["events"].get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    articles = [STATE["enriched"][aid] for aid in event["article_ids"] if aid in STATE["enriched"]]
    return {"event": event, "articles": articles}


async def event_stream() -> AsyncIterator[str]:
    sent = 0
    while True:
        if sent < len(STATE["event_updates"]):
            event = list(STATE["event_updates"])[sent]
            yield f"data: {event}\n\n"
            sent += 1
        else:
            yield "event: heartbeat\ndata: {}\n\n"
        await __import__("asyncio").sleep(2)


@app.get("/events/stream")
async def stream_events() -> StreamingResponse:
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    await websocket.accept()
    for event in STATE["events"].values():
        await websocket.send_json(event)
    while True:
        await websocket.send_json({"type": "heartbeat"})
        await __import__("asyncio").sleep(5)
