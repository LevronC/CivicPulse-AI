"""Tests for the in-process event bus."""

from src.events.bus import EventBus


def test_publish_to_subscriber():
    bus = EventBus()
    received = []
    bus.subscribe("test.event", lambda data: received.append(data))

    bus.publish("test.event", {"key": "value"})
    assert len(received) == 1
    assert received[0]["key"] == "value"


def test_wildcard_subscriber_receives_all():
    bus = EventBus()
    received = []
    bus.subscribe("*", lambda data: received.append(data))

    bus.publish("event.a", {"a": 1})
    bus.publish("event.b", {"b": 2})
    assert len(received) == 2
    assert received[0]["type"] == "event.a"
    assert received[1]["type"] == "event.b"


def test_no_subscribers_does_not_raise():
    bus = EventBus()
    bus.publish("orphan.event", {"data": "ignored"})


def test_failing_listener_does_not_block_others():
    bus = EventBus()
    results = []

    def bad_listener(data):
        raise ValueError("boom")

    def good_listener(data):
        results.append(data)

    bus.subscribe("test", bad_listener)
    bus.subscribe("test", good_listener)
    bus.publish("test", {"ok": True})

    assert len(results) == 1
    assert results[0]["ok"] is True


def test_multiple_subscribers_same_event():
    bus = EventBus()
    a_received = []
    b_received = []

    bus.subscribe("shared", lambda d: a_received.append(d))
    bus.subscribe("shared", lambda d: b_received.append(d))
    bus.publish("shared", {"x": 1})

    assert len(a_received) == 1
    assert len(b_received) == 1
