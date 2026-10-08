from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

from h2station.confidential_history_profile import (
    analyze_confidential_history,
    header_fingerprint,
)


def _write_trace(path: Path, header: list[str], rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerow(["unit"] * len(header))
        writer.writerows(rows)


def test_longitudinal_history_is_privacy_bounded_and_excludes_counters_from_stability(
    tmp_path: Path,
) -> None:
    start = datetime(2024, 1, 1)
    pressure_header = [f"private_pressure_{index}" for index in range(9)]
    thermal_header = [f"private_thermal_{index}" for index in range(9)]
    pressure_rows = []
    thermal_rows = []
    for index in range(200):
        timestamp = (start + timedelta(seconds=index)).strftime("%Y-%m-%d %H:%M:%S")
        wave = float(index % 10)
        pressure_rows.append(
            [timestamp, index, wave / 10, index * 2, wave / 20, 16 + wave / 10,
             18 + wave / 10, 43 + wave / 20, 83 + wave / 20]
        )
        thermal_rows.append(
            [timestamp, timestamp, index, index * 2, 22 + wave / 10,
             23 + wave / 10, 24 + wave / 10, 21 + wave / 10, 20 + wave / 10]
        )
    _write_trace(tmp_path / "pressure.csv", pressure_header, pressure_rows)
    _write_trace(tmp_path / "thermal.csv", thermal_header, thermal_rows)
    mapping = {
        "schemas": [
            {
                "schema_id": "pressure_flow_candidate",
                "header_fingerprint": header_fingerprint(pressure_header),
                "timestamp_index": 0,
                "skip_rows_after_header": 1,
                "numeric_channels": [
                    {"role": "counter", "index": 1},
                    {"role": "flow", "index": 2},
                    {"role": "low", "index": 6},
                    {"role": "medium", "index": 7},
                    {"role": "high", "index": 8},
                ],
                "stability_roles": ["flow", "low", "medium", "high"],
                "ordered_role_groups": [["low", "medium", "high"]],
            },
            {
                "schema_id": "thermal_candidate",
                "header_fingerprint": header_fingerprint(thermal_header),
                "timestamp_index": 0,
                "skip_rows_after_header": 1,
                "numeric_channels": [
                    {"role": "counter", "index": 2},
                    {"role": "temperature_1", "index": 4},
                    {"role": "temperature_2", "index": 5},
                ],
                "stability_roles": ["temperature_1", "temperature_2"],
                "plausible_ranges": {
                    "temperature_1": [-80, 120],
                    "temperature_2": [-80, 120],
                },
            },
        ],
        "attestation": {
            "flow_totalizer_roles_attested": False,
            "temperature_roles_attested": False,
            "vehicle_side_channels_confirmed": False,
        },
    }
    result = analyze_confidential_history(
        tmp_path,
        mapping,
        sample_stride=1,
        calibration_fraction=0.70,
    )
    assert result["files_read"] == 2
    assert result["raw_data_rows"] == 400
    assert result["sampled_rows"] == 400
    assert result["median_sample_period_s"] == 1.0
    assert result["schema_coverage_overlap_fraction"] == 1.0
    assert result["eligibility"]["station_side_longitudinal_diagnostic_supported"] is False
    assert result["eligibility"]["runtime_parameter_application"] is False
    assert result["eligibility"]["vehicle_fill_validation"] is False
    assert result["schemas"]["pressure_flow_candidate"]["stability_supported"] is True
    assert "counter" not in result["schemas"]["pressure_flow_candidate"][
        "holdout_medians_inside_calibration_p05_p95"
    ]
    encoded = str(result)
    assert "private_pressure" not in encoded
    assert "private_thermal" not in encoded
    assert str(tmp_path) not in encoded
