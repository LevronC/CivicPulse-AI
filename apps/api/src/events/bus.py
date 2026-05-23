from __future__ import annotations

"""
In-process event bus for decoupled subsystem communication.

Ingestion, enrichment, and rebuild operations publish domain events
without knowing who subscribes. The SSE stream module subscribes to
receive updates and push them to connected clients.

This keeps the dependency graph clean:
  services -> bus (publish)
  stream   -> bus (subscribe)

Neither side imports the other.

For multi-instance deployments this bus can be replaced with Redis
pub/sub or a message broker using the same subscribe/publish interface.
"""

from collections import defaultdict
from typing import Any, Callable

from src.logging import get_logger

logger = get_logger("events.bus")

Listener = Callable[[dict[str, Any]], None]


class EventBus:
    """Simple publish/subscribe bus for domain events."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[Listener]] = defaultdict(list)

    def subscribe(self, event_type: str, listener: Listener) -> None:
        self._listeners[event_type].append(listener)

    def publish(self, event_type: str, data: dict[str, Any]) -> None:
        for listener in self._listeners.get(event_type, []):
            try:
                listener(data)
            except Exception:
                logger.exception(
                    "Event listener failed",
                    extra={"event_type": event_type},
                )

        for listener in self._listeners.get("*", []):
            try:
                listener({"type": event_type, **data})
            except Exception:
                logger.exception("Wildcard listener failed")


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
