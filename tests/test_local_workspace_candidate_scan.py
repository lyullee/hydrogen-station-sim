from __future__ import annotations

import json
from pathlib import Path

from scripts.scan_local_workspace_candidates import scan_workspace


def test_workspace_scan_is_aggregate_only(tmp_path: Path) -> None:
    (tmp_path / "vehicle_trace.csv").write_text(
        "time,vehicle_pressure,vehicle_temperature,flow\n"
        "0,1,20,0\n",
        encoding="utf-8",
    )
    (tmp_path / "notes.md").write_text("station notes", encoding="utf-8")

    result = scan_workspace([tmp_path])

    assert result["scan"]["machine_readable_files"] == 2
    assert result["scan"]["path_keyword_candidates"] == 1
    assert result["scan"]["csv_tsv_headers_screened"] == 1
    assert result["scan"]["header_family_candidate_counts"]["vehicle_or_dispenser"] == 1
    assert result["scan"]["coarse_candidate_classes"][
        "vehicle_pressure_temperature_candidate"
    ] == 1
    assert result["eligibility"]["full_loop_candidate_count"] == 0
    assert all(value is False for value in result["privacy"].values())

    serialized = json.dumps(result, ensure_ascii=False)
    assert str(tmp_path) not in serialized
    assert "vehicle_trace.csv" not in serialized
    assert "vehicle_pressure,vehicle_temperature" not in serialized


def test_workspace_scan_skips_virtualenv_and_build_outputs(tmp_path: Path) -> None:
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "hidden.csv").write_text("pressure\n1\n", encoding="utf-8")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "hidden.csv").write_text("pressure\n1\n", encoding="utf-8")

    result = scan_workspace([tmp_path])

    assert result["scan"]["machine_readable_files"] == 0


def test_release_rig_nozzle_trace_is_not_classified_as_vehicle_loop(tmp_path: Path) -> None:
    (tmp_path / "release_rig.csv").write_text(
        "Time,PT1ReleaseRig,PT2Nozzle\n0,10,9\n", encoding="utf-8"
    )

    result = scan_workspace([tmp_path])

    classes = result["scan"]["coarse_candidate_classes"]
    assert classes["release_rig_experiment_candidate"] == 1
    assert classes.get("vehicle_pressure_temperature_candidate", 0) == 0


def test_split_station_vehicle_pair_is_only_reported_as_an_attestable_lead(
    tmp_path: Path,
) -> None:
    (tmp_path / "event01_station.csv").write_text(
        "time (s),station_pressure_mpa,gas_temperature_c,flow_g_s,operation_state\n"
        "0,45,-35,10,start\n1,46,-34,10,fill\n",
        encoding="utf-8",
    )
    (tmp_path / "event01_vehicle.csv").write_text(
        "time (s),vehicle_pressure_mpa,vehicle_temperature_c\n"
        "0,5,25\n1,6,28\n",
        encoding="utf-8",
    )

    result = scan_workspace([tmp_path])

    assert result["scan"]["split_pair_candidate_count"] == 1
    assert result["eligibility"]["split_pair_candidates_require_attestation"] == 1
    assert result["eligibility"]["full_loop_candidate_count"] == 0
    serialized = json.dumps(result, ensure_ascii=False)
    assert str(tmp_path) not in serialized
    assert "event01_station.csv" not in serialized


def test_schema_template_is_not_treated_as_measured_vehicle_trace(tmp_path: Path) -> None:
    (tmp_path / "discharge_timeseries_template.csv").write_text(
        "time_s,tank_pressure_pa,tank_temperature_k,measured_mass_flow_kg_s\n",
        encoding="utf-8",
    )

    result = scan_workspace([tmp_path])

    classes = result["scan"]["coarse_candidate_classes"]
    assert classes.get("vehicle_pressure_temperature_candidate", 0) == 0
    assert result["scan"]["split_pair_candidate_count"] == 0


def test_xlsx_header_inspection_is_opt_in_and_aggregate_only(tmp_path: Path) -> None:
    openpyxl = __import__("openpyxl")
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["time (s)", "station_pressure_mpa", "gas_temperature_c", "flow_g_s", "operation_state"])
    sheet.append([0, 45, -35, 10, "fill"])
    workbook.save(tmp_path / "event_station.xlsx")

    disabled = scan_workspace([tmp_path])
    assert disabled["scan"]["spreadsheet_inspection_enabled"] is False
    assert disabled["scan"]["spreadsheet_headers_screened"] == 0

    enabled = scan_workspace([tmp_path], inspect_spreadsheets=True)
    assert enabled["scan"]["spreadsheet_inspection_enabled"] is True
    assert enabled["scan"]["spreadsheet_headers_screened"] == 1
    assert enabled["scan"]["coarse_candidate_classes"]["control_or_protocol_candidate"] == 1
    serialized = json.dumps(enabled, ensure_ascii=False)
    assert str(tmp_path) not in serialized
    assert "event_station.xlsx" not in serialized
    assert "station_pressure_mpa" not in serialized


def test_malformed_xlsx_is_counted_as_a_bounded_parse_miss(tmp_path: Path) -> None:
    # Discovery must continue when a workspace contains a mislabeled or
    # truncated workbook; the filename and raw contents must not enter output.
    (tmp_path / "truncated_station_export.xlsx").write_bytes(b"not-a-zip")
    (tmp_path / "valid_station.csv").write_text(
        "time_s,station_pressure_mpa,gas_temperature_c,flow_g_s,operation_state\n"
        "0,45,-35,10,fill\n",
        encoding="utf-8",
    )

    result = scan_workspace([tmp_path], inspect_spreadsheets=True)

    assert result["scan"]["spreadsheet_headers_screened"] == 1
    assert result["scan"]["spreadsheet_header_parse_errors"] == 1
    assert result["scan"]["csv_tsv_headers_screened"] == 1
    serialized = json.dumps(result, ensure_ascii=False)
    assert "truncated_station_export.xlsx" not in serialized
    assert "station_pressure_mpa" not in serialized


def test_single_file_full_loop_candidate_is_counted_without_publishing_headers(
    tmp_path: Path,
) -> None:
    (tmp_path / "synchronized_export.csv").write_text(
        "time (s),station_pressure_mpa,station_temperature_c,vehicle_pressure_mpa,"
        "vehicle_temperature_c,flow_g_s,protocol_phase\n"
        "0,45,-35,5,25,10,fill\n",
        encoding="utf-8",
    )

    result = scan_workspace([tmp_path])

    assert result["eligibility"]["full_loop_candidate_count"] == 1
    assert result["scan"]["coarse_candidate_classes"][
        "full_loop_timeseries_candidate"
    ] == 1
    serialized = json.dumps(result, ensure_ascii=False)
    assert "synchronized_export.csv" not in serialized
    assert "station_pressure_mpa" not in serialized


def test_source_and_receiving_channels_without_protocol_are_partial_only(
    tmp_path: Path,
) -> None:
    (tmp_path / "bench_trace.csv").write_text(
        "time_s,pressure_mpa,source_pressure_1_mpa,temperature_c,flow_g_s\n"
        "0,5,85,20,1\n"
        "1,6,84,21,2\n",
        encoding="utf-8",
    )

    result = scan_workspace([tmp_path])

    assert result["eligibility"]["partial_loop_candidate_count"] == 1
    assert result["eligibility"]["full_loop_candidate_count"] == 0
    assert result["scan"]["coarse_candidate_classes"][
        "boundary_bundle_missing_protocol_candidate"
    ] == 1


def test_mat_variable_name_inspection_is_opt_in_and_aggregate_only(tmp_path: Path) -> None:
    scipy_io = __import__("scipy.io", fromlist=["savemat"])
    scipy_io.savemat(
        tmp_path / "synchronized_mat_export.mat",
        {
            "time_s": [0.0, 1.0],
            "station_pressure_mpa": [45.0, 46.0],
            "vehicle_pressure_mpa": [5.0, 6.0],
            "vehicle_temperature_c": [25.0, 26.0],
            "flow_g_s": [10.0, 11.0],
            "protocol_phase": ["fill", "fill"],
        },
    )

    disabled = scan_workspace([tmp_path])
    assert disabled["scan"]["scientific_inspection_enabled"] is False
    assert disabled["scan"]["scientific_headers_screened"] == 0
    assert disabled["eligibility"]["full_loop_candidate_count"] == 0

    enabled = scan_workspace([tmp_path], inspect_scientific=True)
    assert enabled["scan"]["scientific_inspection_enabled"] is True
    assert enabled["scan"]["scientific_headers_screened"] == 1
    assert enabled["eligibility"]["full_loop_candidate_count"] == 1
    serialized = json.dumps(enabled, ensure_ascii=False)
    assert str(tmp_path) not in serialized
    assert "synchronized_mat_export.mat" not in serialized
    assert "station_pressure_mpa" not in serialized
