"""Fast-path guards for optional companion services and expensive runtimes."""

from urllib.error import URLError

import h2station.api as api


def test_hyram_backend_is_loaded_once_per_loader(monkeypatch):
    calls = {"count": 0}

    class Backend:
        available = True

    def fake_loader():
        calls["count"] += 1
        return Backend()

    monkeypatch.setattr(api, "load_hyram_backend", fake_loader)
    api._hyram_backend_cache.clear()
    first = api._load_hyram_backend_cached()
    second = api._load_hyram_backend_cached()

    assert first is second
    assert calls["count"] == 1


def test_direct_hazop_failure_circuit_breaker_skips_repeated_timeout(monkeypatch):
    calls = {"count": 0}

    def failed_urlopen(*args, **kwargs):
        calls["count"] += 1
        raise URLError("companion unavailable")

    monkeypatch.setattr(api, "urlopen", failed_urlopen)
    api._saga_direct_failure_until.clear()
    monkeypatch.setattr(api, "_SAGA_DIRECT_FAILURE_COOLDOWN_S", 30.0)
    frame = {"hazop": {"signals": {"PT-0901": {"value": 80.0, "quality": "GOOD"}}}}

    assert api._invoke_saga_hazop_direct(
        frame, api.load_catalog(), "station", "현재 상태", []
    ) is None
    assert api._invoke_saga_hazop_direct(
        frame, api.load_catalog(), "station", "현재 상태", []
    ) is None
    assert calls["count"] == 1


def test_isolated_assistant_failure_circuit_breaker_skips_repeated_call(monkeypatch):
    calls = {"count": 0}

    def failed_urlopen(*args, **kwargs):
        calls["count"] += 1
        raise URLError("companion unavailable")

    monkeypatch.setattr(api, "urlopen", failed_urlopen)
    api._saga_assistant_failure_until.clear()
    monkeypatch.setattr(api, "_SAGA_ASSISTANT_FAILURE_COOLDOWN_S", 30.0)
    request = api.Request("http://127.0.0.1:8090/api/integrations/digital-twin/main")

    for _ in range(2):
        try:
            api._open_saga_assistant(request, endpoint_key="main")
        except URLError:
            pass
        else:  # pragma: no cover - a failing transport is required here
            raise AssertionError("expected the optional companion call to fail")
    assert calls["count"] == 1
