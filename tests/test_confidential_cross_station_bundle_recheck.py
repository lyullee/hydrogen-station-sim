from __future__ import annotations

import csv
from pathlib import Path

from audit_confidential_cross_station_bundle_recheck import audit


def _write_csv(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def test_recheck_accepts_reverse_ordered_source_and_keeps_full_loop_false(tmp_path: Path):
    bundle_a = tmp_path / "private-a"
    bundle_b = tmp_path / "private-b"
    bundle_a.mkdir()
    bundle_b.mkdir()
    _write_csv(
        bundle_a / "a.csv",
        [
            ["LocalTimeCol", "PI_0001", "XV_0001"],
            ["11/18/2024 12:00:00 PM", "50", "OPEN"],
            ["11/18/2024 11:59:59 AM", "49", "CLOSED"],
        ],
    )
    _write_csv(
        bundle_b / "b.csv",
        [
            ["time", "PT_001", "TT_001", "COMP.STATUS"],
            ["2025 04 21 00:00:00", "50", "20", "RUN"],
            ["2025 04 21 00:00:01", "51", "21", "RUN"],
        ],
    )

    result = audit(tmp_path, sample_rows=32)

    assert result["bundle_count"] == 2
    assert result["station_side_transfer_candidate"] is True
    assert result["full_loop_external_validation_supported"] is False
    assert result["raw_rows_persisted"] is False
    assert result["bundles"][0]["timestamp_directions"] == ["descending"]
    assert result["bundles"][1]["timestamp_directions"] == ["ascending"]
