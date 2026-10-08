from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/confidential_station_cascade_sequence_holdout_2026_10_08.json"
PROTOCOL = ROOT / "research/confidential_station_cascade_sequence_protocol_2026_10_08.json"


def test_cascade_sequence_result_retains_frozen_positive_outcome() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["runner_git_commit"] == "e8f9655"
    assert result["files_read"] == 12
    assert result["reverse_chronological_files"] == 12
    assert result["mixed_order_files"] == 0
    assert result["calibration"]["paired_episode_count"] == 8_106
    assert result["holdout"]["paired_episode_count"] == 3_664
    assert result["holdout"]["pair_coverage_fraction"] == 0.703939
    assert result["holdout"]["sequential_fraction"] == 0.943777
    assert result["holdout"]["handoff_gap_s"]["median"] == 80.0
    assert all(result["eligibility"].values())
    assert all(result["screens"].values())
    decision = result["decision"]
    assert decision["cascade_controller_structure_supported"] is True
    assert decision["vehicle_fill_validation"] is False
    assert decision["full_loop_holdout_eligible"] is False
    assert decision["runtime_parameter_application"] is False
    assert result["protocol"]["protocol_sha256"] == hashlib.sha256(
        PROTOCOL.read_bytes()
    ).hexdigest()


def test_cascade_sequence_result_has_no_private_source_surface() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    for key in (
        "source_identifiers_published",
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "raw_rows_persisted",
        "absolute_timestamps_published",
        "calendar_dates_published",
    ):
        assert result[key] is False
    assert re.search(r"[A-Za-z]:\\\\", json.dumps(result, ensure_ascii=False)) is None
