from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/confidential_station_lifecycle_pressure_alignment_protocol_2026_10_08.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_lifecycle_pressure_protocol_is_prospective_and_hash_locked() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["protocol_id"] == "CONFIDENTIAL-STATION-LIFECYCLE-PRESSURE-ALIGNMENT-001"
    assert protocol["joint_alignment_outcomes_seen_before_freeze"] is False
    assert protocol["split"]["calibration_fraction"] == 0.7
    assert protocol["event_definition"]["exact_duplicate_files_excluded"] is True
    assert protocol["decision_boundary"]["vehicle_fill_validation"] is False
    assert protocol["decision_boundary"]["runtime_parameter_application"] is False
    locked = protocol["locked_implementation"]
    for file_key, hash_key in (
        ("evaluator", "evaluator_sha256"),
        ("runner", "runner_sha256"),
        ("synthetic_regression_test", "synthetic_regression_test_sha256"),
    ):
        assert _sha256(ROOT / locked[file_key]) == locked[hash_key]
