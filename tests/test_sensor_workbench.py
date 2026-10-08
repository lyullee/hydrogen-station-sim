"""Selected-sensor detail and focused SAGA analysis stay scoped to one tag."""

import h2station.api as api
from fastapi.testclient import TestClient


def _job(job_id, *, active=False):
    rule = {"rule_id": "HZ-053", "node_id": "N08", "sensor_id": "PT-0801",
            "active": True, "state": "TRIGGER", "value": 68.4, "quality": "GOOD"}
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [{
            "time_s": 42.0, "analysis": {"status": "WARNING" if active else "NORMAL"},
            "active_faults": [], "relief_valves_open": [],
            "hazop": {"active": [rule] if active else [], "releases": [], "signals": {
                "PT-0801": {"value": 68.4 if active else 64.0, "unit": "MPa", "quality": "GOOD"},
                "TT-0801": {"value": 27.0, "unit": "°C", "quality": "GOOD"},
                "PT-0901": {"value": 92.0, "unit": "MPa", "quality": "GOOD"},
            }},
        }]}


def test_selected_sensor_analysis_streams_llm_tokens(monkeypatch):
    def fake_stream(prompt, length, provider, on_token):
        assert provider == "groq"
        assert length == "detailed"
        assert "왜 이 센서가 위험한가?" in prompt
        on_token("중압 저장뱅크 ")
        on_token("압력 정상")
        return {"answer": "중압 저장뱅크 압력 정상", "model": "test"}

    monkeypatch.setattr(api, "_invoke_saga_stream", fake_stream)
    job_id = "sensor-workbench-stream"
    _job(job_id)
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/sensors/PT-0801/analyze/stream",
                                   json={"provider": "groq", "question": "왜 이 센서가 위험한가?", "direct": False})
        assert response.status_code == 200, response.text
        assert response.text.count("event: token") == 2
        assert response.text.index("event: token") < response.text.index("event: result")
        assert "중압 저장뱅크" in response.text
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_live_selected_sensor_uses_direct_api_with_computed_impact(monkeypatch):
    captured = {}

    class FakeBackend:
        available = True

        def evaluate_release(self, request):
            return {"status": "calculated", "maximum_heat_flux_w_m2": 5100.0,
                    "maximum_overpressure_pa": 4200.0, "sampled_effect_radius_m": 3.0,
                    "literature_delayed_ignition_status": "CALCULATED_EXTRAPOLATED",
                    "literature_delayed_ignition_5kpa_radial_distance_m": 5.4,
                    "literature_delayed_ignition_distance_origin":
                    "CENTRE_OF_25_TO_35_VOL_PERCENT_H2_CLOUD",
                    "literature_delayed_ignition_site_safety_distance": False,
                    "literature_delayed_ignition_doi": "10.3390/hydrogen3040027"}

    def direct(frame, catalog, station_id, question, impact_results):
        captured["signals"] = set(frame["hazop"]["signals"])
        captured["impacts"] = impact_results
        return {"status": "WARNING", "hits": [],
                "sop": {"answer": "중압 저장뱅크 압력 상승을 확인했습니다."}}

    monkeypatch.setattr(api, "load_hyram_backend", lambda: FakeBackend())
    monkeypatch.setattr(api, "_invoke_saga_hazop_direct", direct)
    monkeypatch.setattr(api, "_invoke_saga", lambda *args: (_ for _ in ()).throw(
        AssertionError("Live sensor analysis must not call generative chat")))
    job_id = "sensor-workbench-direct-alarm"
    _job(job_id, active=True)
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/sensors/PT-0801/analyze/stream",
                                   json={"direct": True})
        assert response.status_code == 200, response.text
        assert "event: token" in response.text
        assert "피해영향예측" in response.text
        assert captured["signals"] == {"PT-0801", "TT-0801"}
        assert captured["impacts"][0]["pressure_sensor"] == "PT-0801"
        assert captured["impacts"][0]["literature_delayed_ignition_5kpa_radial_distance_m"] == 5.4
        assert captured["impacts"][0]["literature_delayed_ignition_site_safety_distance"] is False
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_sensor_detail_exposes_current_value_rule_and_response_plan(monkeypatch):
    captured = {}

    def llm(prompt, answer_length):
        captured["prompt"] = prompt
        return {"answer": "### 현재 판정\n중압 뱅크 압력을 확인했습니다.", "model": "test"}

    monkeypatch.setattr(api, "_invoke_saga", llm)
    job_id = "sensor-workbench-normal"
    _job(job_id)
    try:
        with TestClient(api.app) as client:
            detail = client.get(f"/api/simulations/{job_id}/sensors/PT-0801")
            analysis = client.post(f"/api/simulations/{job_id}/sensors/PT-0801/analyze", json={})
        assert detail.status_code == 200
        payload = detail.json()
        assert payload["signal"]["value"] == 64.0
        assert payload["sensor"]["node_id"] == "N08"
        assert any(rule["scenario"] == "뱅크 과압 대응 후보" for rule in payload["rules"])
        assert "overpressure" in payload["response_plans"]
        assert payload["related_signals"]["TT-0801"]["value"] == 27.0
        assert "PT-0901" not in payload["related_signals"]
        assert analysis.status_code == 200
        assert analysis.json()["active_rule_count"] == 0
        assert "중압 뱅크" in analysis.json()["answer"]
        assert "### 예방·안전관리" in analysis.json()["answer"]
        assert "**즉시 조치**" not in analysis.json()["answer"]
        assert analysis.json()["response_guidance"]["actual_alert"] is False
        assert "PT-0801" in captured["prompt"]
        assert "TT-0801" in captured["prompt"]
        assert "PT-0901" not in captured["prompt"]
        assert '"immediate"' not in captured["prompt"]
        assert "비상대응을 출력하지 말고" in captured["prompt"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_active_sensor_computes_impact_before_focused_llm(monkeypatch):
    captured = {}
    monkeypatch.setattr(api, "load_hyram_backend", lambda: object())

    def assess(frame, catalog, backend, nodes):
        captured["nodes"] = nodes
        return [{"calculation_status": "calculated", "node_id": "N08", "maximum_overpressure_pa": 1200.0}]

    def llm(prompt, answer_length):
        captured["prompt"] = prompt
        assert answer_length == "detailed"
        return {"answer": "중압 저장뱅크 압력 상승을 확인하세요.", "model": "test"}

    monkeypatch.setattr(api, "assess_sensor_cases", assess)
    monkeypatch.setattr(api, "_invoke_saga", llm)
    job_id = "sensor-workbench-alarm"
    _job(job_id, active=True)
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/sensors/PT-0801/analyze",
                                   json={"question": "이 압력 상승의 우선 조치는?"})
        assert response.status_code == 200
        assert captured["nodes"] == ["N08"]
        assert '"maximum_overpressure_pa": 1200.0' in captured["prompt"]
        assert "이 압력 상승의 우선 조치는?" in captured["prompt"]
        assert "사용자 질문에 먼저 직접 답하고" in captured["prompt"]
        assert "Markdown 인용문" in captured["prompt"]
        assert response.json()["active_rule_count"] == 1
        answer = response.json()["answer"]
        assert "### 종합 안전판단" in answer
        assert "#### 발생 가능한 시나리오" in answer
        assert "### 즉시 실행할 단계별 대응" in answer
        assert "**2단계 · 공정 정지·격리 및 인원 보호**" in answer
        assert "**3단계 · 안정화 확인**" in answer
        assert "**4단계 · 복구·재가동 전 확인**" in answer
        assert "### 단계별 예방·안전관리" in answer
        assert response.json()["response_guidance"]["actual_alert"] is True
        assert response.json()["response_guidance"]["mode"] == "consolidated"
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_direct_sensor_llm_cannot_replace_detailed_emergency_guidance(monkeypatch):
    monkeypatch.setattr(api, "load_hyram_backend", lambda: object())
    monkeypatch.setattr(api, "assess_sensor_cases", lambda *args: [])
    monkeypatch.setattr(api, "_invoke_saga_hazop_direct",
                        lambda *args: {"status": "WARNING", "hits": []})

    async def terse_answer(*args, **kwargs):
        return {"answer": "중압 저장뱅크 압력 경보입니다.", "model": "terse-test"}

    monkeypatch.setattr(api, "_invoke_sensor_assistant_selected", terse_answer)
    job_id = "sensor-workbench-direct-guidance"
    _job(job_id, active=True)
    try:
        with TestClient(api.app) as client:
            response = client.post(
                f"/api/simulations/{job_id}/sensors/PT-0801/analyze/direct",
                json={"provider": "groq", "question": "현재 상태를 분석해줘"},
            )
        assert response.status_code == 200
        result = response.json()
        assert result["model"] == "terse-test"
        assert "중압 저장뱅크 압력 경보입니다." in result["answer"]
        assert "### 종합 안전판단" in result["answer"]
        assert "#### 발생 가능한 시나리오" in result["answer"]
        assert "**2단계 · 공정 정지·격리 및 인원 보호**" in result["answer"]
        assert "**3단계 · 안정화 확인**" in result["answer"]
        assert "**4단계 · 복구·재가동 전 확인**" in result["answer"]
        assert "### 단계별 예방·안전관리" in result["answer"]
        assert result["response_guidance"]["plans"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_related_threshold_alarms_collapse_into_one_operator_scenario():
    catalog = api.load_catalog()
    definitions = {rule["rule_id"]: rule for rule in catalog["rules"]}
    ids = ("HZ-156", "HZ-157", "HZ-158", "HZ-178")
    active = []
    frame_active = []
    for rule_id in ids:
        rule = definitions[rule_id]
        active.append({"rule_id": rule_id, "node_id": rule["node_id"],
                       "sensor_id": rule["sensor_id"], "scenario": rule["시나리오명"],
                       "response_plan_id": api.classify_rule(rule), "state": "TRIGGER"})
        frame_active.append({"rule_id": rule_id, "node_id": rule["node_id"],
                             "sensor_id": rule["sensor_id"], "state": "TRIGGER",
                             "value": 100.0, "quality": "GOOD"})
    playbooks = api.load_playbooks()
    known = {plan["id"]: plan for plan in playbooks["plans"]}
    markdown, guidance = api._sensor_response_guidance(
        {"hazop": {"active": frame_active, "releases": []}, "active_faults": []},
        catalog, "현재 상태를 분석해줘", active, [], {"gas_release": None}, known,
    )
    assert guidance["mode"] == "consolidated"
    assert len(guidance["scenarios"]) == 1
    assert guidance["scenarios"][0]["id"] == "gas_release"
    assert "경보 조건 4건" in markdown
    assert "**1개 대응 시나리오**" in markdown
    assert markdown.count("### 즉시 실행할 단계별 대응") == 1
    assert markdown.count("### 단계별 예방·안전관리") == 1
    assert len(guidance["plans"]) == 1


def test_unknown_sensor_returns_404():
    job_id = "sensor-workbench-unknown"
    _job(job_id)
    try:
        with TestClient(api.app) as client:
            response = client.get(f"/api/simulations/{job_id}/sensors/PT-9999")
        assert response.status_code == 404
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_retained_alarm_does_not_recalculate_impact_and_uses_short_answer(monkeypatch):
    captured = {}

    def unexpected_impact(*args):
        raise AssertionError("A retained alarm is not a new release calculation trigger")

    def llm(prompt, answer_length):
        captured.update(prompt=prompt, answer_length=answer_length)
        return {"answer": "현재 검지값은 기준 미만이며 경보 이력만 유지 중입니다.", "model": "test"}

    monkeypatch.setattr(api, "load_hyram_backend", unexpected_impact)
    monkeypatch.setattr(api, "assess_sensor_cases", unexpected_impact)
    monkeypatch.setattr(api, "_invoke_saga", llm)
    job_id = "sensor-workbench-retained"
    _job(job_id)
    with api._jobs_lock:
        frame = api._jobs[job_id]["frames"][-1]
        frame["hazop"]["signals"]["GD-0801"] = {"value": 0.347, "unit": "vol%_H2", "quality": "GOOD"}
        frame["hazop"]["active"] = [{"rule_id": "HZ-153", "node_id": "N08",
                                         "sensor_id": "GD-0801", "active": True,
                                         "state": "LATCHED", "condition_status": "NORMAL",
                                         "value": 0.347, "quality": "GOOD"}]
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/sensors/GD-0801/analyze", json={})
        assert response.status_code == 200
        assert response.json()["impact_results"] == []
        assert captured["answer_length"] == "concise"
        assert "비영점 가스 농도나 모의 누출을 부정하지 마세요" in captured["prompt"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_below_alarm_gas_reading_and_live_release_are_not_reported_as_no_leak(monkeypatch):
    captured = {}
    monkeypatch.setattr(api, "load_hyram_backend", lambda: (_ for _ in ()).throw(
        AssertionError("Retained alarm must not start a new impact calculation")))

    def llm(prompt, answer_length):
        captured["prompt"] = prompt
        return {"answer": captured.get("answer", "현재 누출은 없습니다."), "model": "test"}

    monkeypatch.setattr(api, "_invoke_saga", llm)
    job_id = "sensor-workbench-gas-below-alarm"
    _job(job_id)
    with api._jobs_lock:
        frame = api._jobs[job_id]["frames"][-1]
        frame["hazop"]["signals"]["GD-1301"] = {"value": 0.218, "unit": "vol%_H2", "quality": "GOOD"}
        frame["hazop"]["active"] = [{"rule_id": "HZ-162", "node_id": "N13",
                                         "sensor_id": "GD-1301", "active": True,
                                         "state": "LATCHED", "condition_status": "NORMAL",
                                         "value": 0.218, "quality": "GOOD"}]
        frame["hazop"]["releases"] = [{"release_id": "test-hose-leak",
                                          "component_id": "dispenser.hose", "mass_flow_g_s": 0.04}]
    try:
        with TestClient(api.app) as client:
            detail = client.get(f"/api/simulations/{job_id}/sensors/GD-1301")
            analysis = client.post(f"/api/simulations/{job_id}/sensors/GD-1301/analyze", json={})
            captured["answer"] = "현재 가스 감지(current_gas_alerts)는 없고 경보 이력만 있습니다."
            ambiguous = client.post(f"/api/simulations/{job_id}/sensors/GD-1301/analyze", json={})
        assert detail.status_code == 200
        assert detail.json()["gas_signal_evidence"] == {
            "value_volpct_h2": 0.218, "alarm_threshold_volpct_h2": 0.4,
            "hydrogen_observed": True, "alarm_threshold_exceeded": False}
        assert detail.json()["simulated_release_evidence"]["active"] is True
        assert analysis.status_code == 200
        assert '"observed_hydrogen_readings": [{"tag": "GD-1301", "value_volpct_h2": 0.218' in captured["prompt"]
        assert '"simulated_release_evidence": {"active": true, "mass_flow_g_s": 0.04' in captured["prompt"]
        assert "0.218 vol%" in analysis.json()["answer"]
        assert "0.040 g/s" in analysis.json()["answer"]
        assert "누출은 없습니다" not in analysis.json()["answer"]
        assert ambiguous.status_code == 200
        assert "현재 가스 감지" not in ambiguous.json()["answer"]
        assert "0.218 vol%" in ambiguous.json()["answer"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_one_sensor_combines_simultaneous_scenarios_and_response_families(monkeypatch):
    captured = {}
    monkeypatch.setattr(api, "load_hyram_backend", lambda: object())
    monkeypatch.setattr(api, "assess_sensor_cases", lambda *args: [])

    def llm(prompt, answer_length):
        captured["prompt"] = prompt
        return {"answer": "과압과 급감압 징후를 함께 확인합니다.", "model": "test"}

    monkeypatch.setattr(api, "_invoke_saga", llm)
    job_id = "sensor-workbench-compound"
    _job(job_id, active=True)
    with api._jobs_lock:
        frame = api._jobs[job_id]["frames"][-1]
        frame["hazop"]["active"] = [
            {"rule_id": rule_id, "node_id": "N08", "sensor_id": "PT-0801",
             "active": True, "state": "TRIGGER", "severity": "ALARM",
             "value": 70.0, "quality": "GOOD"}
            for rule_id in ("HZ-052", "HZ-057")
        ]
        frame["hazop"]["active"].append(
            {"rule_id": "HZ-059", "node_id": "N08", "sensor_id": "FT-0801",
             "active": True, "state": "TRIGGER", "severity": "ALARM",
             "value": 8.0, "quality": "GOOD"})
        frame["hazop"]["signals"]["PT-0801"]["value"] = 70.0
        frame["hazop"]["signals"]["FT-0801"] = {"value": 8.0, "unit": "g/s", "quality": "GOOD"}
    try:
        with TestClient(api.app) as client:
            detail = client.get(f"/api/simulations/{job_id}/sensors/PT-0801")
            analysis = client.post(f"/api/simulations/{job_id}/sensors/PT-0801/analyze", json={})
        assert detail.status_code == 200
        assert detail.json()["active_rule_count"] == 2
        assert detail.json()["sensor_status"] == "ALERT"
        assert detail.json()["related_active_rules"][0]["response_plan_id"] == "flow_anomaly"
        assert {rule["response_plan_id"] for rule in detail.json()["rules"] if rule["active"]} == {
            "overpressure", "gas_release"}
        assert analysis.status_code == 200
        assert analysis.json()["active_rule_count"] == 2
        assert '"rule_id": "HZ-052"' in captured["prompt"]
        assert '"rule_id": "HZ-057"' in captured["prompt"]
        assert '"rule_id": "HZ-059"' in captured["prompt"]
        assert '"immediate"' in captured["prompt"]
        assert "동시 경보를 공통 원인별 시나리오로 묶고" in captured["prompt"]
        assert analysis.json()["response_guidance"]["mode"] == "consolidated"
        assert {row["id"] for row in analysis.json()["response_guidance"]["scenarios"]} == {
            "overpressure", "gas_release", "flow_anomaly"}
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_sensor_analysis_uses_displayed_frame_instead_of_newest_frame(monkeypatch):
    captured = {}
    monkeypatch.setattr(api, "load_hyram_backend", lambda: object())
    monkeypatch.setattr(api, "assess_sensor_cases", lambda *args: [])
    monkeypatch.setattr(api, "_invoke_saga", lambda prompt, length: captured.update(prompt=prompt)
                        or {"answer": "표시 시각에 화염이 감지되었습니다.", "model": "test"})
    job_id = "sensor-workbench-snapshot"
    _job(job_id)
    with api._jobs_lock:
        first = api._jobs[job_id]["frames"][0]
        first["hazop"]["signals"]["FD-0801"] = {"value": 1.0, "unit": "bool", "quality": "GOOD"}
        first["hazop"]["active"] = [{"rule_id": "HZ-209", "node_id": "N08",
                                       "sensor_id": "FD-0801", "active": True,
                                       "state": "TRIGGER", "value": 1.0, "quality": "GOOD"}]
        second = {**first, "time_s": 43.0,
                  "hazop": {**first["hazop"], "active": [],
                            "signals": {**first["hazop"]["signals"],
                                        "FD-0801": {"value": 0.0, "unit": "bool", "quality": "GOOD"}}}}
        api._jobs[job_id]["frames"].append(second)
        api._jobs[job_id]["hazop_detail"] = {"rules": [{"rule_id": "HZ-209", "active": False,
                                                          "state": "NORMAL", "value": 0.0}]}
    try:
        with TestClient(api.app) as client:
            detail = client.get(f"/api/simulations/{job_id}/sensors/FD-0801?time_s=42")
            analysis = client.post(f"/api/simulations/{job_id}/sensors/FD-0801/analyze",
                                   json={"time_s": 42.0})
        assert detail.status_code == 200
        assert detail.json()["signal"]["value"] == 1.0
        assert detail.json()["active_rule_count"] == 1
        assert analysis.status_code == 200
        assert analysis.json()["time_s"] == 42.0
        assert '"value": 1.0' in captured["prompt"]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_normal_flame_sensor_reports_related_gas_detection_and_latched_history(monkeypatch):
    prompts = []
    monkeypatch.setattr(api, "load_hyram_backend", lambda: object())
    monkeypatch.setattr(api, "assess_sensor_cases", lambda *args: [])
    monkeypatch.setattr(api, "_invoke_saga", lambda prompt, length: prompts.append(prompt)
                        or {"answer": "가스검지 신호와 화염검지 신호를 구분했습니다.", "model": "test"})
    job_id = "sensor-workbench-related-gas"
    _job(job_id)
    with api._jobs_lock:
        frame = api._jobs[job_id]["frames"][-1]
        frame["hazop"]["signals"]["FD-0801"] = {"value": 0.0, "unit": "bool", "quality": "GOOD"}
        frame["hazop"]["signals"]["GD-0801"] = {"value": 1.2, "unit": "vol%_H2", "quality": "GOOD"}
        frame["hazop"]["signals"]["GD-2201"] = {"value": 0.0, "unit": "vol%_H2", "quality": "GOOD"}
        frame["hazop"]["active"] = [
            {"rule_id": "HZ-154", "node_id": "N08", "sensor_id": "GD-0801",
             "active": True, "state": "TRIGGER", "value": 1.2, "quality": "GOOD"},
            {"rule_id": "HZ-178", "node_id": "N22", "sensor_id": "GD-2201",
             "active": True, "state": "LATCHED", "value": 0.0, "quality": "GOOD"},
        ]
    try:
        with TestClient(api.app) as client:
            detail = client.get(f"/api/simulations/{job_id}/sensors/FD-0801")
            analysis = client.post(f"/api/simulations/{job_id}/sensors/FD-0801/analyze", json={})
        assert detail.json()["sensor_status"] == "NORMAL"
        assert detail.json()["related_active_count"] == 2
        assert {rule["sensor_id"] for rule in detail.json()["related_active_rules"]} == {"GD-0801", "GD-2201"}
        assert analysis.json()["related_active_count"] == 2
        assert '"current_gas_alerts": [{"tag": "GD-0801", "value": 1.2' in prompts[-1]
        assert '"retained_gas_alarm_tags": ["GD-2201"]' in prompts[-1]
        with api._jobs_lock:
            frame["hazop"]["signals"]["GD-0801"]["value"] = 0.0
            frame["hazop"]["active"][0].update(state="LATCHED", condition_status="NORMAL", value=0.0)
        with TestClient(api.app) as client:
            analysis = client.post(f"/api/simulations/{job_id}/sensors/FD-0801/analyze", json={})
        assert analysis.json()["related_active_count"] == 2
        assert '"current_gas_alerts": []' in prompts[-1]
        assert '"retained_gas_alarm_tags": ["GD-0801", "GD-2201"]' in prompts[-1]
        with TestClient(api.app) as client:
            gas_analysis = client.post(f"/api/simulations/{job_id}/sensors/GD-0801/analyze", json={})
        assert gas_analysis.json()["active_rule_count"] == 1
        assert "비영점 가스 농도나 모의 누출을 부정하지 마세요" in prompts[-1]
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)
