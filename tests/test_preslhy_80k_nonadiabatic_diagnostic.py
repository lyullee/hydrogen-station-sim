import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_preslhy_80k_candidate_failure_is_retained_without_promotion() -> None:
    record = json.loads(
        (
            ROOT
            / "research/preslhy_80k_nonadiabatic_diagnostic_2026_10_14.json"
        ).read_text(encoding="utf-8")
    )

    assert record["artifact_type"] == "preslhy_80k_nonadiabatic_development_diagnostic"
    assert record["aggregate"] == {
        "case_count": 11,
        "joint_primary_passes": 3,
        "joint_primary_pass_fraction": 3 / 11,
        "nozzle_diameter_groups": [0.5, 2.0],
    }
    assert record["claim_supported"] is False
    assert record["runtime_parameter_application"] is False
    assert record["prospective_validation"] is False
    assert "negative result is retained" in record["claim_boundary"]

