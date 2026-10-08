from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/confidential_station_cascade_sequence_protocol_2026_10_08.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_cascade_sequence_protocol_is_hash_locked_before_joint_outcomes() -> None:
    record = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert record["status"] == (
        "frozen_before_ordered_joint_medium_high_outcome_access"
    )
    prior = record["prior_information"]
    assert prior["individual_high_pressure_cycle_outcomes_known"] is True
    assert prior["joint_medium_high_pairing_outcomes_known"] is False
    assert record["sequence_rules"]["minimum_holdout_pair_coverage"] == 0.6
    assert record["sequence_rules"]["minimum_holdout_sequential_fraction"] == 0.9
    boundary = record["decision_boundary"]
    assert boundary["vehicle_fill_validation"] is False
    assert boundary["runtime_parameter_application"] is False
    assert boundary["independent_external_validation"] is False
    locked = record["locked_implementation"]
    for name in ("evaluator", "runner", "cycle_detector", "causal_filter"):
        assert _sha256(ROOT / locked[name]) == locked[f"{name}_sha256"]
