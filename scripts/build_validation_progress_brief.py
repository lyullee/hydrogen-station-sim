"""Build a privacy-safe, claim-bounded validation progress brief.

The repository contains several evidence classes with deliberately different
claim boundaries.  This report keeps the useful station-side/component results
visible while making the remaining station-to-vehicle and safety gates explicit.
It contains aggregate metrics and artifact references only; raw rows, source
paths, tags, site names and absolute timestamps are never copied.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _number(value: Any, digits: int = 3) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "기록 없음"
    return f"{value:,.{digits}f}" if isinstance(value, float) else f"{value:,}"


def build_brief(
    coverage: dict[str, Any],
    readiness: dict[str, Any],
    local_screen: dict[str, Any],
) -> str:
    counts = coverage.get("readiness", {}).get("ijhe_gate_counts", {})
    actionable = coverage.get("validated_or_actionable_now", [])
    station = next(
        (item for item in actionable if item.get("id") == "owner_station_side_dynamics"),
        {},
    )
    station_cov = station.get("coverage", {})
    station_holdout = next(
        (
            item
            for item in actionable
            if item.get("id") == "owner_station_side_integrated_validation"
        ),
        {},
    )
    station_holdout_cov = station_holdout.get("coverage", {})
    tank = next(
        (item for item in actionable if item.get("id") == "public_type_iv_tank"),
        {},
    )
    nrel = next(
        (item for item in actionable if item.get("id") == "public_station_tank_boundary"),
        {},
    )
    nrel_cov = nrel.get("coverage", {})
    full_loop = local_screen.get("coverage_assessment", {})
    minimum = coverage.get("minimum_next_input", {})

    holdout_result = Path("data/public_validation/results/closed_loop_external_holdout/validation.json")
    holdout = _read(holdout_result)
    holdout_aggregate = holdout.get("aggregate", {})
    holdout_metrics = holdout_aggregate.get("metrics", {})

    lines = [
        "# 검증 진행 브리프 (privacy-safe)",
        "",
        "> 이 문서는 현재 저장소에 있는 근거를 주장 범위별로 정리한 상태판입니다. "
        "원자료 행, 태그, 경로, 사업장·제조사·정확한 날짜는 포함하지 않습니다.",
        "",
        "## 현재 판정",
        "",
        f"- IJHE 내부 게이트: **PASS {_number(counts.get('PASS'), 0)} / "
        f"FAIL {_number(counts.get('FAIL'), 0)} / PENDING {_number(counts.get('PENDING'), 0)}**.",
        f"- 제한된 투고 준비: **{'가능' if readiness.get('bounded_ijhe_submission_ready') else '아직 불가'}**.",
        f"- 사용자 목표(독립 full-loop 포함): **{'달성' if readiness.get('full_user_objective_ready') else '아직 미달'}**.",
        "",
        "## 지금 바로 사용할 수 있는 근거",
        "",
        f"- 비식별 station-side 원자료: {_number(station_cov.get('deduplicated_rows'), 0)}개 행, "
        f"고압 압력 사이클 {_number(station_cov.get('ordered_high_bank_pressure_cycles'), 0)}건, "
        f"중·고압 연계 {_number(station_cov.get('paired_medium_high_pressure_episodes'), 0)}건, "
        f"재충전 압력 예측 {_number(station_cov.get('short_horizon_pressure_forecast_cases'), 0)}건. "
        "압력·cascade·재충전 동역학 진단에 사용합니다.",
        f"- 같은 자료의 시간순 holdout: 압력 경계 {_number(station_holdout_cov.get('pressure_boundary_holdout_points'), 0)}점, "
        f"cascade {_number(station_holdout_cov.get('cascade_sequence_holdout_pairs'), 0)}쌍, "
        f"재충전 예측 {_number(station_holdout_cov.get('recharge_pressure_forecast_holdout_cases'), 0)}건. "
        "차량 충전 정확도나 현장 안전한계로 확대하지 않습니다.",
        f"- 공개 Type-IV 탱크 경계 검증: {_number(tank.get('coverage', {}).get('validation_case_count'), 0)}건, "
        "탱크 경계 구성요소 검증으로 유지합니다.",
        "- 사고 전례·대응 플레이북·가상 조치 실행은 시나리오와 단계별 대응 근거로 사용하며, "
        "사고 빈도나 현장 대응 효과를 추정하지 않습니다.",
        "",
        "## 실패 또는 제한된 결과도 그대로 유지",
        "",
        f"- 공개 MC Default full-loop holdout: {_number(holdout_aggregate.get('screening_pass_count'), 0)} / "
        f"{_number(holdout_aggregate.get('case_count'), 0)} 통과. "
        f"평균 압력 RMSE {_number(holdout_metrics.get('pressure_rmse_mpa', {}).get('mean'))} MPa, "
        f"온도 RMSE {_number(holdout_metrics.get('temperature_rmse_c', {}).get('mean'))} °C, "
        f"SOC RMSE {_number(holdout_metrics.get('soc_rmse_percentage_points', {}).get('mean'))}%p. "
        "이 결과는 숨기거나 재평가로 대체하지 않습니다.",
        f"- NREL 탱크 경계 자료: 압력 RMSE {_number(nrel_cov.get('pressure_rmse_mpa'))} MPa로 "
        "현재 스크리닝을 통과하지 못해 진단용으로만 유지합니다.",
        f"- 새 full-loop 측정 코호트: **{'확인됨' if full_loop.get('new_full_loop_measured_cohort_found') else '확인되지 않음'}**. "
        "현재 주된 공백은 동기화된 차량·수용용기 측 채널입니다.",
        "",
        "## 추가 자료 없이 진행 가능한 작업",
        "",
        "1. station-side 압력·cascade·재충전 모델과 시간순 holdout을 논문용 방법·결과로 정리합니다.",
        "2. 공개 탱크·방출·검지·사고 자료는 구성요소 진단과 LLM 근거 연결에 사용합니다.",
        "3. full-loop가 아닌 범위로 안전 시나리오, 단계별 대응, 가상 밸브·ESD 조치의 실행 가능성을 평가합니다.",
        "4. 결과 화면과 LLM은 위 주장 경계를 자동 표시해 station-side 결과가 차량 full-loop 검증처럼 보이지 않게 합니다.",
        "",
        "## full-loop 게이트를 닫기 위한 최소 입력",
        "",
        f"- 비식별 이벤트 **{_number(minimum.get('event_count'), 0)}건 이상**.",
        "- 공통 경과시간, station/디스펜서 압력, 공급가스 또는 경계 온도, 질량유량/이송질량, "
        "프로토콜 시작·종료 상태.",
        "- 가능하면 차량·수용용기 압력·온도, cascade 선택 상태, precooler 출구온도, ESD·fault 전이.",
        "- 단위·초기조건·센서 품질·동기화·재사용 권한에 대한 관리자 확인. 원자료 자체를 저장소에 올릴 필요는 없습니다.",
        "",
        "## 근거 파일",
        "",
        "- `research/data_coverage_summary_2026_10_10.json`",
        "- `research/ijhe_readiness_audit.json`",
        "- `research/local_candidate_full_loop_screen_2026_10_09.json`",
        "- `data/public_validation/results/closed_loop_external_holdout/validation.json`",
        "",
        "이 브리프는 모델이나 검증 게이트를 변경하지 않습니다. 새로운 자료가 들어오면 동일한 동결·시간축·권한 검사를 거친 뒤 다시 생성합니다.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--coverage",
        type=Path,
        default=Path("research/data_coverage_summary_2026_10_10.json"),
    )
    parser.add_argument(
        "--readiness",
        type=Path,
        default=Path("research/ijhe_readiness_audit.json"),
    )
    parser.add_argument(
        "--local-screen",
        type=Path,
        default=Path("research/local_candidate_full_loop_screen_2026_10_09.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/VALIDATION_PROGRESS_BRIEF_2026_10_10.md"),
    )
    args = parser.parse_args()
    report = build_brief(
        _read(args.coverage), _read(args.readiness), _read(args.local_screen)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
