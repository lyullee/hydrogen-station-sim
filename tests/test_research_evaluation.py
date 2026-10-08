import numpy as np

from h2station.protocol import FuelingSchedule
from h2station.research_evaluation import (
    DecisionSupportRubric,
    audit_fueling_protocol,
    score_decision_support,
)


def test_protocol_audit_reports_schedule_tracking_and_safety_margins():
    schedule = FuelingSchedule(
        target_pressure_pa=70e6,
        average_pressure_ramp_rate_pa_s=0.2e6,
        delivery_temperature_k=233.15,
        maximum_mass_flow_kg_s=0.06,
    )
    time = np.arange(0.0, 326.0, 1.0)
    reference = np.minimum(70e6, 5e6 + 0.2e6 * time)
    pressure = reference - 0.05e6
    pressure[-1] = 70e6
    result = audit_fueling_protocol(
        case_id="PT-03",
        schedule=schedule,
        time_s=time,
        pressure_pa=pressure,
        reference_pressure_pa=reference,
        gas_temperature_k=np.linspace(298.15, 345.15, len(time)),
        mass_flow_kg_s=np.full(len(time), 0.04),
        soc=np.linspace(0.1, 0.96, len(time)),
        completion_reason="target-pressure",
    )
    assert result.protocol_boundary_pass
    assert result.safety_envelope_pass
    assert result.completion_pass
    assert not result.soc_target_pass
    assert result.aprr_error_percent < 1.0
    assert result.temperature_margin_c > 0
    assert "not SAE J2601 certification" in result.scope


def test_protocol_audit_fails_temperature_and_incomplete_fill():
    schedule = FuelingSchedule(70e6, 0.2e6, 233.15, 0.06)
    result = audit_fueling_protocol(
        case_id="PT-FAIL",
        schedule=schedule,
        time_s=[0, 1, 2],
        pressure_pa=[5e6, 5.1e6, 5.2e6],
        reference_pressure_pa=[5e6, 5.2e6, 5.4e6],
        gas_temperature_k=[298.15, 359.15, 360.15],
        mass_flow_kg_s=[0.01, 0.01, 0.0],
        soc=[0.1, 0.11, 0.12],
        completion_reason="gas-temperature-limit",
    )
    assert not result.protocol_boundary_pass
    assert "gas-temperature-limit" in result.failures
    assert "completion" in result.failures


def test_llm_linkage_score_rewards_grounded_ordered_response():
    rubric = DecisionSupportRubric(
        case_id="DS-01",
        situation_concepts=(("수소 누출", "가스 농도 상승"),),
        ordered_action_concepts=(
            ("충전 중지", "공급 중지"),
            ("상류 차단", "유입 차단"),
            ("인원 대피", "출입 통제"),
        ),
        prevention_concepts=(("기밀시험", "누설시험"),),
        impact_concepts=(("5.5 m", "5.5m"),),
    )
    evidence = "GD-0901 2.0 vol%_H2, 영향거리 5.5 m. 충전 중지, 상류 차단, 인원 대피, 기밀시험"
    baseline = score_decision_support(
        answer="GD-0901에서 수소 누출 경보가 발생했습니다.",
        allowed_evidence=evidence,
        rubric=rubric,
        variant="alarm-only",
    )
    linked = score_decision_support(
        answer=("수소 누출입니다. 먼저 충전 중지, 다음으로 상류 차단 후 인원 대피를 시행하세요. "
                "계산 영향거리 5.5 m를 통제하고 복구 전 기밀시험을 실시하세요."),
        allowed_evidence=evidence,
        rubric=rubric,
        variant="saga-linked",
    )
    assert linked.score > baseline.score
    assert linked.action_coverage == 1.0
    assert linked.action_order == 1.0
    assert linked.unsupported_numeric_claims == ()


def test_llm_linkage_score_penalizes_unsupported_numeric_claims():
    rubric = DecisionSupportRubric(
        case_id="DS-02",
        situation_concepts=(("과압",),),
        ordered_action_concepts=(("충전 중지",),),
    )
    result = score_decision_support(
        answer="과압이므로 120 MPa에서 충전 중지하세요.",
        allowed_evidence="현재 압력 98 MPa",
        rubric=rubric,
        variant="saga-linked",
    )
    assert result.unsupported_numeric_claims == ("120mpa",)
    assert result.score < 100


def test_korean_action_particles_do_not_hide_ordered_overheat_response():
    rubric = DecisionSupportRubric(
        case_id="DS-OVERHEAT-KO",
        situation_concepts=(("과열", "온도 경보"),),
        ordered_action_concepts=(
            ("충전 정지", "충전을 정지", "충전 중단"),
            ("밸브 차단", "밸브를 차단"),
            ("안정화 확인", "안정화되", "안정화된"),
            ("재가동 승인", "재가동이 승인", "재가동 전"),
        ),
        prevention_concepts=(("프리쿨러",), ("온도센서", "온도 센서")),
    )
    answer = (
        "차량 탱크 과열입니다. 즉시 충전을 정지하고 충전밸브 차단을 확인합니다. "
        "온도와 압력이 안정화되었는지 확인하고, 재가동 전 프리쿨러와 온도센서 기능시험을 완료합니다."
    )
    result = score_decision_support(
        answer=answer,
        allowed_evidence=answer,
        rubric=rubric,
        variant="saga-linked",
    )
    assert result.action_coverage == 1.0
    assert result.action_order == 1.0
    assert result.score == 100.0
