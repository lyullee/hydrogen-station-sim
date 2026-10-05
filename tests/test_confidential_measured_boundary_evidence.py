from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_confidential_boundary_evidence_is_deidentified_and_claim_bounded():
    record = json.loads(
        (ROOT / "research/confidential_measured_boundary_replay_2026_10_06.json")
        .read_text(encoding="utf-8")
    )
    assert record["source_identifiers_published"] is False
    assert record["raw_rows_persisted"] is False
    assert record["provenance_boundary"]["raw_archive_in_repository"] is False
    assert record["controlled_replay"]["trajectory_completed"] is True
    assert record["controlled_replay"]["default_model_parameters_changed"] is False
    assert record["diagnostic_correction"]["safety_trip_relaxed"] is False
    assert record["eligibility"]["independent_full_loop_validation_supported"] is False
    assert record["eligibility"]["prospective_holdout"] is False
    assert "full_loop_external_validation remains open" in record["gate_impact"]
