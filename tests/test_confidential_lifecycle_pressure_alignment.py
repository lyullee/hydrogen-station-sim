from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from h2station.confidential_history_profile import header_fingerprint
from h2station.confidential_lifecycle_pressure_alignment import (
    LifecyclePressureAlignmentRules,
    evaluate_lifecycle_pressure_alignment,
)


PRESSURE_HEADER = ["clock", "unused", "medium_p", "high_p"]
COUNTER_HEADER = ["utc", "local", "high_counter", "medium_counter"]


def _pressure(t: int, full: float) -> float:
    phase = t % 100
    if phase < 40:
        return full - 2.0
    if phase <= 50:
        return full - 2.0 + 0.2 * (phase - 40)
    if phase <= 60:
        return full
    return full - 2.0


def _counter(t: int) -> int:
    return sum(t >= crossing for crossing in (48, 148, 248, 348))


def _write_reverse_logs(root: Path) -> None:
    pressure = root / "private-pressure.csv"
    with pressure.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(PRESSURE_HEADER)
        for t in range(399, -1, -1):
            writer.writerow([t, 0, _pressure(t, 45.0), _pressure(t, 85.0)])
    counter = root / "private-counter.csv"
    with counter.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(COUNTER_HEADER)
        for t in range(399, -1, -1):
            value = _counter(t)
            writer.writerow([t, t, value, value])
    (root / "private-counter-copy.csv").write_bytes(counter.read_bytes())


def _mapping() -> dict[str, object]:
    return {
        "schemas": [
            {
                "schema_id": "pressure_flow_candidate",
                "header_fingerprint": header_fingerprint(PRESSURE_HEADER),
                "timestamp_index": 0,
                "skip_rows_after_header": 0,
                "numeric_channels": [
                    {"role": "medium_storage_pressure", "index": 2},
                    {"role": "high_storage_pressure", "index": 3},
                ],
            },
            {
                "schema_id": "lifecycle_counter_candidate",
                "header_fingerprint": header_fingerprint(COUNTER_HEADER),
                "timestamp_index": 1,
                "skip_rows_after_header": 0,
                "numeric_channels": [
                    {"role": "high_bank_full_recharge_counter", "index": 2},
                    {"role": "medium_bank_full_recharge_counter", "index": 3},
                ],
            },
        ],
        "attestation": {
            "medium_high_pressure_roles_attested_elsewhere": True,
            "lifecycle_counter_roles_attested_elsewhere": True,
            "full_recharge_thresholds_attested": True,
            "local_clock_alignment_attested": True,
        },
    }


def _rules() -> LifecyclePressureAlignmentRules:
    return LifecyclePressureAlignmentRules(
        maximum_match_offset_s=20.0,
        minimum_pressure_files=1,
        minimum_counter_files=1,
        minimum_calibration_counter_events_per_bank=2,
        minimum_holdout_counter_events_per_bank=1,
        minimum_holdout_counter_recall=0.8,
        minimum_holdout_pressure_precision=0.8,
        maximum_recall_shift=0.1,
        maximum_holdout_median_absolute_offset_s=10.0,
    )


def test_reverse_chronological_alignment_is_deduplicated_and_passes(tmp_path: Path) -> None:
    _write_reverse_logs(tmp_path)

    result = evaluate_lifecycle_pressure_alignment(
        tmp_path, _mapping(), rules=_rules()
    )

    assert result["files"] == {
        "pressure_files_read": 1,
        "counter_files_read": 1,
        "exact_duplicate_files_excluded": 1,
    }
    assert result["calibration"]["combined"]["counter_increment_event_count"] == 6
    assert result["holdout"]["combined"]["counter_increment_event_count"] == 2
    assert result["holdout"]["combined"]["counter_event_recall"] == 1.0
    assert result["holdout"]["combined"]["pressure_event_precision"] == 1.0
    assert all(result["eligibility"].values())
    assert all(result["screens"].values())
    assert result["decision"]["recharge_event_detector_corroborated"] is True
    assert result["decision"]["vehicle_fill_validation"] is False
    serialized = json.dumps(result)
    assert "private-pressure.csv" not in serialized
    assert "medium_p" not in serialized
    assert str(tmp_path) not in serialized


def test_attestation_is_required(tmp_path: Path) -> None:
    _write_reverse_logs(tmp_path)
    mapping = _mapping()
    mapping["attestation"]["local_clock_alignment_attested"] = False

    with pytest.raises(ValueError, match="attestations"):
        evaluate_lifecycle_pressure_alignment(tmp_path, mapping, rules=_rules())
