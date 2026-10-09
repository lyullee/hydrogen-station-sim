from __future__ import annotations

import csv
import json
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


def test_committed_recheck_is_privacy_bounded_and_matches_verified_aggregate():
    root = Path(__file__).resolve().parents[1]
    artifact_path = root / "research" / "local_cross_station_bundle_recheck_2026_10_09.json"
    record = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert record["schema_version"] == 1
    assert record["artifact_type"] == "confidential_cross_station_bundle_recheck"
    assert record["bundle_count"] == 2
    assert [item["id"] for item in record["bundles"]] == [
        "station_bundle_a",
        "station_bundle_b",
    ]
    assert [item["file_count"] for item in record["bundles"]] == [25, 8]
    assert [item["data_rows"] for item in record["bundles"]] == [
        58_618_858,
        653_442,
    ]
    assert [item["timestamp_directions"] for item in record["bundles"]] == [
        ["descending"],
        ["ascending"],
    ]
    assert record["station_side_transfer_candidate"] is True
    assert record["full_loop_external_validation_supported"] is False
    assert record["quantitative_consequence_validation_supported"] is False

    for key in (
        "source_identifiers_published",
        "raw_rows_persisted",
        "exact_source_dates_published",
        "manufacturer_or_model_published",
        "tag_names_published",
    ):
        assert record[key] is False
