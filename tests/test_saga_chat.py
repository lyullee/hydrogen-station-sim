"""SAGA receives conversation context and actual rules for a named equipment node."""

import io
import json
from urllib.error import URLError

import pytest
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
        assert data["show_impact_results"] is True
        assert "계산이 필요" not in data["answer"]
        assert "3 m로 확정" not in data["answer"]
        assert "현재 압력을 확인" in data["answer"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_routine_saga_hides_impact_until_alert_or_explicit_request(monkeypatch):
    calls = []
    class FakeBackend:
        available = True

        def evaluate_release(self, request):
            calls.append(request)
            return {"status": "calculated", "maximum_heat_flux_w_m2": 8300.0,
                    "maximum_overpressure_pa": 6200.0, "sampled_effect_radius_m": 3.0,
                    "sampled_max_distance_m": 5.0, "effect_range_status": "WITHIN_SAMPLED_POINTS"}

    def fake_urlopen(request, timeout):
        answer = "현재 센서는 정상입니다.\n1 mm 가정 누출 열복사 8.3 kW/m², 영향 반경 3 m."
        return io.BytesIO(json.dumps({"answer": answer, "model": "test"}).encode())

    monkeypatch.setattr(api, "load_hyram_backend", lambda: FakeBackend())
    monkeypatch.setattr(api, "urlopen", fake_urlopen)
    job_id = "saga-visibility-test"
    frame = {"time_s": 10.0, "analysis": {"status": "NORMAL"}, "hazop": {
        "active": [], "releases": [], "signals": {
            "PT-0901": {"value": 88.0, "quality": "GOOD"},
            "TT-0901": {"value": 31.0, "quality": "GOOD"},
        }}}
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [frame]}
    try:
        with TestClient(api.app) as client:
            normal = client.post(f"/api/simulations/{job_id}/saga-analysis", json={"trigger": "periodic"}).json()
            assert normal["show_impact_results"] is False
            assert normal["impact_results"] == []
            assert calls == []
            assert "열복사" not in normal["answer"]
            assert "현재 센서는 정상" in normal["answer"]

            requested = client.post(f"/api/simulations/{job_id}/saga-analysis",
                                    json={"question": "고압 저장뱅크 피해영향을 알려줘"}).json()
            assert requested["show_impact_results"] is True

            frame["analysis"]["status"] = "WARNING"
            warning = client.post(f"/api/simulations/{job_id}/saga-analysis", json={"trigger": "alarm"}).json()
            assert warning["show_impact_results"] is True
            assert warning["risk_assessment"]["status"] == "WARNING"
            assert warning["risk_assessment"]["calculated_impact_count"] > 0
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_routine_saga_discards_stale_failure_and_latched_claim(monkeypatch):
    def fake_urlopen(request, timeout):
        prompt = json.loads(request.data)["message"]
        assert '"impact_results": []' in prompt
        answer = ("현재 운전은 정상입니다.\nHY-07 계산 실패: IntegratorConcurrencyError\n"
                  "HY-22 입력 부족으로 피해영향을 계산하지 못했습니다.\n"
                  "모든 HAZOP 규칙은 LATCHED 상태지만 경보는 없습니다.")
        return io.BytesIO(json.dumps({"answer": answer, "model": "test"}).encode())

    monkeypatch.setattr(api, "urlopen", fake_urlopen)
    job_id = "saga-normal-cleanup-test"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [{"time_s": 1.0, "analysis": {"status": "NORMAL"},
            "hazop": {"active": [], "releases": [], "signals": {}}}]}
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/saga-analysis", json={"trigger": "periodic"})
        assert response.status_code == 200
        answer = response.json()["answer"]
        assert "현재 운전은 정상" in answer
        assert "HY-07" not in answer
        assert "HY-22" not in answer
        assert "LATCHED" not in answer
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_saga_public_answer_hides_internal_rule_engine_terms():
    answer = ("현재 저장뱅크 압력은 94.0 MPa입니다.\n"
              "활성 HAZOP 규칙이 없습니다.\n"
              "HZ-061 규칙 ID를 기준으로 판정했습니다.\n"
              "현재 센서값은 정상 범위입니다.")
    public = api._safe_saga_text(answer)
    assert "94.0 MPa" in public
    assert "현재 센서값" in public
    assert "HAZOP" not in public
    assert "HZ-061" not in public


def test_saga_public_answer_removes_false_impact_not_requested_claim():
    answer = ("현재 저장뱅크 압력은 94.0 MPa입니다.\n"
              "현재 피해영향예측은 요청되지 않았으므로 계산 결과를 제공하지 않습니다.\n"
              "SENSOR_BASED_HYPOTHESIS는 calculated 상태입니다.\n"
              "HZ‑081 경보 규칙을 확인하세요.\n"
              "현재 설비의 압력을 확인하고 현장 접근을 제한하세요.")
    public = api._safe_saga_text(answer)
    assert "94.0 MPa" in public
    assert "요청되지 않았" not in public
    assert "SENSOR_BASED_HYPOTHESIS" not in public
    assert "HZ‑081" not in public
    assert "현장 접근" in public


def test_active_external_fire_is_critical_before_sensor_rise():
    assessed = api._analyze_frame({"active_faults": ["external-fire:cascade.medium"]})
    assert assessed["status"] == "CRITICAL"
    assert any("화재" in finding for finding in assessed["findings"])


def test_alarm_impact_prioritizes_active_accident_location(monkeypatch):
    class FakeBackend:
        available = True

        def evaluate_release(self, request):
            return {"status": "calculated", "maximum_heat_flux_w_m2": 1000.0,
                    "maximum_overpressure_pa": 1000.0, "sampled_effect_radius_m": None,
                    "sampled_max_distance_m": 5.0, "effect_range_status": "BELOW_THRESHOLDS_AT_SAMPLES"}

    monkeypatch.setattr(api, "load_hyram_backend", lambda: FakeBackend())
    monkeypatch.setattr(api, "_invoke_saga", lambda prompt: {"answer": "중압 저장뱅크 화재 상태입니다.", "model": "test"})
    job_id = "saga-fire-location-test"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [{"time_s": 1.0, "analysis": {"status": "CRITICAL"},
            "active_faults": ["external-fire:cascade.medium"],
            "hazop": {"active": [], "releases": [], "signals": {
                "PT-0801": {"value": 65.0, "quality": "GOOD"},
                "TT-0801": {"value": 30.0, "quality": "GOOD"},
                "PT-0901": {"value": 94.0, "quality": "GOOD"},
                "TT-0901": {"value": 30.0, "quality": "GOOD"}}}}]}
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/saga-analysis", json={"trigger": "alarm"})
        assert response.status_code == 200
        assert response.json()["impact_results"][0]["node_id"] == "N08"
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_critical_alert_keeps_risk_and_impact_when_saga_is_unavailable(monkeypatch):
    class FakeBackend:
        available = True

        def evaluate_release(self, request):
            return {"status": "calculated", "maximum_heat_flux_w_m2": 8300.0,
                    "maximum_overpressure_pa": 6200.0, "sampled_effect_radius_m": 3.0,
                    "sampled_max_distance_m": 5.0, "effect_range_status": "WITHIN_SAMPLED_POINTS"}

    monkeypatch.setattr(api, "load_hyram_backend", lambda: FakeBackend())
    monkeypatch.setattr(api, "_invoke_saga", lambda prompt: (_ for _ in ()).throw(URLError("offline")))
    job_id = "saga-critical-fallback-test"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [{"time_s": 12.0, "analysis": {
            "status": "CRITICAL", "score": 3, "findings": ["저장뱅크 압력 상승"]},
            "hazop": {"active": [], "releases": [], "signals": {
                "PT-0901": {"value": 94.0, "quality": "GOOD"},
                "TT-0901": {"value": 28.0, "quality": "GOOD"}}}}]}
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/saga-analysis", json={"trigger": "alarm"})
        assert response.status_code == 200
        data = response.json()
        assert data["risk_assessment"]["status"] == "CRITICAL"
        assert data["show_impact_results"] is True
        assert data["impact_results"]
        assert "긴급" in data["answer"]
        assert "피해영향예측" in data["answer"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_area_case_uses_labelled_storage_bank_proxy(monkeypatch):
    from h2station.risk.sensor_assessment import assess_sensor_cases

    class FakeBackend:
        available = True

        def evaluate_release(self, request):
            return {"status": "calculated", "maximum_heat_flux_w_m2": 1.0,
                    "maximum_overpressure_pa": 2.0, "sampled_effect_radius_m": 0.0,
                    "sampled_max_distance_m": 5.0, "effect_range_status": "BELOW_THRESHOLDS_AT_SAMPLES"}

    frame = {"time_s": 2.0, "hazop": {"signals": {
        "PT-0701": {"value": 44.0, "quality": "GOOD"},
        "TT-0701": {"value": 23.7, "quality": "GOOD"},
    }, "releases": []}}
    impact = assess_sensor_cases(frame, api.load_catalog(), FakeBackend(), ["N22"])[0]
    assert impact["calculation_status"] == "calculated"
    assert impact["sensor_basis"] == "PROXY"
    assert impact["pressure_source_node_id"] == "N07"
    assert impact["temperature_source_node_id"] == "N07"
    assert impact["pressure_sensor"] == "PT-0701"


def test_saga_does_not_present_failed_impact_as_a_result(monkeypatch):
    captured = {}

    class FakeBackend:
        available = True

        def evaluate_release(self, request):
            raise RuntimeError("IntegratorConcurrencyError")

    def fake_urlopen(request, timeout):
        captured["prompt"] = json.loads(request.data)["message"]
        return io.BytesIO(b'{"answer":"No numeric impact result is available.","model":"test"}')

    monkeypatch.setattr(api, "load_hyram_backend", lambda: FakeBackend())
    monkeypatch.setattr(api, "urlopen", fake_urlopen)
    job_id = "saga-failed-impact-test"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [{"time_s": 2.0, "analysis": {"status": "NORMAL"},
            "hazop": {"active": [], "releases": [], "signals": {
                "PT-0701": {"value": 44.0, "quality": "GOOD"},
                "TT-0701": {"value": 23.7, "quality": "GOOD"},
            }}}]}
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/saga-analysis",
                                   json={"question": "저압 저장탱크 피해영향을 알려줘"})
        assert response.status_code == 200
        assert response.json()["impact_results"] == []
        assert "IntegratorConcurrencyError" not in captured["prompt"]
        assert '"impact_results": []' in captured["prompt"]
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
        assert data["show_impact_results"] is True
        assert data["proposed_scenarios"][0]["node_id"] == "N09"
        assert data["impact_results"][0]["calculation_basis"] == "LLM_PROPOSED_HYPOTHESIS"
        assert "표본 지점 과압" in data["answer"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_saga_rejects_proposal_using_bad_sensor_tag(monkeypatch):
    calls = []

    class FakeBackend:
        available = True

        def evaluate_release(self, request):
            raise AssertionError("Invalid proposal must not reach consequence engine")

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data)["message"])
        answer = ('{"scenarios":[{"node_id":"N13","leak_size_id":"L04",'
                  '"pressure_sensor":"PT-0901","temperature_sensor":"TT-1301",'
                  '"rationale":"test"}]}')
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
        assert '"case_id": "HY-09"' not in captured["prompts"][0]
        assert {request.component_id for request in captured["requests"]} == {"dispenser.hose", "dispenser_2.hose"}
        assert {row["scenario_id"] for row in data["impact_results"]} == {"LLM-1", "LLM-2"}
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_dispenser_question_uses_llm_selected_proxy_temperature(monkeypatch):
    question = "디스펜서에서 현재 상태에서 누출이 발생했을 때 예상 피해영향을 계산해줘."
    captured = {"prompts": []}

    class FakeBackend:
        available = True

        def evaluate_release(self, request):
            captured["request"] = request
            return {"status": "calculated", "maximum_heat_flux_w_m2": 42.0,
                    "maximum_overpressure_pa": 1050.0, "sampled_effect_radius_m": 0.0,
                    "sampled_max_distance_m": 5.0, "effect_range_status": "BELOW_THRESHOLDS_AT_SAMPLES"}

    def fake_urlopen(request, timeout):
        captured["prompts"].append(json.loads(request.data)["message"])
        answer = ('{"scenarios":[{"node_id":"N13","leak_size_id":"L03",'
                  '"pressure_sensor":"PT-1301","temperature_sensor":"TT-1201",'
                  '"rationale":"호스 압력과 인접 예냉기 온도를 대체 적용"}]}') if len(captured["prompts"]) == 1 else "N13의 온도는 N12 대체 신호입니다."
        return io.BytesIO(json.dumps({"answer": answer, "model": "test"}).encode())

    monkeypatch.setattr(api, "urlopen", fake_urlopen)
    monkeypatch.setattr(api, "load_hyram_backend", lambda: FakeBackend())
    job_id = "saga-dispenser-missing-test"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [{"time_s": 2.0, "hazop": {"active": [], "releases": [], "signals": {
            "PT-0901": {"value": 90.0, "quality": "GOOD"}, "TT-0901": {"value": 25.0, "quality": "GOOD"},
            "TT-1201": {"value": -34.0, "quality": "GOOD"},
            "PT-1301": {"value": 44.0, "quality": "GOOD"}, "TT-1301": {"value": -35.0, "quality": "BAD"},
        }}}]}
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/saga-analysis", json={"question": question})
        assert response.status_code == 200
        data = response.json()
        assert len(captured["prompts"]) == 2
        assert captured["prompts"][0].index('"sensor_id": "TT-1201"') < captured["prompts"][0].index('"sensor_id": "TT-0901"')
        assert len(data["impact_results"]) == 1
        assert data["impact_results"][0]["calculation_status"] == "calculated"
        assert data["impact_results"][0]["calculation_basis"] == "LLM_PROPOSED_PROXY_HYPOTHESIS"
        assert data["impact_results"][0]["pressure_sensor"] == "PT-1301"
        assert data["impact_results"][0]["temperature_sensor"] == "TT-1201"
        assert data["impact_results"][0]["temperature_source_node_id"] == "N12"
        assert captured["request"].source_temperature_k == pytest.approx(239.15)
        assert data["impact_results"][0]["sensor_basis"] == "PROXY"
        assert "대체 신호" in data["answer"]
        assert "계산을 요청" not in data["answer"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_saga_removes_deferred_calculation_advice():
    text = "필요 시 '피해영향예측' 계산을 요청해 주세요.\n피해영향예측 계산 완료, 현장 점검이 필요합니다."
    answer = api._safe_saga_text(text)
    assert "요청해 주세요" not in answer
    assert "계산 완료" in answer


def test_saga_rejects_non_string_sensor_selection():
    from h2station.risk.scenario_planning import parse_saga_plan

    answer = ('{"scenarios":[{"node_id":"N13","leak_size_id":"L03",'
              '"pressure_sensor":[],"temperature_sensor":"TT-1201","rationale":"proxy"}]}')
    with pytest.raises(ValueError, match="GOOD pressure and temperature"):
        parse_saga_plan(answer, {"N13"}, api.load_catalog(), {"PT-1301"}, {"TT-1201"})
