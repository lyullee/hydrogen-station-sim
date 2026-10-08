from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

from h2station.confidential_cascade_sequence_holdout import (
    CascadeSequenceRules,
    evaluate_confidential_cascade_sequence_holdout,
)
from h2station.confidential_history_profile import header_fingerprint
from h2station.confidential_pressure_cycle_holdout import PressureCycleRules


def _pressures(second: int) -> tuple[float, float]:
    phase = second % 240
    medium = 65.0
    high = 85.0
    if 30 <= phase < 90:
        medium -= (phase - 30) * 3.0 / 60.0
    elif 90 <= phase < 110:
        medium = 62.0 + (phase - 90) * 3.0 / 20.0
    if 100 <= phase < 160:
        high -= (phase - 100) * 4.5 / 60.0
    elif 160 <= phase < 180:
        high = 80.5 + (phase - 160) * 4.5 / 20.0
    return medium, high


def test_reverse_ordered_medium_high_sequence_passes_frozen_synthetic_case(
    tmp_path: Path,
) -> None:
    header = [f"private_{index}" for index in range(9)]
    start = datetime(2024, 1, 1)
    for file_index in range(6):
        rows = []
        for second in range(20 * 240):
            medium, high = _pressures(second)
            rows.append([
                (start + timedelta(days=file_index, seconds=second)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                second,
                0.0,
                second,
                0.0,
                45.0,
                48.0,
                medium,
                high,
            ])
        with (tmp_path / f"synthetic_{file_index}.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerow(["unit"] * 9)
            writer.writerows(reversed(rows))
    mapping = {
        "schemas": [{
            "schema_id": "pressure_flow_candidate",
            "header_fingerprint": header_fingerprint(header),
            "timestamp_index": 0,
            "skip_rows_after_header": 1,
            "numeric_channels": [
                {"role": "medium_storage_pressure", "index": 7},
                {"role": "high_storage_pressure", "index": 8},
            ],
        }],
        "attestation": {"medium_high_pressure_roles_attested_elsewhere": True},
    }
    result = evaluate_confidential_cascade_sequence_holdout(
        tmp_path,
        mapping,
        cycle_rules=PressureCycleRules(sample_stride=1),
        sequence_rules=CascadeSequenceRules(
            minimum_calibration_pairs=60,
            minimum_holdout_pairs=24,
        ),
    )
    assert result["reverse_chronological_files"] == 6
    assert result["mixed_order_files"] == 0
    assert result["calibration"]["paired_episode_count"] >= 60
    assert result["holdout"]["paired_episode_count"] >= 24
    assert result["holdout"]["sequential_fraction"] == 1.0
    assert all(result["eligibility"].values())
    assert all(result["screens"].values())
    assert result["decision"]["cascade_controller_structure_supported"] is True
    assert result["decision"]["runtime_parameter_application"] is False


def test_sequence_requires_attested_roles(tmp_path: Path) -> None:
    mapping = {
        "schemas": [],
        "attestation": {"medium_high_pressure_roles_attested_elsewhere": False},
    }
    try:
        evaluate_confidential_cascade_sequence_holdout(tmp_path, mapping)
    except ValueError as exc:
        assert "attestation" in str(exc)
    else:
        raise AssertionError("missing role attestation must be rejected")
