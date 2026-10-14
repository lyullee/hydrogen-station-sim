from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_local_usn_archive_is_recorded_as_a_duplicate_only() -> None:
    artifact = json.loads(
        (
            ROOT
            / "research/ftpdata_usn_26117989_duplicate_recheck_2026_10_14.json"
        ).read_text(encoding="utf-8")
    )

    assert artifact["source"]["dataset_doi"] == "10.23642/usn.26117989.v2"
    assert artifact["source"]["archive_count"] == 22
    comparison = artifact["comparison"]
    assert comparison["matched_archives"] == 22
    assert comparison["missing_archives"] == []
    assert comparison["mismatched_archives"] == []
    classification = artifact["evidence_classification"]
    assert classification["new_independent_dataset"] is False
    assert classification["post_access_duplicate_check"] is True
    assert classification["readiness_gate_effect"] is False

