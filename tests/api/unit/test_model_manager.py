"""Tests for the ModelManager — lazy loading, thread safety, lifecycle."""

import threading

from src.services.enrichment.models.manager import ModelManager


def _echo_backend(text: str) -> dict:
    return {"echo": text}


def _counter_factory():
    call_count = {"n": 0}
    def backend(text: str) -> dict:
        call_count["n"] += 1
        return {"count": call_count["n"]}
    return backend


def test_lazy_loading():
    mgr = ModelManager()
    loaded = []
    def factory():
        loaded.append(True)
        return _echo_backend
    mgr.register("test_model", factory)

    assert not mgr.is_loaded("test_model")
    assert len(loaded) == 0

    backend = mgr.get("test_model")
    assert mgr.is_loaded("test_model")
    assert len(loaded) == 1
    assert backend("hello") == {"echo": "hello"}


def test_shared_instance():
    mgr = ModelManager()
    mgr.register("shared", lambda: _echo_backend)

    a = mgr.get("shared")
    b = mgr.get("shared")
    assert a is b


def test_unload_and_reload():
    mgr = ModelManager()
    load_count = []
    def factory():
        load_count.append(1)
        return _echo_backend
    mgr.register("reloadable", factory)

    mgr.get("reloadable")
    assert len(load_count) == 1

    mgr.unload("reloadable")
    assert not mgr.is_loaded("reloadable")

    mgr.get("reloadable")
    assert len(load_count) == 2


def test_missing_model_raises():
    mgr = ModelManager()
    try:
        mgr.get("nonexistent")
        assert False, "Should have raised"
    except KeyError as e:
        assert "nonexistent" in str(e)


def test_status_report():
    mgr = ModelManager()
    mgr.register("model_a", lambda: _echo_backend, device="cpu")
    mgr.register("model_b", lambda: _echo_backend, device="cuda")

    status = mgr.status()
    assert len(status) == 2
    names = {s["name"] for s in status}
    assert names == {"model_a", "model_b"}
    assert all(not s["loaded"] for s in status)

    mgr.get("model_a")
    status = mgr.status()
    loaded_names = {s["name"] for s in status if s["loaded"]}
    assert loaded_names == {"model_a"}


def test_thread_safe_loading():
    mgr = ModelManager()
    load_count = {"n": 0}
    lock = threading.Lock()

    def slow_factory():
        import time
        time.sleep(0.05)
        with lock:
            load_count["n"] += 1
        return _echo_backend

    mgr.register("concurrent", slow_factory)
    threads = [threading.Thread(target=lambda: mgr.get("concurrent")) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert load_count["n"] == 1


def test_unload_all():
    mgr = ModelManager()
    mgr.register("a", lambda: _echo_backend)
    mgr.register("b", lambda: _echo_backend)
    mgr.get("a")
    mgr.get("b")

    mgr.unload_all()
    assert not mgr.is_loaded("a")
    assert not mgr.is_loaded("b")
