from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/confidential_station_filtered_pressure_cycle_holdout_2026_10_08.json"
PROTOCOL = ROOT / "research/confidential_station_filtered_pressure_cycle_protocol_2026_10_08.json"


def test_filtered_revision_retains_failure_and_reverse_order_diagnosis() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["files_read"] == 12
    assert result["raw_data_rows"] == 29_361_269
    assert result["calibration"]["pressure_drop_mpa"]["count"] == 0
    assert result["holdout"]["pressure_drop_mpa"]["count"] == 0
    assert result["decision"][
        "existing_high_bank_restart_margin_cross_format_corroborated"
    ] is False
    assert result["decision"]["runtime_parameter_application"] is False
    diagnosis = result["post_outcome_order_diagnostic"]
    assert diagnosis["reverse_chronological_files"] == 12
    assert diagnosis["median_absolute_sample_period_s"] == 10.0
    assert result["protocol"]["protocol_sha256"] == hashlib.sha256(
        PROTOCOL.read_bytes()
    ).hexdigest()


def test_filtered_result_has_no_source_identity_fields() -> None:
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
