from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/confidential_station_ordered_pressure_cycle_protocol_2026_10_08.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_ordered_protocol_is_locked_before_ordered_cycle_outcome_access() -> None:
    record = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert record["status"] == (
        "chronology_correction_frozen_before_ordered_cycle_outcome_access"
    )
    assert record["disclosure"].startswith("The first two methods returned zero cycles")
    assert record["target"]["candidate_mpa"] == 4.5
    assert record["target"]["candidate_changed_after_prior_results"] is False
    assert record["primary_screens"][
        "candidate_relative_holdout_median_error_percent_max"
    ] == 20.0
    assert record["decision_boundary"]["runtime_parameter_application"] is False
    assert record["decision_boundary"]["independent_external_validation"] is False
    locked = record["locked_implementation"]
    for name in ("evaluator", "runner", "filter_revision", "base_detector"):
        assert _sha256(ROOT / locked[name]) == locked[f"{name}_sha256"]
