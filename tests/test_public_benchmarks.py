from pathlib import Path

from h2station.public_benchmarks import (
    ARTIFACT_RELATIVE_PATH,
    compare_public_high_flow_benchmark,
    load_public_benchmark,
)


ROOT = Path(__file__).resolve().parents[1]


def test_public_h2iq_benchmark_is_provenance_checked_and_loads() -> None:
    benchmark = load_public_benchmark(ROOT)
    assert benchmark is not None
    assert benchmark.benchmark_id == "NREL_HD_FAST_FLOW_2024_REPORT"
    assert benchmark.aggregate["peak_mass_flow_g_s"] == 483.33


def test_public_benchmark_comparison_is_diagnostic_only() -> None:
    result = compare_public_high_flow_benchmark(
        duration_s=423.5,
        start_pressure_mpa=5.5,
        end_pressure_mpa=74.6,
        maximum_flow_g_s=483.33,
        benchmark=load_public_benchmark(ROOT),
    )
    assert result["status"] == "operating_range_context"
    assert result["artifact"] == ARTIFACT_RELATIVE_PATH
    assert result["runtime_parameter_application"] is False
    assert result["full_loop_holdout_eligible"] is False
    assert result["metrics"]["aprr_mpa_min"]["simulated"] == 9.789846517119242


def test_public_benchmark_is_unavailable_without_source() -> None:
    result = compare_public_high_flow_benchmark(
        duration_s=10.0,
        start_pressure_mpa=5.0,
        end_pressure_mpa=10.0,
        maximum_flow_g_s=20.0,
        benchmark=None,
    )
    assert result["status"] == "unavailable"
    assert result["runtime_parameter_application"] is False
