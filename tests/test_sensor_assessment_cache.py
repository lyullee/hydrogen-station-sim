from h2station import api


def test_sensor_assessment_cache_reuses_same_snapshot(monkeypatch):
    api._sensor_assessment_cache.clear()
    calls = {"count": 0}

    def fake_assess(frame, catalog, backend, node_ids, *, max_cases=3, proposals=None):
        calls["count"] += 1
        return [{"node_id": node_ids[0] if node_ids else "N09", "calculation_status": "calculated"}]

    monkeypatch.setattr(api, "assess_sensor_cases", fake_assess)
    frame = {
        "time_s": 12.0,
        "hazop": {
            "signals": {"PT-0901": {"value": 80.0, "quality": "GOOD", "unit": "MPa"}},
            "releases": [],
        },
        "active_faults": [],
        "relief_valves_open": [],
    }
    first = api._assess_sensor_cases_cached(frame, {}, object(), ["N09"])
    first[0]["calculation_status"] = "mutated-by-caller"
    second = api._assess_sensor_cases_cached(frame, {}, object(), ["N09"])

    assert calls["count"] == 1
    assert second[0]["calculation_status"] == "calculated"


def test_sensor_assessment_cache_invalidates_when_release_state_changes(monkeypatch):
    api._sensor_assessment_cache.clear()
    calls = {"count": 0}

    def fake_assess(frame, catalog, backend, node_ids, *, max_cases=3, proposals=None):
        calls["count"] += 1
        return [{"node_id": node_ids[0], "calculation_status": "calculated"}]

    monkeypatch.setattr(api, "assess_sensor_cases", fake_assess)
    base = {
        "time_s": 12.0,
        "hazop": {
            "signals": {"PT-0901": {"value": 80.0, "quality": "GOOD", "unit": "MPa"}},
            "releases": [],
        },
        "active_faults": [],
        "relief_valves_open": [],
    }
    api._assess_sensor_cases_cached(base, {}, object(), ["N09"])
    changed = {**base, "hazop": {**base["hazop"], "releases": [{"release_id": "r1", "component_id": "cascade"}]}}
    api._assess_sensor_cases_cached(changed, {}, object(), ["N09"])

    assert calls["count"] == 2
