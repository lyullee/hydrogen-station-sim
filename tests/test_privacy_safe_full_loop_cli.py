from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from freeze_privacy_safe_full_loop import build_manifest, build_split_manifest  # noqa: E402


def _event(path: Path) -> None:
    path.write_text(
        "elapsed_time_s,station_pressure_mpa,delivered_gas_temperature_c,mass_flow_g_s,protocol_phase\n"
        "0,20,20,1,start\n"
        "1,21,21,1.2,fill\n",
        encoding="utf-8",
    )


def test_cli_builder_creates_hash_only_preaccess_manifest(tmp_path: Path) -> None:
    events = []
    for index in range(3):
        event = tmp_path / f"private-event-{index}.csv"
        _event(event)
        events.append(event)
    protocol = tmp_path / "protocol.json"
    model = tmp_path / "model.py"
    evaluator = tmp_path / "evaluator.py"
    roles = tmp_path / "roles.json"
    for path in (protocol, model, evaluator):
        path.write_text("locked", encoding="utf-8")
    roles.write_text(json.dumps({
        "elapsed_time_s": "event-relative logger time",
        "station_pressure_mpa": "station boundary pressure",
        "delivered_gas_temperature_c": "delivery gas temperature",
        "protocol_phase": "controller phase",
        "mass_or_transferred_mass": "calibrated mass-flow channel",
    }), encoding="utf-8")

    manifest = build_manifest(
        events,
        protocol_path=protocol,
        model_path=model,
        evaluator_path=evaluator,
        channel_roles_path=roles,
    )

    assert manifest["status"] == "FROZEN_BEFORE_OUTCOME_ACCESS"
    assert manifest["freeze"]["outcomes_accessed_before_freeze"] is False
    assert manifest["bundle"]["event_count"] == 3
    assert str(tmp_path) not in str(manifest)
    assert "private-event-0.csv" not in str(manifest)


def test_cli_builder_can_fail_closed_without_vehicle_boundary(tmp_path: Path) -> None:
    events = []
    for index in range(3):
        event = tmp_path / f"private-event-{index}.csv"
        _event(event)
        events.append(event)
    protocol = tmp_path / "protocol.json"
    model = tmp_path / "model.py"
    evaluator = tmp_path / "evaluator.py"
    roles = tmp_path / "roles.json"
    for path in (protocol, model, evaluator):
        path.write_text("locked", encoding="utf-8")
    roles.write_text(json.dumps({
        "elapsed_time_s": "event-relative logger time",
        "station_pressure_mpa": "station boundary pressure",
        "delivered_gas_temperature_c": "delivery gas temperature",
        "protocol_phase": "controller phase",
        "mass_or_transferred_mass": "calibrated mass-flow channel",
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="incomplete"):
        build_manifest(
            events,
            protocol_path=protocol,
            model_path=model,
            evaluator_path=evaluator,
            channel_roles_path=roles,
            require_vehicle_boundary=True,
        )


def test_cli_builder_accepts_paired_station_vehicle_exports(tmp_path: Path) -> None:
    stations = []
    vehicles = []
    for index in range(3):
        station = tmp_path / f"station-{index}.csv"
        vehicle = tmp_path / f"vehicle-{index}.csv"
        station.write_text(
            "elapsed_time_s,station_pressure_mpa,delivered_gas_temperature_c,mass_flow_g_s,protocol_phase\n"
            "0,20,20,1,start\n"
            "1,21,21,1.2,fill\n",
            encoding="utf-8",
        )
        vehicle.write_text(
            "elapsed_time_s,vehicle_pressure_mpa,vehicle_temperature_c\n"
            "0,5,25\n"
            "1,6,28\n",
            encoding="utf-8",
        )
        stations.append(station)
        vehicles.append(vehicle)
    protocol = tmp_path / "protocol.json"
    model = tmp_path / "model.py"
    evaluator = tmp_path / "evaluator.py"
    roles = tmp_path / "roles.json"
    for path in (protocol, model, evaluator):
        path.write_text("locked", encoding="utf-8")
    roles.write_text(json.dumps({
        "elapsed_time_s": "event-relative logger time",
        "station_pressure_mpa": "station boundary pressure",
        "delivered_gas_temperature_c": "delivery gas temperature",
        "protocol_phase": "controller phase",
        "mass_or_transferred_mass": "calibrated mass-flow channel",
        "vehicle_pressure_mpa": "receiving-vessel pressure",
        "vehicle_temperature_c": "receiving-vessel temperature",
    }), encoding="utf-8")

    manifest = build_split_manifest(
        stations, vehicles,
        protocol_path=protocol,
        model_path=model,
        evaluator_path=evaluator,
        channel_roles_path=roles,
    )

    assert manifest["status"] == "FROZEN_BEFORE_OUTCOME_ACCESS"
    assert manifest["bundle"]["event_count"] == 3
    assert manifest["eligibility"]["full_loop_protocol_freeze_candidate"] is True
    assert str(tmp_path) not in str(manifest)


def test_cli_builder_accepts_combined_xlsx_events(tmp_path: Path) -> None:
    events = []
    for index in range(3):
        event = tmp_path / f"private-event-{index}.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "trace"
        sheet.append([
            "elapsed_time_s", "station_pressure_mpa",
            "delivered_gas_temperature_c", "mass_flow_g_s", "protocol_phase",
            "vehicle_pressure_mpa", "vehicle_temperature_c",
        ])
        sheet.append([0, 20, 20, 1, "start", 5, 25])
        sheet.append([1, 21, 21, 1.2, "fill", 6, 28])
        workbook.save(event)
        events.append(event)
    protocol = tmp_path / "protocol.json"
    model = tmp_path / "model.py"
    evaluator = tmp_path / "evaluator.py"
    roles = tmp_path / "roles.json"
    for path in (protocol, model, evaluator):
        path.write_text("locked", encoding="utf-8")
    roles.write_text(json.dumps({
        "elapsed_time_s": "event-relative logger time",
        "station_pressure_mpa": "station boundary pressure",
        "delivered_gas_temperature_c": "delivery gas temperature",
        "protocol_phase": "controller phase",
        "mass_or_transferred_mass": "calibrated mass-flow channel",
        "vehicle_pressure_mpa": "receiving-vessel pressure",
        "vehicle_temperature_c": "receiving-vessel temperature",
    }), encoding="utf-8")

    manifest = build_manifest(
        events,
        protocol_path=protocol,
        model_path=model,
        evaluator_path=evaluator,
        channel_roles_path=roles,
        xlsx_worksheet="trace",
    )

    assert manifest["bundle"]["event_count"] == 3
    assert manifest["eligibility"]["full_loop_protocol_freeze_candidate"] is True


def test_cli_builder_accepts_mixed_split_workbooks(tmp_path: Path) -> None:
    stations = []
    vehicles = []
    for index in range(3):
        station = tmp_path / f"station-{index}.csv"
        _event(station)
        vehicle = tmp_path / f"vehicle-{index}.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "vehicle"
        sheet.append(["elapsed_time_s", "vehicle_pressure_mpa", "vehicle_temperature_c"])
        sheet.append([0, 5, 25])
        sheet.append([1, 6, 28])
        workbook.save(vehicle)
        stations.append(station)
        vehicles.append(vehicle)
    protocol = tmp_path / "protocol.json"
    model = tmp_path / "model.py"
    evaluator = tmp_path / "evaluator.py"
    roles = tmp_path / "roles.json"
    for path in (protocol, model, evaluator):
        path.write_text("locked", encoding="utf-8")
    roles.write_text(json.dumps({
        "elapsed_time_s": "event-relative logger time",
        "station_pressure_mpa": "station boundary pressure",
        "delivered_gas_temperature_c": "delivery gas temperature",
        "protocol_phase": "controller phase",
        "mass_or_transferred_mass": "calibrated mass-flow channel",
        "vehicle_pressure_mpa": "receiving-vessel pressure",
        "vehicle_temperature_c": "receiving-vessel temperature",
    }), encoding="utf-8")

    manifest = build_split_manifest(
        stations, vehicles,
        protocol_path=protocol,
        model_path=model,
        evaluator_path=evaluator,
        channel_roles_path=roles,
        vehicle_xlsx_worksheet="vehicle",
    )

    assert manifest["eligibility"]["full_loop_protocol_freeze_candidate"] is True
    assert str(tmp_path) not in str(manifest)
