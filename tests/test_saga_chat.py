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


def test_saga_calculates_current_sensor_hazop_impact_before_llm(monkeypatch):
    captured = {}

    class FakeBackend:
        available = True

        def evaluate_release(self, request):
            captured["request"] = request
            return {"status": "calculated", "maximum_heat_flux_w_m2": 8300.0,
                    "maximum_overpressure_pa": 6200.0, "sampled_effect_radius_m": 3.0,
                    "sampled_max_distance_m": 5.0, "effect_range_status": "WITHIN_SAMPLED_POINTS"}

    def fake_urlopen(request, timeout):
        captured["prompt"] = json.loads(request.data)["message"]
        return io.BytesIO(json.dumps({"answer": "HYRAM 피해영향예측 계산이 필요합니다.\n영향 반경은 3 m로 확정됩니다.\n현재 압력을 확인했습니다.",
                                      "model": "test"}).encode())

    monkeypatch.setattr(api, "load_hyram_backend", lambda: FakeBackend())
    monkeypatch.setattr(api, "urlopen", fake_urlopen)
    job_id = "saga-sensor-impact-test"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [{
            "time_s": 42.0, "analysis": {"status": "NORMAL"}, "active_faults": [],
            "hazop": {"active": [], "releases": [], "signals": {
                "PT-0901": {"value": 88.0, "unit": "MPa", "quality": "GOOD"},
                "TT-0901": {"value": 31.0, "unit": "°C", "quality": "GOOD"},
            }},
        }]}
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/saga-analysis", json={
                "question": "고압 저장뱅크 피해영향을 분석해줘.",
            })
        assert response.status_code == 200
        data = response.json()
        assert captured["request"].source_pressure_pa == 88e6
        assert captured["request"].source_temperature_k == 304.15
        assert captured["request"].orifice_diameter_m == 0.001
        assert '"calculation_status": "calculated"' in captured["prompt"]
        assert '"current_pressure_mpa": 88.0' in captured["prompt"]
        assert '"calculation_basis": "SENSOR_BASED_HYPOTHESIS"' in captured["prompt"]
        assert data["impact_results"][0]["maximum_heat_flux_w_m2"] == 8300.0
        assert "계산이 필요" not in data["answer"]
        assert "3 m로 확정" not in data["answer"]
        assert "현장 안전반경은 확정할 수 없습니다" in data["answer"]
        assert "현재 압력을 확인" in data["answer"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_sensor_assessment_rejects_bad_quality_without_calling_backend():
    from h2station.risk.sensor_assessment import assess_sensor_cases

    class FakeBackend:
        available = True

        def evaluate_release(self, request):
            raise AssertionError("Bad sensor values must not reach the consequence engine")

    frame = {"time_s": 3.0, "hazop": {"signals": {
        "PT-0901": {"value": 90, "quality": "GOOD"},
        "TT-0901": {"value": 25, "quality": "BAD"},
    }, "releases": []}}
    impact = assess_sensor_cases(frame, api.load_catalog(), FakeBackend(), ["N09"])[0]
    assert impact["calculation_status"] == "input_unavailable"
    assert impact["pressure_sensor"] == "PT-0901"
    assert "temperature_sensor" not in impact


def test_sensor_assessment_uses_live_release_orifice_and_flow():
    from h2station.risk.sensor_assessment import assess_sensor_cases

    class FakeBackend:
        available = True

        def evaluate_release(self, request):
            self.request = request
            return {"status": "calculated", "maximum_heat_flux_w_m2": 12.0,
                    "maximum_overpressure_pa": 34.0,
                    "sampled_effect_radius_m": 0.0, "sampled_max_distance_m": 5.0,
                    "effect_range_status": "BELOW_THRESHOLDS_AT_SAMPLES"}

    backend = FakeBackend()
    frame = {"time_s": 9.0, "hazop": {"signals": {
        "PT-0901": {"value": 84.0, "quality": "GOOD"},
        "TT-0901": {"value": 29.0, "quality": "GOOD"},
    }, "releases": [{"release_id": "actual-1", "component_id": "cascade.high",
                     "orifice_diameter_m": 0.003, "mass_flow_g_s": 8.0}]}}
    impact = assess_sensor_cases(frame, api.load_catalog(), backend, ["N09"])[0]
    assert impact["calculation_basis"] == "ACTIVE_RELEASE_CURRENT_SENSORS"
    assert impact["orifice_source"] == "ACTIVE_RELEASE"
    assert impact["sampled_effect_radius_m"] is None
    assert backend.request.source_pressure_pa == 84e6
    assert backend.request.orifice_diameter_m == 0.003
    assert backend.request.mass_flow_override_kg_s == 0.008


def test_saga_can_propose_calculate_and_interpret_scenarios(monkeypatch):
    captured = {"prompts": []}

    class FakeBackend:
        available = True

        def evaluate_release(self, request):
            captured["request"] = request
            return {"status": "calculated", "maximum_heat_flux_w_m2": 7200.0,
                    "maximum_overpressure_pa": 8100.0, "sampled_effect_radius_m": 3.0,
                    "sampled_max_distance_m": 5.0, "effect_range_status": "WITHIN_SAMPLED_POINTS"}

    def fake_urlopen(request, timeout):
        prompt = json.loads(request.data)["message"]
        captured["prompts"].append(prompt)
        if len(captured["prompts"]) == 1:
            answer = '```json\n{"scenarios":[{"node_id":"N09","leak_size_id":"L04","rationale":"고압 저장 HAZOP 검토"}]}\n```'
        else:
            answer = "N09의 가정 누출은 실제 사고가 아닙니다. 표본 지점 과압을 우선 검토합니다."
        return io.BytesIO(json.dumps({"answer": answer, "model": "test"}).encode())

    monkeypatch.setattr(api, "load_hyram_backend", lambda: FakeBackend())
    monkeypatch.setattr(api, "urlopen", fake_urlopen)
    job_id = "saga-scenario-test"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [{
            "time_s": 17.0, "analysis": {"status": "NORMAL"}, "active_faults": [],
            "hazop": {"active": [], "releases": [], "signals": {
                "PT-0901": {"value": 89.0, "unit": "MPa", "quality": "GOOD"},
                "TT-0901": {"value": 28.0, "unit": "°C", "quality": "GOOD"},
            }},
        }]}
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/saga-analysis", json={
                "scenario_mode": True, "question": "고압 저장 사고 시나리오를 생성해 평가해줘.",
            })
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(captured["prompts"]) == 2
        assert captured["request"].orifice_diameter_m == 0.003
        assert captured["request"].source_pressure_pa == 89e6
        assert '"maximum_overpressure_pa": 8100.0' in captured["prompts"][1]
        assert data["scenario_mode"] is True
        assert data["proposed_scenarios"][0]["node_id"] == "N09"
        assert data["impact_results"][0]["calculation_basis"] == "LLM_PROPOSED_HYPOTHESIS"
        assert "실제 사고 발생이나 현장 안전반경을 뜻하지 않습니다" in data["answer"]
        assert "표본 지점 과압" in data["answer"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_saga_rejects_proposal_without_good_sensor_pair(monkeypatch):
    calls = []

    class FakeBackend:
        available = True

        def evaluate_release(self, request):
            raise AssertionError("Invalid proposal must not reach consequence engine")

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data)["message"])
        answer = '{"scenarios":[{"node_id":"N08","leak_size_id":"L04","rationale":"test"}]}'
        return io.BytesIO(json.dumps({"answer": answer, "model": "test"}).encode())

    monkeypatch.setattr(api, "load_hyram_backend", lambda: FakeBackend())
    monkeypatch.setattr(api, "urlopen", fake_urlopen)
    job_id = "saga-invalid-scenario-test"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [{"time_s": 1.0, "hazop": {"active": [], "releases": [], "signals": {
            "PT-0901": {"value": 90.0, "unit": "MPa", "quality": "GOOD"},
            "TT-0901": {"value": 25.0, "unit": "°C", "quality": "GOOD"},
        }}}]}
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/saga-analysis", json={
                "scenario_mode": True, "question": "가상 누출을 평가해줘.",
            })
        assert response.status_code == 502
        assert len(calls) == 2
        assert "형식 검증 실패" in response.json()["detail"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_dispenser_hypothetical_leak_question_runs_scoped_impact_calculation(monkeypatch):
    question = "디스펜서에서 현재 상태에서 누출이 발생했을 때 예상 피해영향을 계산해줘."
    catalog = api.load_catalog()
    assert api._scenario_requested(api.SagaAnalysisInput(question=question))
    assert {row["node_id"] for row in api._mentioned_hazop_nodes(question, catalog)} == {"N13", "N17"}
    captured = {"prompts": [], "requests": []}

    class FakeBackend:
        available = True

        def evaluate_release(self, request):
            captured["requests"].append(request)
            return {"status": "calculated", "maximum_heat_flux_w_m2": 510.0,
                    "maximum_overpressure_pa": 2100.0, "sampled_effect_radius_m": 0.0,
                    "sampled_max_distance_m": 5.0, "effect_range_status": "BELOW_THRESHOLDS_AT_SAMPLES"}

    def fake_urlopen(request, timeout):
        captured["prompts"].append(json.loads(request.data)["message"])
        answer = ('{"scenarios":[{"node_id":"N13","leak_size_id":"L03","rationale":"디스펜서 1 호스"},'
                  '{"node_id":"N17","leak_size_id":"L02","rationale":"디스펜서 2 호스"}]}') if len(captured["prompts"]) == 1 else "계산된 두 가정 누출을 비교합니다."
        return io.BytesIO(json.dumps({"answer": answer, "model": "test"}).encode())

    monkeypatch.setattr(api, "load_hyram_backend", lambda: FakeBackend())
    monkeypatch.setattr(api, "urlopen", fake_urlopen)
    job_id = "saga-dispenser-question-test"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [{"time_s": 12.0, "hazop": {"active": [], "releases": [], "signals": {
            "PT-0901": {"value": 90.0, "quality": "GOOD"}, "TT-0901": {"value": 25.0, "quality": "GOOD"},
            "PT-1301": {"value": 44.0, "quality": "GOOD"}, "TT-1301": {"value": -35.0, "quality": "GOOD"},
            "PT-1701": {"value": 39.0, "quality": "GOOD"}, "TT-1701": {"value": -32.0, "quality": "GOOD"},
        }}}]}
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/saga-analysis", json={"question": question})
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["scenario_mode"] is True
        assert {row["node_id"] for row in data["impact_results"]} == {"N13", "N17"}
        assert '"node_id": "N09"' not in captured["prompts"][0]
        assert {request.component_id for request in captured["requests"]} == {"dispenser.hose", "dispenser_2.hose"}
        assert "LLM-1" in data["answer"] and "LLM-2" in data["answer"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_dispenser_question_reports_missing_sensor_instead_of_asking_for_calculation(monkeypatch):
    question = "디스펜서에서 현재 상태에서 누출이 발생했을 때 예상 피해영향을 계산해줘."

    def fake_urlopen(request, timeout):
        raise AssertionError("No usable dispenser sensors: do not ask the LLM to guess")

    monkeypatch.setattr(api, "urlopen", fake_urlopen)
    job_id = "saga-dispenser-missing-test"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [{"time_s": 2.0, "hazop": {"active": [], "releases": [], "signals": {
            "PT-0901": {"value": 90.0, "quality": "GOOD"}, "TT-0901": {"value": 25.0, "quality": "GOOD"},
            "PT-1301": {"value": 44.0, "quality": "GOOD"}, "TT-1301": {"value": -35.0, "quality": "BAD"},
        }}}]}
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/saga-analysis", json={"question": question})
        assert response.status_code == 200
        data = response.json()
        assert {row["node_id"] for row in data["impact_results"]} == {"N13", "N17"}
        assert all(row["calculation_status"] == "input_unavailable" for row in data["impact_results"])
        assert "N13" in data["answer"] and "N17" in data["answer"]
        assert "계산을 요청" not in data["answer"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_saga_removes_deferred_calculation_advice():
    text = "필요 시 '피해영향예측' 계산을 요청해 주세요.\n피해영향예측 계산 완료, 현장 점검이 필요합니다."
    answer = api._safe_saga_text(text)
    assert "요청해 주세요" not in answer
    assert "계산 완료" in answer
