from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/runtime_qra_envelope_comparison_2026_10_08.json"


def test_runtime_qra_comparison_keeps_diagnostic_boundary() -> None:
    payload = json.loads(RESULT.read_text(encoding="utf-8"))

    assert payload["source"]["doi"] == "10.34810/DATA3632"
    assert payload["aggregate"]["case_count"] == 4
    assert payload["model_action"].startswith("No automatic calibration")
    assert "not experimental validation" in payload["claim_boundary"]
    assert {case["equipment"] for case in payload["cases"]} == {
        "Supply", "Compressor", "Buffer", "Dispenser"
    }


def test_runtime_qra_comparison_reports_separate_effect_radii() -> None:
    payload = json.loads(RESULT.read_text(encoding="utf-8"))

    for case in payload["cases"]:
        runtime = case["runtime"]
        assert runtime["thermal_radius_5_kw_m2_m"] >= 0.0
        assert runtime["overpressure_radius_5_kpa_m"] >= 0.0
        assert runtime["combined_radius_m"] == max(
            runtime["thermal_radius_5_kw_m2_m"],
            runtime["overpressure_radius_5_kpa_m"],
        )
