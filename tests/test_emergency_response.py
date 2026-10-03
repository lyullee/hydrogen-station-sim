"""Emergency guidance follows the active station signal, even without SAGA."""

from fastapi.testclient import TestClient
import sqlite3

import h2station.api as api
from h2station.hazop.database import DEFAULT_DB, load_catalog
from h2station.hazop.response import (classify_rule, load_playbooks, prompt_guidance,
                                      response_selection, structured_guidance)


def test_all_registered_sensor_rules_have_a_complete_response_plan():
    catalog = load_catalog()
    playbooks = load_playbooks()
    plans = {plan["id"] for plan in playbooks["plans"]}
    assert len(catalog["rules"]) == 214
    assert all(classify_rule(rule) in plans for rule in catalog["rules"])
    named = {rule["시나리오명"]: classify_rule(rule) for rule in catalog["rules"]}
    assert named["뱅크 과압 대응 후보"] == "overpressure"
    assert named["충전기 1 ESD 후 유량 지속"] == "isolation_failure"
    assert named["PT-0801 데이터 갱신 지연"] == "sensor_fault"
    assert named["충전기 1 호스 급감압"] == "gas_release"
    with TestClient(api.app) as client:
        response = client.get("/api/hazop/emergency-responses")
    assert response.status_code == 200
    linked = response.json()
    assert len(linked["plans"]) == 16
    assert len(linked["rule_mappings"]) == 214
    assert all(row["response_plan_id"] in plans for row in linked["rule_mappings"])


def test_high_consequence_playbooks_link_public_incident_evidence():
    playbooks = load_playbooks()
    assert playbooks["sources"]["HIAD2026"]["url"].startswith("https://minerva.jrc.ec.europa.eu/")
    by_id = {plan["id"]: plan for plan in playbooks["plans"]}
    for plan_id in ("gas_release", "hydrogen_fire", "external_fire", "overpressure",
                    "relief_discharge", "fueling_fault", "hose_connection", "structural_damage"):
        assert "HIAD2026" in by_id[plan_id]["sources"]


def test_fire_selection_uses_actual_event_and_healthy_periodic_is_quiet():
    catalog = load_catalog()
    healthy = {"hazop": {"active": [], "releases": []}, "active_faults": []}
    assert response_selection(healthy, catalog, trigger="periodic") == []
    fire = {**healthy, "active_faults": ["external-fire:cascade.medium"]}
    selected = response_selection(fire, catalog, trigger="alarm")
    assert selected[0]["plan"]["id"] == "external_fire"
    assert "중압 저장뱅크" in selected[0]["evidence"][0]


def test_active_bank_pressure_and_relief_get_distinct_measures():
    frame = {"hazop": {"active": [{"rule_id": "HZ-053", "node_id": "N08"}], "releases": []},
             "relief_valves_open": ["cascade.medium"], "active_faults": []}
    selected = response_selection(frame, load_catalog(), trigger="alarm")
    assert {item["plan"]["id"] for item in selected} == {"overpressure", "relief_discharge"}
    assert any("PT-0801" in evidence for item in selected for evidence in item["evidence"])


def test_saga_alarm_receives_and_displays_specific_actions_when_backend_fails(monkeypatch):
    captured = {}

    def unavailable(prompt):
        captured["prompt"] = prompt
        raise OSError("offline")

    monkeypatch.setattr(api, "_invoke_saga", unavailable)
    job_id = "emergency-plan-test"
    with api._jobs_lock:
        api._jobs[job_id] = {"frames": [{
            "time_s": 8.0, "analysis": {"status": "CRITICAL", "findings": ["중압 저장뱅크 가열"]},
            "active_faults": ["external-fire:cascade.medium"],
            "hazop": {"active": [], "releases": [], "signals": {}},
        }]}
    try:
        with TestClient(api.app) as client:
            response = client.post(f"/api/simulations/{job_id}/saga-analysis", json={"trigger": "alarm"})
        assert response.status_code == 200
        result = response.json()
        answer = result["answer"]
        assert '"external_fire"' not in captured["prompt"]  # public language in the LLM guide
        assert "외부 화재" in captured["prompt"]
        assert "외부 화재의 저장용기" in answer
        assert "**즉시 조치**" in answer
        assert "**안정화 확인**" in answer
        assert "**재가동 전 조건**" in answer
        assert "**예방·안전관리**" in answer
        assert "eiga.eu" in answer
        assert "상황별 긴급대응" not in result["analysis_answer"]
        stages = result["response_guidance"]
        assert stages["actual_alert"] is True
        assert stages["common_steps"]
        assert stages["plans"][0]["title"] == "외부 화재의 저장용기·차량 열 노출"
        assert all(stages["plans"][0][name] for name in
                   ("recognition", "immediate", "stabilize", "restart", "prevention"))
    finally:
        with api._jobs_lock:
            api._jobs.pop(job_id, None)


def test_manual_question_can_get_specific_plan_without_false_active_alarm():
    selected = response_selection({"hazop": {"active": [], "releases": []}}, load_catalog(),
                                  "안전밸브가 열리면 긴급대응은?", trigger="manual")
    assert selected[0]["plan"]["id"] == "relief_discharge"
    assert selected[0]["evidence"] == ["운전자 질의에 따른 가상 상황"]


def test_every_hazop_rule_has_queryable_scenario_specific_stages():
    catalog = load_catalog()
    with sqlite3.connect(DEFAULT_DB) as db:
        assert db.execute("SELECT COUNT(*) FROM response_actions").fetchone()[0] == len(catalog["rules"])
    for rule in catalog["rules"]:
        stages = rule["비상대응_단계"]
        assert rule["대응유형"] == classify_rule(rule)
        assert all(len(stages[key]) >= 3 for key in
                   ("recognition", "immediate", "stabilize", "restart", "prevention"))
        assert rule["sensor_id"] in stages["recognition"][0]
        assert rule["대응근거_출처"]
    with TestClient(api.app) as client:
        rows = client.get("/api/hazop/emergency-responses").json()["rule_mappings"]
    assert len(rows) == len(catalog["rules"])
    assert all(row["response_stages"]["immediate"] for row in rows)


def test_simultaneous_rules_in_same_family_remain_separate_scenarios():
    frame = {"hazop": {"active": [{"rule_id": "HZ-052", "node_id": "N08"},
                                   {"rule_id": "HZ-053", "node_id": "N08"}], "releases": []}}
    selected = response_selection(frame, load_catalog(), trigger="alarm")
    assert {item["plan"]["rule_id"] for item in selected} == {"HZ-052", "HZ-053"}
    assert all(item["plan"]["id"] == "overpressure" for item in selected)
    assert selected[0]["plan"]["recognition"] != selected[1]["plan"]["recognition"]
    compact = prompt_guidance(selected)
    stages = structured_guidance(selected, actual_alert=True)
    assert len(compact) == len(stages["plans"]) == 2
    assert {plan["rule_id"] for plan in stages["plans"]} == {"HZ-052", "HZ-053"}
    assert all(plan["immediate"] and plan["prevention"] for plan in stages["plans"])
