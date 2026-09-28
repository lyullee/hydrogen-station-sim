"""A live leak can enter and leave an already running physical simulation."""
import time

from fastapi.testclient import TestClient

from h2station.api import app


def _wait_for(client, job_id, predicate, timeout=25):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        frames = client.get(f"/api/simulations/{job_id}/frames").json()["frames"]
        if predicate(frames):
            return frames
        time.sleep(.05)
    raise AssertionError("live simulation did not reach expected state")


def test_add_and_remove_live_leak_changes_process():
    with TestClient(app) as client:
        job_id = client.post("/api/simulations", json={"continuous": True,
            "duration_s": 2.0, "control_period_s": .2}).json()["id"]
        try:
            _wait_for(client, job_id, lambda frames: len(frames) >= 2)
            response = client.post(f"/api/simulations/{job_id}/faults", json={
                "event_id": "live-leak", "kind": "hydrogen-leak", "target": "cascade.high",
                "start_time_s": 0, "leak_diameter_mm": .2,
            })
            assert response.status_code == 202, response.text
            frames = _wait_for(client, job_id, lambda frames: any(
                frame["total_leak_flow_g_s"] > 0 and
                "hydrogen-leak:cascade.high" in frame["active_faults"] for frame in frames))
            assert frames[-1]["released_mass_kg"] >= 0
            response = client.delete(f"/api/simulations/{job_id}/faults/live-leak")
            assert response.status_code == 202, response.text
            _wait_for(client, job_id, lambda frames: len(frames) > 3 and
                "hydrogen-leak:cascade.high" not in frames[-1]["active_faults"])
        finally:
            client.post(f"/api/simulations/{job_id}/stop")
