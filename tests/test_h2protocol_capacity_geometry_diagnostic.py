import json
from pathlib import Path

from scripts.run_h2protocol_capacity_geometry_diagnostic import capacity_eos_volume_m3


ROOT = Path(__file__).resolve().parents[1]


def test_capacity_geometry_diagnostic_is_explicitly_non_confirmatory():
    report = json.loads(
        (
            ROOT
            / "research/h2protocol_capacity_geometry_diagnostic_2026_10_05.json"
        ).read_text(encoding="utf-8")
    )
    assert report["status"] == "diagnostic_capacity_geometry_sensitivity_only"
    assert report["aggregate"]["case_count"] == 36
    assert report["aggregate"]["screening_pass_count"] == 6
    assert "cannot close any IJHE gate" in report["claim_limit"]


def test_capacity_eos_volume_is_positive_and_uses_nominal_pressure():
    low = capacity_eos_volume_m3(4.7, 35.0)
    high = capacity_eos_volume_m3(4.7, 70.0)
    assert low > 0.0
    assert high > 0.0
    assert low != high

