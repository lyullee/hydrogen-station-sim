from __future__ import annotations

from types import SimpleNamespace

from scripts import run_preslhy_blowdown_validation as runner


def test_eligible_model_failure_is_retained_as_failed_case(monkeypatch):
    trace = SimpleNamespace(
        case_id="negative-case",
        nozzle_diameter_mm=2.0,
        initial_pressure_pa=15.0e6,
        source_package="PRE3P1A_KIT_D2_300K_DATA.zip",
        source_member="negative-case.xlsx",
        initial_temperature_k=293.15,
        temperature_substituted=False,
        ambient_pressure_substituted=True,
        pressure_unit_interpretation="explicit_absolute",
    )

    def fail(_trace):
        raise RuntimeError("integration failed")

    monkeypatch.setattr(runner, "evaluate_preslhy_trace", fail)
    record = runner._evaluate_or_retain_failure(trace)

    assert record["joint_primary_screen_pass"] is False
    assert record["pressure_screen_pass"] is False
    assert record["half_time_screen_pass"] is False
    assert record["pressure_group"] == "high"
    assert record["evaluation_error"] == "RuntimeError: integration failed"
