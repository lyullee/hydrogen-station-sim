from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_local_station_data_utilization import audit_station_directory  # noqa: E402


def _write_csv(path: Path, width: int, rows: int) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([f"field_{index}" for index in range(width)])
        for row in range(rows):
            writer.writerow([row + index for index in range(width)])


def test_inventory_deduplicates_without_publishing_source_details(tmp_path: Path) -> None:
    source = tmp_path / "private-station"
    source.mkdir()
    _write_csv(source / "station-a.csv", 9, 4)
    (source / "station-copy.csv").write_bytes((source / "station-a.csv").read_bytes())
    _write_csv(source / "controller.csv", 64, 3)
    (source / "private-note.txt").write_text("secret site", encoding="utf-8")

    result = audit_station_directory(source)

    inventory = result["inventory"]
    assert inventory["csv_files"] == 3
    assert inventory["metadata_files"] == 1
    assert inventory["unique_csv_payloads"] == 2
    assert inventory["exact_duplicate_groups"] == 1
    assert inventory["redundant_csv_files"] == 1
    assert inventory["physical_data_rows_after_one_header_per_file"] == 11
    assert inventory["deduplicated_data_rows"] == 7
    assert inventory["narrow_schema_files"] == 2
    assert inventory["wide_schema_files"] == 1

    serialized = str(result)
    assert "station-a.csv" not in serialized
    assert "secret site" not in serialized
    assert str(source) not in serialized
    assert result["assessment"]["local_station_data_is_sparse"] is False


def test_research_utilization_uses_only_deidentified_counts(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    _write_csv(source / "trace.csv", 9, 2)
    research = tmp_path / "research"
    research.mkdir()
    (research / "confidential_station_ordered_pressure_cycle_holdout_2026_10_08.json").write_text(
        '{"calibration":{"pressure_drop_mpa":{"count":10}},"holdout":{"pressure_drop_mpa":{"count":5}}}',
        encoding="utf-8",
    )
    (research / "confidential_station_cascade_sequence_holdout_2026_10_08.json").write_text(
        '{"calibration":{"paired_episode_count":7,"sequential_episode_count":6},'
        '"holdout":{"paired_episode_count":3,"sequential_episode_count":3}}',
        encoding="utf-8",
    )
    (research / "confidential_station_recharge_pressure_forecast_holdout_2026_10_08.json").write_text(
        '{"calibration":{"case_count":20},"holdout":{"case_count":8}}', encoding="utf-8"
    )
    (research / "confidential_station_recharge_flow_screen_2026_10_08.json").write_text(
        '{"screen":{"eligible_recharge_episodes":11}}', encoding="utf-8"
    )
    (research / "confidential_station_signal_consistency_screen_2026_10_08.json").write_text(
        '{"screen":{"strong_consistency_pairs":4}}', encoding="utf-8"
    )
    (research / "local_station_semantic_attestation_2026_10_09.json").write_text(
        '{"attested_roles":{"storage_pressure_role_count":2,'
        '"lifecycle_counter_role_count":2,"storage_pressure_units_attested":true,'
        '"lifecycle_counter_event_definition_attested":true,'
        '"flow_units_attested":false,"totalizer_reset_semantics_attested":false,'
        '"vehicle_side_channels_attested":0}}',
        encoding="utf-8",
    )

    result = audit_station_directory(source, research_dir=research)
    utilization = result["utilization"]
    assert utilization["ordered_high_bank_pressure_cycles"] == 15
    assert utilization["paired_medium_high_pressure_episodes"] == 10
    assert utilization["sequential_medium_high_pressure_episodes"] == 9
    assert utilization["short_horizon_pressure_forecast_cases"] == 28
    assert utilization["conditional_recharge_flow_episodes"] == 11
    assert utilization["strong_instantaneous_totalizer_consistency_pairs"] == 4
    assert utilization["semantic_attestation"]["storage_pressure_role_count"] == 2
    assert utilization["semantic_attestation"]["vehicle_side_channels_attested"] == 0
