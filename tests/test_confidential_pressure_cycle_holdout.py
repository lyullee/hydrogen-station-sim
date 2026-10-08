from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from h2station.confidential_history_profile import header_fingerprint
from h2station.confidential_pressure_cycle_holdout import (
    PressureCycleRules,
    detect_pressure_cycles,
    evaluate_confidential_pressure_cycle_holdout,
)


def test_cycle_detector_retains_completed_fall_and_recovery() -> None:
    samples = [
        (0.0, 85.0),
        (30.0, 84.8),
        (60.0, 82.0),
        (90.0, 80.5),
        (120.0, 80.8),
    ]
    cycles = detect_pressure_cycles(samples)
    assert len(cycles) == 1
    assert cycles[0].pressure_drop_mpa == pytest.approx(4.5)
    assert cycles[0].decline_duration_s == pytest.approx(90.0)


def test_cycle_holdout_is_privacy_bounded_and_requires_attestation(tmp_path: Path) -> None:
    header = [f"private_{index}" for index in range(9)]
    start = datetime(2024, 1, 1)
    for file_index in range(6):
        path = tmp_path / f"secret_{file_index}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerow(["unit"] * 9)
            for index in range(800):
                phase = index % 80
                high = 85.0 - min(phase, 60) * 4.5 / 60.0
                if phase > 60:
                    high = 80.5 + (phase - 60) * 4.5 / 19.0
                writer.writerow([
                    (start + timedelta(seconds=index)).strftime("%Y-%m-%d %H:%M:%S"),
                    index,
                    0.0,
                    index,
                    0.0,
                    20.0,
                    45.0,
                    65.0,
                    high,
                ])
    mapping = {
        "schemas": [{
            "schema_id": "pressure_flow_candidate",
            "header_fingerprint": header_fingerprint(header),
            "timestamp_index": 0,
            "skip_rows_after_header": 1,
            "numeric_channels": [{"role": "high_storage_pressure", "index": 8}],
        }],
        "attestation": {"medium_high_pressure_roles_attested_elsewhere": True},
    }
    rules = PressureCycleRules(sample_stride=1, calibration_fraction=0.70)
    result = evaluate_confidential_pressure_cycle_holdout(
        tmp_path, mapping, rules=rules
    )
    assert result["files_read"] == 6
    assert result["raw_data_rows"] == 4800
    assert result["calibration"]["pressure_drop_mpa"]["count"] >= 30
    assert result["holdout"]["pressure_drop_mpa"]["count"] >= 15
    assert result["decision"][
        "existing_high_bank_restart_margin_cross_format_corroborated"
    ] is True
    assert result["decision"]["runtime_parameter_application"] is False
    encoded = str(result)
    assert "secret_" not in encoded
    assert "private_" not in encoded
    assert str(tmp_path) not in encoded

    mapping["attestation"]["medium_high_pressure_roles_attested_elsewhere"] = False
    with pytest.raises(ValueError, match="attestation"):
        evaluate_confidential_pressure_cycle_holdout(tmp_path, mapping, rules=rules)
