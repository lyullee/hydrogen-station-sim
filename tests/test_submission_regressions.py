from h2station.api import _cooling_evidence, _direct_answer_conflicts_with_signals
from h2station.api import _bank_pressure_evidence, _safe_saga_text


def test_bank_pressure_summary_preserves_identity_and_missing_quality():
    frame = {"hazop": {"signals": {
        "PT-0701": {"value": 45, "unit": "MPa_abs", "quality": "GOOD"},
        "PT-0801": {"value": 65, "unit": "MPa_abs", "quality": "GOOD"},
        "PT-0901": {"value": 90, "unit": "MPa_abs", "quality": "BAD"}}}}
    text = _bank_pressure_evidence(frame, "저장뱅크 압력을 알려줘")
    assert "저압 45.000" in text and "중압 65.000" in text
    assert "고압 (PT-0901): 유효 센서값 미확인" in text
    assert "90.000" not in text
    assert "중압" not in _bank_pressure_evidence(frame, "저압 뱅크 압력")
    assert _bank_pressure_evidence(frame, "차량 압력") == ""


def test_internal_field_names_are_not_operator_prose():
    text = _safe_saga_text("station_status와 current_signals, cooling_feedback를 확인합니다.")
    assert "station_status" not in text
    assert "충전소 상태" in text and "냉각 가동 피드백" in text


def test_normal_sensor_does_not_cancel_fire_explanation():
    assert not _direct_answer_conflicts_with_signals(
        "압력은 정상 범위입니다. 화염 신호가 있어 점검이 필요합니다.", alert=True)
    assert _direct_answer_conflicts_with_signals("현재 공정은 정상 운전입니다.", alert=True)
    assert _direct_answer_conflicts_with_signals(
        "전체는 정상 상태입니다. 온도는 정상 범위가 아닙니다.", alert=True)
    assert not _direct_answer_conflicts_with_signals("현재 정상 상태가 아닙니다.", alert=True)


def test_cooling_evidence_keeps_failed_feedback_and_rising_temperature():
    frame = {"time_s": 55, "bank_temperature_c": {"low": 27},
             "virtual_safety": {"cooling": {
                 "low": {"commanded": True, "running": False, "fault": True}},
                 "actions": [{"kind": "cooling.on", "target": "low", "issued_s": 45,
                              "baseline_metrics": {"bank_temperature_c": {"low": 26}}}]}}
    answer = _cooling_evidence(frame, "저압 저장뱅크 냉각 상태")
    assert "명령 ON, 가동 피드백 OFF, 고장 있음" in answer
    assert "26.000" in answer and "27.000" in answer
    assert _cooling_evidence(frame, "차량 충전 상태") == ""


def test_cooling_without_baseline_does_not_imply_effectiveness():
    frame = {"time_s": 12, "bank_temperature_c": {"low": 25.02},
             "virtual_safety": {"cooling": {"low": {"commanded": True, "running": True}},
                 "actions": [{"kind": "cooling.on", "target": "low", "issued_s": 3,
                              "baseline_metrics": {}}]}}
    assert "판단할 수 없습니다" in _cooling_evidence(frame, "저압 화재 냉각")


def test_retained_alarm_is_not_presented_as_new_hazard():
    from h2station.api import _analyze_frame
    frame={'hazop': {'active': [{'severity':'TRIP','state':'LATCHED'}]}}
    result=_analyze_frame(frame)
    assert result['status']=='ADVISORY'
    assert '경보 이력' in result['headline']
    frame['total_leak_flow_g_s']=1
    assert _analyze_frame(frame)['status']=='CRITICAL'
    frame['total_leak_flow_g_s']=0
    frame['esd']=True
    assert '공정 차단 유지' in _analyze_frame(frame)['headline']
