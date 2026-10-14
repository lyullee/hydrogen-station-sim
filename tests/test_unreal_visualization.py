import json
from copy import deepcopy

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from h2station.visualization import build_snapshot, scene_manifest, unreal_position
from h2station.unreal_api import make_unreal_router


@pytest.fixture
def state():
    return {
        "job": {"created_at": "2026-10-15T00:00:00Z", "status": "running"},
        "frame": {"sequence": 7, "time_s": 2.5, "esd": True,
                  "bank_pressure_mpa": {"low": 0, "medium": 68, "high": 96},
                  "bank_temperature_c": {"low": 0, "high": -12.5},
                  "bank_mass_kg": {"high": 20},
                  "vehicle_pressure_mpa": 5, "vehicle_2_pressure_mpa": 8,
                  "hazop": {"signals": {"GD-0901": {"value": 100, "quality": "GOOD"}},
                            "releases": [{"release_id": "leak-high", "component_id": "cascade.high",
                                          "mass_flow_g_s": 33.3,
                                          "consequence": {"sampled_effect_radius_m": 5.0}}]},
                  "active_faults": ["hydrogen-leak:cascade.high"]},
        "safety": {"valves": {"bank.high.inlet": {"commanded_open": False,
                       "actual_open": True, "feedback_open": True, "status": "moving"}}},
    }


def client_for(state):
    app = FastAPI()

    def read(run_id):
        if run_id != "test-run":
            raise HTTPException(404, "Simulation not found")
        return state["job"], state["frame"], state["safety"], None

    app.include_router(make_unreal_router(read))
    return TestClient(app)


def test_axis_conversion_and_geometry_dimensions():
    assert unreal_position((1, 2, 3)) == [100, 300, 200]
    assert unreal_position((0, 1, 0)) == [0, 0, 100]
    manifest = scene_manifest()
    high = next(e for e in manifest["equipment"] if e["component_id"] == "cascade.high")
    assert high["position_cm"] == [700, -600, 0]
    assert high["dimensions_cm"] == [265, 460, 280]
    assert len(manifest["detectors"]) == 24


def test_no_fabricated_normal_or_cross_vehicle_state(state):
    original = deepcopy(state)
    snapshot = build_snapshot("test-run", state["job"], state["frame"], state["safety"])
    eq = {e["component_id"]: e for e in snapshot["equipment"]}
    assert eq["cascade.low"]["pressure_mpa"] == 0
    assert eq["cascade.low"]["temperature_c"] == 0
    assert eq["cascade.medium"]["temperature_c"] is None
    assert eq["vehicle.tank"]["pressure_mpa"] == 5
    assert eq["vehicle_2.tank"]["pressure_mpa"] == 8
    assert snapshot["releases"][0]["sampled_effect_radius_m"] == 5
    assert snapshot["detectors"][0]["value"] == 100
    assert snapshot["safety"]["valves"]["bank.high.inlet"]["actual_open"] is True
    assert snapshot["active_faults"] == ["hydrogen-leak:cascade.high"]
    assert snapshot["risk_zones"]["status"] == "not_requested"
    assert state == original
    json.dumps(snapshot, allow_nan=False)


def test_nonfinite_and_waiting_state_are_unknown(state):
    state["frame"]["bank_pressure_mpa"]["high"] = float("nan")
    result = build_snapshot("test-run", state["job"], state["frame"])
    assert next(e for e in result["equipment"] if e["component_id"] == "cascade.high")["pressure_mpa"] is None
    waiting = build_snapshot("test-run", state["job"], None)
    assert waiting["sequence"] == -1 and waiting["data_available"] is False
    assert waiting["esd"] is None and waiting["releases"] == []


def test_snapshot_and_stream_do_not_call_physics_or_llm(state):
    client = client_for(state)
    assert client.get("/api/simulations/unknown/visualization/snapshot").status_code == 404
    result = client.get("/api/simulations/test-run/visualization/snapshot").json()
    assert result["sequence"] == 7
    with client.websocket_connect("/api/simulations/test-run/visualization/stream") as socket:
        assert socket.receive_json()["snapshot"]["run_id"] == "test-run"
    with client.websocket_connect("/api/simulations/missing/visualization/stream") as socket:
        assert socket.receive_json()["type"] == "error"


def test_terminal_run_sends_final_state(state):
    state["job"]["status"] = "complete"
    with client_for(state).websocket_connect("/api/simulations/test-run/visualization/stream") as socket:
        assert socket.receive_json()["snapshot"]["status"] == "complete"
        assert socket.receive()["type"] == "websocket.close"


def test_feedback_changes_are_streamed_even_without_new_process_frame(state):
    with client_for(state).websocket_connect("/api/simulations/test-run/visualization/stream") as socket:
        first = socket.receive_json()["snapshot"]
        state["safety"] = {"valves": {"bank.high.inlet": {"actual_open": False, "status": "confirmed"}}}
        second = socket.receive_json()["snapshot"]
        assert first["sequence"] == second["sequence"]
        assert second["safety"]["valves"]["bank.high.inlet"]["actual_open"] is False


def test_real_app_registers_unreal_routes_before_static_mount(monkeypatch, state):
    import h2station.api as api
    monkeypatch.setitem(api._jobs, "unreal-smoke", {
        **state["job"], "frames": [state["frame"]]})

    def forbidden(*args, **kwargs):
        raise AssertionError("A renderer read must not trigger consequence calculation")

    monkeypatch.setattr(api, "_load_hyram_backend_cached", forbidden)
    with TestClient(api.app) as client:
        assert client.get("/api/integrations/unreal/scene").status_code == 200
        result = client.get("/api/simulations/unreal-smoke/visualization/snapshot")
        assert result.status_code == 200
        assert result.json()["sequence"] == 7


def test_bind_and_reset_invalidate_old_run_without_stopping_process(state):
    client = client_for(state)
    base = "/api/integrations/unreal/session/default"
    assert client.get(base).json() == {"run_id": None, "generation": 0}
    assert client.post(base, json={"run_id": "missing"}).status_code == 404
    assert client.post(base, json={"run_id": "test-run"}).json()["generation"] == 1
    assert client.post(base, json={"run_id": "test-run"}).json()["generation"] == 1
    assert client.post(base, json={"run_id": None}).json() == {"run_id": None, "generation": 2}
    assert state["job"]["status"] == "running"


def test_config_is_explicit_and_rejects_embedded_credentials(monkeypatch, state):
    client = client_for(state)
    monkeypatch.delenv("H2STATION_UNREAL_PLAYER_URL", raising=False)
    assert not client.get("/api/integrations/unreal/config").json()["configured"]
    monkeypatch.setenv("H2STATION_UNREAL_PLAYER_URL", "https://user:secret@localhost")
    assert client.get("/api/integrations/unreal/config").status_code == 503
    monkeypatch.setenv("H2STATION_UNREAL_PLAYER_URL", "http://localhost:8080")
    assert client.get("/api/integrations/unreal/config").json()["configured"]


def test_late_binding_cannot_restore_incident_after_reset(state):
    client = client_for(state)
    base = "/api/integrations/unreal/session/default"
    assert client.post(base, json={"run_id": "test-run", "request_serial": 100}).status_code == 200
    assert client.post(base, json={"run_id": None, "request_serial": 102}).status_code == 200
    assert client.post(base, json={"run_id": "test-run", "request_serial": 101}).status_code == 409
    assert client.get(base).json()["run_id"] is None
    assert client.post(base, json={"run_id": "test-run", "request_serial": 102}).status_code == 409
