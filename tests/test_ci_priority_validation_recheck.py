import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_latest_priority_ci_recheck_preserves_scientific_gate_boundary():
    record = json.loads(
        (
            ROOT / "research/ci_priority_validation_recheck_2026_10_14.json"
        ).read_text(encoding="utf-8")
    )
    assert record["branch"] == "main"
    assert record["conclusion"] == "success"
    assert record["software_and_process_reproducibility"] == "PASS"
    assert record["scientific_gate_promotion"] is False
    assert record["scientific_screen_status"] == "FAIL"
    assert record["readiness_status"] == "BLOCKED"
