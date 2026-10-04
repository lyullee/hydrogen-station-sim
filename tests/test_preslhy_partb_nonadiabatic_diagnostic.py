from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_partb_nonadiabatic_diagnostic_preserves_negative_claim_boundary():
    record = json.loads(
        (ROOT / "research/preslhy_partb_nonadiabatic_diagnostic_2026_10_05.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["status"] == "POST_OUTCOME_DEVELOPMENT_DIAGNOSTIC_ONLY"
    assert record["protocol"]["outcomes_were_already_accessed"] is True
    assert record["diagnostic_result"]["joint_primary_passes"] == 3
    assert record["baseline_frozen_result"]["joint_primary_passes"] == 3
    assert record["diagnostic_result"]["cases"][0]["half_time_error_percent"] > 20.0
    assert record["interpretation"]["claim_boundary"]
