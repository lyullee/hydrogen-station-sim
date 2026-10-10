from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook

from h2station.privacy_safe_full_loop_intake import (
    PilotIntakeRules,
    validate_privacy_safe_split_event_bundle,
    validate_privacy_safe_pilot_bundle,
)


def _write_event(path: Path, *, with_vehicle: bool = True) -> None:
    fields = [
        "elapsed_time_s",
        "station_pressure_mpa",
        "delivered_gas_temperature_c",
        "mass_flow_g_s",
        "protocol_phase",
    ]
    if with_vehicle:
        fields.extend(["vehicle_pressure_mpa", "vehicle_temperature_c"])
    rows = [
        {
            "elapsed_time_s": "0",
            "station_pressure_mpa": "45",
            "delivered_gas_temperature_c": "-35",
            "mass_flow_g_s": "10",
            "protocol_phase": "start",
        },
        {
            "elapsed_time_s": "1",
            "station_pressure_mpa": "46",
            "delivered_gas_temperature_c": "-34",
            "mass_flow_g_s": "10",
            "protocol_phase": "fill",
        },
    ]
    if with_vehicle:
        rows[0].update(vehicle_pressure_mpa="5", vehicle_temperature_c="25")
        rows[1].update(vehicle_pressure_mpa="6", vehicle_temperature_c="28")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_three_events_produce_raw_row_free_pilot_report(tmp_path: Path) -> None:
    paths = [tmp_path / f"event_{index}.csv" for index in range(3)]
    for path in paths:
        _write_event(path)

    report = validate_privacy_safe_pilot_bundle(paths)

    assert report["status"] == "READY_FOR_FULL_LOOP_PROTOCOL_FREEZE"
    assert report["event_count"] == 3
    assert report["valid_event_count"] == 3
    assert report["vehicle_boundary_complete_event_count"] == 3
    assert report["full_loop_readiness"]["full_loop_protocol_freeze_candidate"] is True
    assert report["full_loop_readiness"]["missing_vehicle_boundary_event_count"] == 0
    assert report["raw_rows_persisted"] is False
    assert report["source_paths_published"] is False
    assert report["event_reports"][0]["event_id"] == "event_001"
    assert "event_0.csv" not in str(report)


def test_identity_and_time_quality_errors_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "event.csv"
    fields = [
        "elapsed_time_s",
        "station_pressure_mpa",
        "delivered_gas_temperature_c",
        "mass_flow_g_s",
        "protocol_phase",
        "site_name",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "elapsed_time_s": "1",
            "station_pressure_mpa": "45",
            "delivered_gas_temperature_c": "-35",
            "mass_flow_g_s": "1",
            "protocol_phase": "fill",
            "site_name": "redacted",
        })
        writer.writerow({
            "elapsed_time_s": "0",
            "station_pressure_mpa": "46",
            "delivered_gas_temperature_c": "-34",
            "mass_flow_g_s": "-1",
            "protocol_phase": "fill",
            "site_name": "redacted",
        })

    report = validate_privacy_safe_pilot_bundle(
        [path],
        rules=PilotIntakeRules(minimum_event_count=1),
    )

    event = report["event_reports"][0]
    assert report["status"] == "SCHEMA_INCOMPLETE"
    assert event["schema_valid"] is False
    assert event["forbidden_identity_columns_detected"] is True
    assert "forbidden_identity_or_calendar_column" in event["errors"]


def test_intake_counts_all_rows_without_materializing_the_event(tmp_path: Path) -> None:
    path = tmp_path / "event.csv"
    path.write_text(
        "elapsed_time_s,station_pressure_mpa,delivered_gas_temperature_c,mass_flow_g_s,protocol_phase\n"
        "0,45,-35,10,start\n"
        "bad,46,-34,10,fill\n"
        "2,47,-33,10,stop\n",
        encoding="utf-8",
    )

    report = validate_privacy_safe_pilot_bundle(
        [path], rules=PilotIntakeRules(minimum_event_count=1)
    )

    event = report["event_reports"][0]
    assert event["row_count"] == 3
    assert any("elapsed_time_s at row 3" in error for error in event["errors"])


def test_station_only_bundle_is_ready_for_schema_freeze_but_not_full_loop(
    tmp_path: Path,
) -> None:
    paths = [tmp_path / f"event_{index}.csv" for index in range(3)]
    for path in paths:
        _write_event(path, with_vehicle=False)

    report = validate_privacy_safe_pilot_bundle(paths)

    assert report["status"] == "READY_FOR_PROTOCOL_FREEZE"
    assert report["full_loop_readiness"]["station_boundary_ready"] is True
    assert report["full_loop_readiness"]["vehicle_boundary_complete"] is False
    assert report["full_loop_readiness"]["full_loop_protocol_freeze_candidate"] is False
    assert report["full_loop_readiness"]["missing_vehicle_boundary_event_count"] == 3
    assert "vehicle_pressure_mpa" in report["decision"]["next_step"]


def test_nonuniform_event_axis_is_rejected_before_full_loop_freeze(tmp_path: Path) -> None:
    paths = [tmp_path / f"event_{index}.csv" for index in range(3)]
    for path in paths:
        _write_event(path)
    # One event has a large logger-clock jump.  It is still monotonic, but it
    # cannot be treated as a synchronized sampling grid for a frozen holdout.
    paths[1].write_text(
        "elapsed_time_s,station_pressure_mpa,delivered_gas_temperature_c,mass_flow_g_s,protocol_phase,vehicle_pressure_mpa,vehicle_temperature_c\n"
        "0,45,-35,10,start,5,25\n"
        "1,46,-34,10,fill,6,28\n"
        "5,47,-33,10,fill,7,30\n",
        encoding="utf-8",
    )

    report = validate_privacy_safe_pilot_bundle(paths)

    assert report["status"] == "READY_FOR_PROTOCOL_FREEZE"
    assert report["full_loop_readiness"]["common_elapsed_time_axis"] is False
    assert report["full_loop_readiness"]["common_sample_period_s"] is None
    assert report["event_reports"][1]["elapsed_time_s"]["sample_period_jitter_ratio"] > 0.05


def test_empty_protocol_phase_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "event.csv"
    path.write_text(
        "elapsed_time_s,station_pressure_mpa,delivered_gas_temperature_c,mass_flow_g_s,protocol_phase\n"
        "0,45,-35,10,start\n"
        "1,46,-34,10,\n",
        encoding="utf-8",
    )

    report = validate_privacy_safe_pilot_bundle(
        [path], rules=PilotIntakeRules(minimum_event_count=1)
    )

    event = report["event_reports"][0]
    assert event["schema_valid"] is False
    assert any("protocol_phase at row 3 is empty" in error for error in event["errors"])


def test_split_station_vehicle_exports_are_checked_without_merging_raw_rows(
    tmp_path: Path,
) -> None:
    pairs = []
    for index in range(3):
        station = tmp_path / f"station_{index}.csv"
        vehicle = tmp_path / f"vehicle_{index}.csv"
        station.write_text(
            "elapsed_time_s,station_pressure_mpa,delivered_gas_temperature_c,mass_flow_g_s,protocol_phase\n"
            "0,45,-35,10,start\n"
            "1,46,-34,10,fill\n",
            encoding="utf-8",
        )
        vehicle.write_text(
            "elapsed_time_s,vehicle_pressure_mpa,vehicle_temperature_c\n"
            "0,5,25\n"
            "1,6,28\n",
            encoding="utf-8",
        )
        pairs.append((station, vehicle))

    report = validate_privacy_safe_split_event_bundle(pairs)

    assert report["status"] == "READY_FOR_FULL_LOOP_PROTOCOL_FREEZE"
    assert report["full_loop_readiness"]["common_elapsed_time_axis"] is True
    assert report["vehicle_boundary_complete_event_count"] == 3
    assert "station_0.csv" not in str(report)
    assert "vehicle_0.csv" not in str(report)


def test_split_station_vehicle_time_mismatch_fails_closed(tmp_path: Path) -> None:
    pairs = []
    for index in range(3):
        station = tmp_path / f"station_{index}.csv"
        vehicle = tmp_path / f"vehicle_{index}.csv"
        station.write_text(
            "elapsed_time_s,station_pressure_mpa,delivered_gas_temperature_c,mass_flow_g_s,protocol_phase\n"
            "0,45,-35,10,start\n"
            "1,46,-34,10,fill\n",
            encoding="utf-8",
        )
        vehicle_time = "1.01" if index == 1 else "1"
        vehicle.write_text(
            "elapsed_time_s,vehicle_pressure_mpa,vehicle_temperature_c\n"
            f"0,5,25\n{vehicle_time},6,28\n",
            encoding="utf-8",
        )
        pairs.append((station, vehicle))

    report = validate_privacy_safe_split_event_bundle(pairs)

    assert report["status"] == "SCHEMA_INCOMPLETE"
    assert report["event_reports"][1]["schema_valid"] is False
    assert "channel_time_axis_mismatch" in report["event_reports"][1]["errors"]


def test_combined_xlsx_event_is_streamed_through_same_gate(tmp_path: Path) -> None:
    paths = []
    for index in range(3):
        path = tmp_path / f"event_{index}.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "event"
        sheet.append([
            "elapsed_time_s", "station_pressure_mpa",
            "delivered_gas_temperature_c", "mass_flow_g_s", "protocol_phase",
            "vehicle_pressure_mpa", "vehicle_temperature_c",
        ])
        sheet.append([0, 20, 20, 1, "start", 5, 25])
        sheet.append([1, 21, 21, 1.2, "fill", 6, 28])
        workbook.save(path)
        paths.append(path)

    report = validate_privacy_safe_pilot_bundle(paths, xlsx_worksheet="event")

    assert report["status"] == "READY_FOR_FULL_LOOP_PROTOCOL_FREEZE"
    assert report["valid_event_count"] == 3
    assert report["full_loop_readiness"]["common_elapsed_time_axis"] is True


def test_split_mixed_csv_xlsx_channels_use_same_time_axis_gate(tmp_path: Path) -> None:
    pairs = []
    for index in range(3):
        station = tmp_path / f"station_{index}.csv"
        station.write_text(
            "elapsed_time_s,station_pressure_mpa,delivered_gas_temperature_c,mass_flow_g_s,protocol_phase\n"
            "0,45,-35,10,start\n"
            "1,46,-34,10,fill\n",
            encoding="utf-8",
        )
        vehicle = tmp_path / f"vehicle_{index}.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "vehicle_trace"
        sheet.append(["elapsed_time_s", "vehicle_pressure_mpa", "vehicle_temperature_c"])
        sheet.append([0, 5, 25])
        sheet.append([1, 6, 28])
        workbook.save(vehicle)
        pairs.append((station, vehicle))

    report = validate_privacy_safe_split_event_bundle(
        pairs,
        station_worksheet=None,
        vehicle_worksheet="vehicle_trace",
    )

    assert report["status"] == "READY_FOR_FULL_LOOP_PROTOCOL_FREEZE"
    assert report["vehicle_boundary_complete_event_count"] == 3
    assert "vehicle_0.xlsx" not in str(report)
