from __future__ import annotations

"""
Realtime event stream endpoints (SSE and WebSocket).

Subscribes to the in-process event bus so that ingestion, enrichment,
and rebuild operations automatically push updates to connected clients
without either side importing the other.
"""

import asyncio
import json
from collections import deque
from typing import Any, AsyncIterator

from fastapi import APIRouter, WebSocket
from fastapi.responses import StreamingResponse

from src.events.bus import get_event_bus
from src.logging import get_logger

logger = get_logger("stream")

router = APIRouter(tags=["stream"])

_event_buffer: deque[dict[str, Any]] = deque(maxlen=500)
_initialized = False


def _ensure_subscribed() -> None:
    """
    Subscribe to the event bus once on first access.

    Listens to all event types (*) so that ingestion results,
    enrichment completions, and rebuild events all flow to
    connected SSE/WebSocket clients.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True
    bus = get_event_bus()
    bus.subscribe("*", lambda data: _event_buffer.append(data))
    logger.info("Stream subscribed to event bus")


async def _sse_generator() -> AsyncIterator[str]:
    _ensure_subscribed()
    sent = len(_event_buffer)
    while True:
        current_len = len(_event_buffer)
        if sent < current_len:
            items = list(_event_buffer)
            for item in items[sent:]:
                yield f"data: {json.dumps(item, default=str)}\n\n"
            sent = current_len
        else:
            yield "event: heartbeat\ndata: {}\n\n"
        await asyncio.sleep(2)


@router.get("/events/stream")
async def stream_events() -> StreamingResponse:
    return StreamingResponse(_sse_generator(), media_type="text/event-stream")


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    _ensure_subscribed()
    await websocket.accept()
    for event in list(_event_buffer):
        await websocket.send_json(event)
    sent = len(_event_buffer)

    try:
        while True:
            current_len = len(_event_buffer)
            if sent < current_len:
                items = list(_event_buffer)
                for item in items[sent:]:
                    await websocket.send_json(item)
                sent = current_len
            else:
                await websocket.send_json({"type": "heartbeat"})
            await asyncio.sleep(5)
    except Exception:
        pass
