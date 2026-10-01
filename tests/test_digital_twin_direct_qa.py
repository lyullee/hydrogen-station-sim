"""The monitor's direct Q&A routes retain sensor-based consequence results."""

from fastapi.testclient import TestClient

import h2station.api as api


def _frame(*, alarm=False):
    return {
        "time_s": 12.0,
        "analysis": {"status": "WARNING" if alarm else "NORMAL", "findings": []},
        "active_faults": [],
        "hazop": {"active": [], "releases": [], "signals": {
            "PT-0901": {"value": 88.0, "unit": "MPa", "quality": "GOOD"},
            "TT-0901": {"value": 27.0, "unit": "°C", "quality": "GOOD"},
        }},
    }


def test_direct_qa_calculates_impact_for_alarm_and_explicit_hypothesis(monkeypatch):
    received = []
    llm_prompts = []
    impact = {"node_id": "N09", "node_name": "고압 저장뱅크",
              "calculation_status": "calculated", "calculation_basis": "SENSOR_BASED_HYPOTHESIS",
              "pressure_sensor": "PT-0901", "current_pressure_mpa": 88.0,
              "maximum_heat_flux_w_m2": 6200.0, "sampled_effect_radius_m": 3.0}
    monkeypatch.setattr(api, "load_hyram_backend", lambda: object())
    monkeypatch.setattr(api, "assess_sensor_cases", lambda *args: [impact])
    monkeypatch.setattr(api, "_invoke_saga_hazop_direct",
                        lambda *args: received.append(args[-1]) or {"status": "NORMAL", "hits": []})
    async def one_pass(question, context, history, provider, request_kind, stream_output=False):
        llm_prompts.append({"question": question, "context": context, "kind": request_kind})
        return {"answer": "질문에 대한 직접 답변입니다.", "model": "one-pass-test"}
    monkeypatch.setattr(api, "_invoke_main_assistant_selected", one_pass)
    monkeypatch.setattr(api, "_invoke_saga_selected", lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("reasoning endpoint must not be called")))
    monkeypatch.setattr(api, "_run_saga_scenario_analysis", lambda *args: (_ for _ in ()).throw(
        AssertionError("generative scenario planner must not be called")))
    job_id = "direct-qa-impact"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [_frame()]}
    try:
        with TestClient(api.app) as client:
            normal = client.post(f"/api/simulations/{job_id}/saga-analysis/direct",
                                 json={"direct": False, "question": "현재 상태"}).json()
            assert normal["impact_results"] == []
            assert normal["show_impact_results"] is False
            hypothetical = client.post(f"/api/simulations/{job_id}/saga-analysis/direct",
                                       json={"direct": False, "scenario_mode": True,
                                             "question": "고압 저장 가정 누출 피해영향"}).json()
            assert hypothetical["show_impact_results"] is True
            assert hypothetical["impact_results"] == [impact]
            assert hypothetical["response_guidance"] is None
            assert "PT-0901" in hypothetical["answer"]
            assert "질문에 대한 직접 답변" in hypothetical["answer"]
            assert "피해영향예측" in hypothetical["answer"]
            assert "피해영향예측" not in hypothetical["question_answer"]
            assert "질문에 대한 직접 답변" in hypothetical["question_answer"]
            assert llm_prompts[-1]["context"]["impact_results"][0]["maximum_heat_flux_w_m2"] == 6200.0
            assert llm_prompts[-1]["kind"] == "user_query"
            assert received[-1] == [impact]
            streamed = client.post(f"/api/simulations/{job_id}/saga-analysis/direct/stream",
                                   json={"direct": False, "scenario_mode": True,
                                         "question": "고압 저장 가정 누출 피해영향"})
            assert streamed.status_code == 200
            assert "event: token" in streamed.text
            assert "event: result" in streamed.text
            assert '"show_impact_results": true' in streamed.text
            with api._jobs_lock:
                api._jobs[job_id]["frames"][-1] = _frame(alarm=True)
            alarm = client.post(f"/api/simulations/{job_id}/saga-analysis/direct",
                                json={"direct": False, "trigger": "alarm", "question": "현재 경보"}).json()
            assert alarm["risk_assessment"]["status"] == "WARNING"
            assert alarm["impact_results"] == [impact]
            assert "피해영향예측" in alarm["answer"]
            assert llm_prompts[-1]["context"]["impact_calculation_attempted"] is True
            assert llm_prompts[-1]["kind"] == "automatic_analysis"
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_sensor_followup_direct_route_never_calls_reasoning(monkeypatch):
    monkeypatch.setattr(api, "_invoke_saga_hazop_direct", lambda *args: {"status": "NORMAL", "hits": []})
    prompts = []
    async def one_pass(sensor_id, question, context, provider, request_kind, stream_output=False):
        prompts.append({"sensor_id": sensor_id, "question": question,
                        "context": context, "kind": request_kind})
        return {"answer": "현재 압력은 88 MPa입니다.", "model": "one-pass-test"}
    monkeypatch.setattr(api, "_invoke_sensor_assistant_selected", one_pass)
    monkeypatch.setattr(api, "load_hyram_backend", lambda: object())
    monkeypatch.setattr(api, "assess_sensor_cases", lambda *args: [{
        "node_id": "N09", "calculation_status": "calculated",
        "calculation_basis": "SENSOR_BASED_HYPOTHESIS",
        "maximum_heat_flux_w_m2": 5000.0,
    }])
    monkeypatch.setattr(api, "_invoke_saga_selected", lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("reasoning endpoint must not be called")))
    job_id = "direct-qa-sensor"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [_frame()]}
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/sensors/PT-0901/analyze/direct",
                                   json={"direct": False, "question": "현재 압력은?"})
            streamed = client.post(f"/api/simulations/{job_id}/sensors/PT-0901/analyze/direct/stream",
                                   json={"direct": False, "question": "현재 압력은?"})
            requested = client.post(f"/api/simulations/{job_id}/sensors/PT-0901/analyze/direct",
                                    json={"question": "이 센서 기준 피해영향은?"})
        assert response.status_code == 200
        assert "88" in response.json()["answer"]
        assert any(item["question"] == "현재 압력은?" for item in prompts)
        assert response.json()["impact_results"] == []
        assert streamed.status_code == 200
        assert "event: result" in streamed.text
        assert requested.json()["impact_results"][0]["node_id"] == "N09"
        assert prompts[-1]["context"]["impact_results"][0]["maximum_heat_flux_w_m2"] == 5000.0
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_direct_impact_question_targets_named_equipment():
    catalog = api.load_catalog()
    assert {row["node_id"] for row in api._mentioned_hazop_nodes("압축기 누출 피해영향", catalog)} >= {"N03", "N06"}
    assert {row["node_id"] for row in api._mentioned_hazop_nodes("트레일러 누출 피해영향", catalog)} >= {"N01", "N02"}


def test_direct_answer_must_not_negate_confirmed_sensor_or_impact_evidence():
    conflicts = api._direct_answer_conflicts_with_signals
    assert conflicts("현재 정상 상태이며 경보가 없습니다.", alert=True)
    assert conflicts("가스는 감지되지 않았습니다.", gas_observed=True)
    assert conflicts("현재 누출이 없습니다.", physical_leak=True)
    assert conflicts("피해영향 결과가 없습니다.", impact_calculated=True)
    assert not conflicts("현재 정상 상태가 아닙니다.", alert=True)
    assert not conflicts("가정 누출은 실제 누출이 아닙니다.", physical_leak=True)


def test_direct_qa_falls_back_to_verified_alarm_when_llm_says_normal(monkeypatch):
    monkeypatch.setattr(api, "_invoke_saga_hazop_direct", lambda *args: None)
    monkeypatch.setattr(api, "load_hyram_backend", lambda: object())
    monkeypatch.setattr(api, "assess_sensor_cases", lambda *args: [])

    async def contradictory_answer(*args, **kwargs):
        return {"answer": "현재 정상 상태이며 경보가 없습니다.", "model": "unreliable-test"}

    monkeypatch.setattr(api, "_invoke_main_assistant_selected", contradictory_answer)
    job_id = "direct-qa-grounding"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [_frame(alarm=True)]}
    try:
        with TestClient(api.app) as client:
            result = client.post(f"/api/simulations/{job_id}/saga-analysis/direct",
                                 json={"question": "현재 경보는?"}).json()
        assert result["risk_assessment"]["status"] == "WARNING"
        assert "정상 상태" not in result["answer"]
        assert "주의·경보" in result["answer"]
        assert result["model"] == "SAGA 직답 · 센서값 검증"
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_idle_zero_flow_does_not_become_a_false_alarm_from_saga(monkeypatch):
    raw = {"status": "WARNING", "hits": [
        {"tag_id": "FT-0201", "value": 0.0, "risk_scenario": "공급 실패"},
        {"tag_id": "PT-0701", "value": 45.0, "risk_scenario": "잔압"},
    ], "sop": {"answer": "공급 실패 경보"}}
    monkeypatch.setattr(api, "_invoke_saga_hazop_direct", lambda *args: raw)

    async def answer(*args, **kwargs):
        return {"answer": "현재 공정은 대기 중입니다.", "model": "one-pass-test"}

    monkeypatch.setattr(api, "_invoke_main_assistant_selected", answer)
    job_id = "direct-qa-idle"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [_frame()]}
    try:
        with TestClient(api.app) as client:
            result = client.post(f"/api/simulations/{job_id}/saga-analysis/direct",
                                 json={"question": "현재 상태는?"}).json()
        assert result["risk_assessment"]["status"] == "NORMAL"
        assert result["hazop_hit_count"] == 0
        assert result["hazop_direct"]["status"] == "NORMAL"
        assert result["hazop_sop"] == {}
        assert result["show_impact_results"] is False
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_direct_evaluation_keeps_only_mode_aware_trigger_tags():
    result = api._align_direct_evaluation(
        {"status": "WARNING", "hits": [{"tag_id": "FT-0201"},
                                        {"tag_id": "GD-1301"}], "sop": {"answer": "unfiltered"}},
        [{"sensor_id": "FT-0201", "state": "NORMAL"},
         {"sensor_id": "GD-1301", "state": "TRIGGER"}], "WARNING",
    )
    assert result["hits"] == [{"tag_id": "GD-1301"}]
    assert result["sop"] == {}


def test_public_main_and_sensor_assistant_routes_are_isolated(monkeypatch):
    main_calls = []
    sensor_calls = []

    async def main_answer(question, context, history, provider, request_kind, stream_output=False):
        main_calls.append((question, provider, request_kind))
        return {"answer": "메인 질문 직접 답변", "model": "main-isolated"}

    async def sensor_answer(sensor_id, question, context, provider, request_kind,
                            stream_output=False):
        sensor_calls.append((sensor_id, question, provider, request_kind))
        return {"answer": "센서 질문 직접 답변", "model": "sensor-isolated"}

    monkeypatch.setattr(api, "_invoke_main_assistant_selected", main_answer)
    monkeypatch.setattr(api, "_invoke_sensor_assistant_selected", sensor_answer)
    monkeypatch.setattr(api, "_invoke_saga_hazop_direct", lambda *args: None)
    job_id = "isolated-assistant-routes"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [_frame()]}
    try:
        with TestClient(api.app) as client:
            main = client.post(f"/api/simulations/{job_id}/assistants/main", json={
                "question": "압력 보완을 멈추려면?", "provider": "service_hub",
            })
            sensor = client.post(
                f"/api/simulations/{job_id}/assistants/sensors/PT-0901", json={
                    "question": "이 값이 왜 올랐어?", "provider": "groq",
                },
            )
        assert main.status_code == 200
        assert sensor.status_code == 200
        assert main.json()["model"] == "main-isolated"
        assert sensor.json()["model"] == "sensor-isolated"
        assert main_calls == [("압력 보완을 멈추려면?", "service_hub", "user_query")]
        assert sensor_calls == [("PT-0901", "이 값이 왜 올랐어?", "groq", "user_query")]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)
