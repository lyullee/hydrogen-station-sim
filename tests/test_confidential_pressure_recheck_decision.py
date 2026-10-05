from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pressure_recheck_decision_keeps_runtime_profile_bounded():
    record = json.loads(
        (ROOT / "research/confidential_pressure_recheck_decision_2026_10_06.json")
        .read_text(encoding="utf-8")
    )
    assert record["source_identifiers_published"] is False
    assert record["raw_rows_persisted"] is False
    assert record["decision"]["candidate_applied_to_runtime"] is False
    assert record["decision"]["retained_restart_margin_mpa"] == 0.54
    assert "nonpositive_pressure_excluded" in record["recheck"]["quality_warnings"]
    assert "sparse_sampling_gap" in record["recheck"]["quality_warnings"]
