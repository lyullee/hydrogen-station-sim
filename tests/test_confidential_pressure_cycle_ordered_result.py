from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/confidential_station_ordered_pressure_cycle_holdout_2026_10_08.json"
PROTOCOL = ROOT / "research/confidential_station_ordered_pressure_cycle_protocol_2026_10_08.json"


def test_ordered_result_retains_outcome_and_protocol_provenance() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["runner_git_commit"] == "1a0f15b"
    assert result["files_read"] == 12
    assert result["reverse_chronological_files"] == 12
    assert result["mixed_order_files"] == 0
    assert result["calibration"]["pressure_drop_mpa"]["count"] == 11_565
    assert result["holdout"]["pressure_drop_mpa"]["count"] == 5_205
    assert result["holdout"]["pressure_drop_mpa"]["median"] == 4.6378
    assert result["metrics"][
        "candidate_relative_holdout_median_error_percent"
    ] == 2.971236
    assert result["metrics"][
        "calibration_holdout_median_shift_percent"
    ] == 1.010585
    assert all(result["eligibility"].values())
    assert all(result["screens"].values())
    assert result["decision"][
        "existing_high_bank_restart_margin_cross_format_corroborated"
    ] is True
    assert result["decision"]["independent_external_validation"] is False
    assert result["decision"]["runtime_parameter_application"] is False
    assert result["protocol"]["protocol_sha256"] == hashlib.sha256(
        PROTOCOL.read_bytes()
    ).hexdigest()


def test_ordered_result_has_no_source_identity_fields() -> None:
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
    encoded = json.dumps(result, ensure_ascii=False)
    assert re.search(r"[A-Za-z]:\\\\", encoded) is None
