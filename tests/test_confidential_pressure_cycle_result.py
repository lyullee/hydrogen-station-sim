from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/confidential_station_pressure_cycle_holdout_2026_10_08.json"
PROTOCOL = ROOT / "research/confidential_station_pressure_cycle_protocol_2026_10_08.json"


def test_first_pressure_cycle_holdout_retains_the_frozen_negative_result() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["files_read"] == 12
    assert result["raw_data_rows"] == 29_361_269
    assert result["sampled_rows"] == 2_936_109
    assert result["rejected_sample_rows"] == 21
    assert result["calibration"]["pressure_drop_mpa"]["count"] == 0
    assert result["holdout"]["pressure_drop_mpa"]["count"] == 0
    assert result["decision"][
        "existing_high_bank_restart_margin_cross_format_corroborated"
    ] is False
    assert result["decision"]["runtime_parameter_application"] is False
    assert result["decision"]["default_model_parameters_changed"] is False
    assert result["protocol"]["protocol_frozen_before_cycle_outcome_access"] is True
    assert result["protocol"]["protocol_sha256"] == hashlib.sha256(
        PROTOCOL.read_bytes()
    ).hexdigest()


def test_pressure_cycle_result_is_publicly_privacy_bounded() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["source_identifiers_published"] is False
    assert result["source_paths_published"] is False
    assert result["source_filenames_published"] is False
    assert result["source_headers_published"] is False
    assert result["raw_rows_persisted"] is False
    assert result["absolute_timestamps_published"] is False
    assert result["calendar_dates_published"] is False
    encoded = json.dumps(result, ensure_ascii=False)
    for forbidden in (
        "C:/Users",
        "C:\\\\Users",
        "DocuData",
        "ProjectData",
        "external_hrs_quarantine",
    ):
        assert forbidden not in encoded
