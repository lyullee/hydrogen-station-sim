"""Tests for the privacy-bounded wide equipment continuity screen."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_local_wide_equipment_continuity import audit_wide_equipment_directory


ARTIFACT = ROOT / "research/local_wide_equipment_continuity_recheck_2026_10_09.json"


def _write_wide_csv(path: Path, *, rows: list[list[str]]) -> None:
    header = ["timestamp", "pressure", "temperature", "compressor_load", "state"]
    header.extend(f"channel_{index}" for index in range(5, 64))
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


def _row(timestamp: str, state: str, load: str = "0") -> list[str]:
    return [timestamp, "70.0", "25.0", load, state, *(["0"] * 59)]


def test_continuity_screen_is_aggregate_and_privacy_bounded(tmp_path: Path) -> None:
    _write_wide_csv(
        tmp_path / "private-equipment-log.csv",
        rows=[
            _row("2025 04 21 00:00:00", "idle"),
            _row("2025 04 21 00:00:01", "run", "1"),
            _row("2025 04 21 00:00:02", "idle"),
        ],
    )
    result = audit_wide_equipment_directory(tmp_path, generated_at="2026-10-09")
    assert result["artifact_type"] == "local_wide_equipment_continuity_screen"
    assert all(value is False for value in result["privacy"].values())
    inventory = result["inventory"]
    assert inventory["wide_file_count"] == 1
    assert inventory["wide_row_count"] == 3
    assert inventory["timestamp_parse_failures"] == 0
    assert inventory["median_positive_interval_s"] == 1.0
    assert inventory["state_transition_count"] >= 2
    rendered = json.dumps(result, ensure_ascii=False)
    assert "private-equipment-log" not in rendered
    assert "compressor_load" not in rendered
    assert "2025 04 21" not in rendered


def test_continuity_screen_rejects_bad_time_as_not_ready(tmp_path: Path) -> None:
    _write_wide_csv(
        tmp_path / "wide.csv",
        rows=[
            _row("2025 04 21 00:00:01", "idle"),
            _row("not-a-time", "run"),
            _row("2025 04 21 00:00:00", "idle"),
        ],
    )
    result = audit_wide_equipment_directory(tmp_path, generated_at="2026-10-09")
    assert result["inventory"]["timestamp_parse_failures"] == 1
    assert result["eligibility"]["station_equipment_continuity_screen_ready"] is False
    assert result["eligibility"]["measured_boundary_replay_ready"] is False


def test_narrow_files_are_not_counted(tmp_path: Path) -> None:
    (tmp_path / "narrow.csv").write_text("timestamp,pressure\n2025-04-21 00:00:00,70\n", encoding="utf-8")
    result = audit_wide_equipment_directory(tmp_path, generated_at="2026-10-09")
    assert result["inventory"]["wide_file_count"] == 0
    assert result["eligibility"]["station_equipment_continuity_screen_ready"] is False


def test_committed_continuity_recheck_preserves_validation_boundary() -> None:
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["artifact_type"] == "local_wide_equipment_continuity_screen"
    assert all(value is False for value in record["privacy"].values())
    assert record["eligibility"]["station_equipment_continuity_screen_ready"] is True
    assert record["eligibility"]["measured_boundary_replay_ready"] is False
    assert record["eligibility"]["independent_external_validation"] is False
    assert record["eligibility"]["full_loop_vehicle_validation"] is False
    rendered = ARTIFACT.read_text(encoding="utf-8")
    assert "\\\\" not in rendered
    assert "2025 04" not in rendered
