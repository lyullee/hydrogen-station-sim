import pytest
import time
from fastapi.testclient import TestClient

from h2station.api import (
    CounterfactualBatchInput,
    FaultInput,
    ProcessSettings,
    SimulationInput,
    _counterfactual_action_sets,
    app,
)


def batch():
    simulation = SimulationInput(
        duration_s=30,
        process_settings=ProcessSettings(),
        faults=[FaultInput(
            event_id="leak", kind="hydrogen-leak", target="cascade.medium",
            start_time_s=1, leak_diameter_mm=1,
        )],
    )
    return CounterfactualBatchInput(simulation=simulation, intervention_time_s=5)


def test_counterfactual_protocol_freezes_scenario_and_varies_only_response():
    plans = _counterfactual_action_sets(batch())
    assert set(plans) == {"no_action", "isolation", "esd", "esd_isolation_ventilation"}
    assert plans["no_action"] == []
    isolation_targets = {row.target for row in plans["isolation"]}
    assert {"bank.medium.inlet", "bank.medium.outlet"} <= isolation_targets
    assert {row.kind for row in plans["esd"]} == {"esd.trip", "operation.stop"}
    assert {row.kind for row in plans["esd_isolation_ventilation"]} >= {
        "esd.trip", "valve.close", "ventilation.on", "access.restrict",
        "personnel.evacuate",
    }
    assert all(row.time_s == 5 for rows in plans.values() for row in rows)


def test_schedule_requires_operator_runtime_and_finite_time():
    from h2station.api import ScheduledSafetyActionInput
    with pytest.raises(ValueError, match="operator process_settings"):
        SimulationInput(
            duration_s=10,
            scheduled_safety_actions=[ScheduledSafetyActionInput(
                time_s=1, kind="esd.trip", target="station"
            )],
        )


def test_counterfactual_endpoint_runs_same_fault_with_distinct_action_histories(monkeypatch):
    import h2station.api as api
    from h2station.risk.runtime_backend import UnavailableHyRAMBackend
    monkeypatch.setattr(api, "load_hyram_backend", lambda: UnavailableHyRAMBackend())
    with TestClient(app) as client:
        response = client.post("/api/simulations/counterfactual-batch", json={
            "intervention_time_s": .2,
            "simulation": {
                "duration_s": .8,
                "control_period_s": .2,
                "process_settings": ProcessSettings().model_dump(),
                "faults": [{"event_id": "paired-leak", "kind": "hydrogen-leak",
                            "target": "cascade.high", "start_time_s": 0,
                            "leak_diameter_mm": .2}],
            },
        })
        assert response.status_code == 202, response.text
        runs = response.json()["runs"]
        deadline = time.monotonic() + 15
        statuses = {}
        while time.monotonic() < deadline:
            statuses = {name: client.get(f"/api/simulations/{job_id}").json()["status"]
                        for name, job_id in runs.items()}
            if all(status in {"complete", "failed"} for status in statuses.values()):
                break
            time.sleep(.05)
        assert statuses == {name: "complete" for name in runs}
        histories = {name: client.get(
            f"/api/simulations/{job_id}/safety/replay"
        ).json()["actions"] for name, job_id in runs.items()}
        assert histories["no_action"] == []
        assert {row["kind"] for row in histories["esd"]} >= {"esd.trip", "operation.stop"}
        assert {row["kind"] for row in histories["esd_isolation_ventilation"]} >= {
            "esd.trip", "valve.close", "ventilation.on", "personnel.evacuate"
        }
