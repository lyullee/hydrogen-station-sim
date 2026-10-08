from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/confidential_station_pressure_cycle_protocol_2026_10_08.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pressure_cycle_protocol_is_locked_before_private_outcome_access() -> None:
    record = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert record["status"] == (
        "method_and_thresholds_frozen_before_pressure_cycle_outcome_access"
    )
    assert record["target"]["candidate_mpa"] == 4.5
    assert record["primary_screens"][
        "candidate_relative_holdout_median_error_percent_max"
    ] == 20.0
    assert record["decision_boundary"]["runtime_parameter_application"] is False
    assert record["decision_boundary"]["vehicle_fill_or_full_loop_validation"] is False
    locked = record["locked_implementation"]
    assert _sha256(ROOT / locked["evaluator"]) == locked["evaluator_sha256"]
    assert _sha256(ROOT / locked["runner"]) == locked["runner_sha256"]
