from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

from h2station.confidential_history_profile import header_fingerprint
from h2station.confidential_pressure_cycle_holdout import PressureCycleRules
from h2station.confidential_pressure_cycle_ordered_holdout import (
    evaluate_ordered_pressure_cycle_holdout,
)


def test_ordered_revision_normalizes_reverse_chronological_files(tmp_path: Path) -> None:
    header = [f"private_{index}" for index in range(9)]
    start = datetime(2024, 1, 1)
    for file_index in range(6):
        rows = []
        for index in range(800):
            phase = index % 80
            cycle_drop = 4.2 + ((index // 80) % 5) * 0.2
            high = 85.0 - min(phase, 60) * cycle_drop / 60.0
            if phase > 60:
                high = 85.0 - cycle_drop + (phase - 60) * cycle_drop / 19.0
            rows.append([
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
        with (tmp_path / f"secret_{file_index}.csv").open(
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
            "numeric_channels": [{"role": "high_storage_pressure", "index": 8}],
        }],
        "attestation": {"medium_high_pressure_roles_attested_elsewhere": True},
    }
    result = evaluate_ordered_pressure_cycle_holdout(
        tmp_path,
        mapping,
        rules=PressureCycleRules(sample_stride=1),
    )
    assert result["reverse_chronological_files"] == 6
    assert result["mixed_order_files"] == 0
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
