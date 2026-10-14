"""Keep the human-readable objective summary synchronized with source evidence.

The summary is used for progress reporting and manuscript scoping.  These checks
are deliberately narrow: they verify that the published numbers are copied from
the frozen evidence artifacts, without treating the summary as a new validation
result.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
SUMMARY = RESEARCH / "OBJECTIVE_EVIDENCE_SUMMARY_2026_10_14.md"


def _load(name: str) -> dict:
    return json.loads((RESEARCH / name).read_text(encoding="utf-8"))


def test_objective_summary_contains_authoritative_progress_and_regression() -> None:
    text = SUMMARY.read_text(encoding="utf-8")
    progress = _load("goal_progress_snapshot_2026_10_14.json")
    regression = _load("full_regression_test_run_2026_10_14.json")

    gates = progress["gate_counts"]
    primary = progress["primary_scope_progress_2026_10_11"]["gate_counts"]
    assert (
        f"{gates['PASS']} PASS / {gates['FAIL']} FAIL / "
        f"{gates['PENDING']} PENDING ({progress['gate_closure_percent']:.1f}%)"
    ) in text
    assert (
        f"{primary['PASS']} PASS / {primary['FAIL']} FAIL / "
        f"{primary['PENDING']} PENDING "
        f"({progress['primary_scope_progress_2026_10_11']['gate_closure_percent']:.1f}%)"
    ) in text
    assert (
        f"{regression['tests_passed']:,} passed / {regression['tests_failed']} failed / "
        f"{regression['tests_skipped']} skipped / {regression['warnings']} warnings"
    ) in text
    assert "station-to-vehicle" in text
    assert "SAGA" in text


def test_objective_summary_contains_frozen_physics_and_station_metrics() -> None:
    text = SUMMARY.read_text(encoding="utf-8")
    tank = _load("tank_model_validation_v2.json")["validation"]
    usn = _load("usn_17934047_ignited_pressure_peaking_result_2026_10_08.json")[
        "aggregate"
    ]
    geometry = _load("consequence_geometry_validation.json")
    station = _load("confidential_station_side_integrated_validation_2026_10_09.json")[
        "checks"
    ]

    assert f"{tank['case_count']}개 validation case" in text
    assert f"{tank['pressure_rmse_mpa']['mean']:.2f} MPa" in text
    assert f"{tank['temperature_rmse_c']['mean']:.2f} °C" in text
    assert (
        f"{tank['soc_rmse_percentage_points']['mean']:.2f} percentage points"
        in text
    )
    assert (
        f"{usn['eligible_case_count']}개 eligible case" in text
        and f"{usn['primary_pass_count']}개가" in text
        and f"{usn['peak_overpressure_mae_kpa']:.3f} kPa" in text
        and f"{usn['median_trace_nrmse_percent']:.2f}%" in text
    )
    assert (
        f"독립 자료군 {geometry['independent_dataset_family_count']}개" in text
        and f"{geometry['upstream_validation']['passed_test_count']} tests / "
        f"{geometry['upstream_validation']['passed_subtest_count']} subtests" in text
    )
    assert (
        f"{station['pressure_boundary']['holdout_duration_s']:,.0f} s" in text
        and f"{station['cascade_sequence']['holdout_pairs']:,} pairs" in text
        and f"{station['recharge_pressure_forecast']['holdout_cases']} cases" in text
        and f"{station['recharge_pressure_forecast']['holdout_mae_mpa']:.3f} MPa" in text
        and f"{station['recharge_pressure_forecast']['holdout_p90_absolute_error_mpa']:.3f} MPa" in text
    )


def test_objective_summary_contains_accident_coverage_counts_and_boundaries() -> None:
    text = SUMMARY.read_text(encoding="utf-8")
    hiad = _load("hiad_accident_response_coverage_evaluation_2026_10_05.json")[
        "aggregate"
    ]
    local = _load("confidential_local_accident_response_coverage_2026_10_06.json")[
        "aggregate"
    ]

    assert (
        f"{hiad['case_count']}건에서 {hiad['category_count']}개 조치 범주" in text
        and f"{hiad['covered_action_category_case_count']}건은 {hiad['covered_action_category_case_count']}건 모두 매핑" in text
        and f"{hiad['executable_case_category_count']}건" in text
    )
    assert (
        f"{local['case_count']}건은 모두 후보 대응계획" in text
        and f"{local['multi_family_case_count']}건은 복수 사고군" in text
    )
    assert "실제 사고에서 어떤 조치가 효과적이었는지" in text
    assert "법정 안전거리" in text
