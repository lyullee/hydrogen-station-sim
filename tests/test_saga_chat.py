"""SAGA receives conversation context and actual rules for a named equipment node."""

import io
import json

from fastapi.testclient import TestClient

import h2station.api as api


def test_saga_followup_uses_registered_hazop_rules(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["prompt"] = json.loads(request.data)["message"]
        return io.BytesIO(json.dumps({"answer": "| 규칙 | 내용 |\n|---|---|\n| HZ-061 | 고압 저장 |", "model": "test"}).encode())

    monkeypatch.setattr(api, "urlopen", fake_urlopen)
    job_id = "saga-chat-test"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [{
            "time_s": 4.0, "analysis": {"status": "NORMAL"}, "active_faults": [],
            "hazop": {"active": [], "releases": [], "signals": {
                "PT-0901": {"value": 90.0, "unit": "MPa", "quality": "GOOD"},
            }},
        }]}
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/saga-analysis", json={
                "question": "고압 저장뱅크 압력과 관련 HAZOP 규칙을 표로 정리해줘.",
                "history": [{"role": "user", "content": "고압 저장뱅크를 살펴보자."},
                            {"role": "assistant", "content": "현재 압력을 확인했습니다."}],
            })
        assert response.status_code == 200
        assert "HZ-061" in captured["prompt"]
        assert "PT-0901" in captured["prompt"]
        assert '"sensor_id": "TT-0901"' not in captured["prompt"]
        assert "user: 고압 저장뱅크를 살펴보자." in captured["prompt"]
        assert "assistant: 현재 압력을 확인했습니다." in captured["prompt"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_saga_prompt_keeps_calculated_impact_before_large_sensor_context(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["prompt"] = json.loads(request.data)["message"]
        return io.BytesIO(b'{"answer":"ok","model":"test"}')

    monkeypatch.setattr(api, "urlopen", fake_urlopen)
    job_id = "saga-impact-test"
    signals = {f"PT-{number:04d}": {"value": float(number), "unit": "MPa", "quality": "GOOD"}
               for number in range(100, 220)}
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [{
            "time_s": 6.0, "analysis": {"status": "CRITICAL"}, "active_faults": [],
            "hazop": {"active": [], "signals": signals, "releases": [{
                "release_id": "leak-1", "component_id": "cascade.high", "mass_flow_g_s": 0.71,
                "consequence": {"status": "calculated", "maximum_heat_flux_w_m2": 41.1,
                                "maximum_overpressure_pa": 1527.0, "sampled_effect_radius_m": 0.0,
                                "sampled_max_distance_m": 5.0,
                                "effect_range_status": "BELOW_THRESHOLDS_AT_SAMPLES"},
            }]},
        }]}
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/saga-analysis", json={
                "question": "현재 누출의 피해영향예측 결과를 알려줘.",
            })
        assert response.status_code == 200
        prompt = captured["prompt"]
        assert '"calculation_status": "calculated"' in prompt
        assert '"maximum_heat_flux_w_m2": 41.1' in prompt
        assert '"sampled_effect_radius_m": null' in prompt
        assert "영향 반경 미확정" in prompt
        assert prompt.index("impact_results") < prompt.index("hazop_active")
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)
