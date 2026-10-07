from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from openpyxl import Workbook

from scripts.audit_controlled_data_schema import inventory_schema


def test_header_only_inventory_identifies_candidate_shapes_without_disclosure(tmp_path: Path):
    full_loop = tmp_path / "owner_site_private_trace.csv"
    full_loop.write_text(
        "private_time,private_vehicle_pressure,private_inlet_temp,private_mass_flow,"
        "private_vehicle_id,private_cascade_pressure,private_controller_state\n"
        "sensitive-value,1,2,3,4,5,6\n",
        encoding="utf-8",
    )
    vehicle = tmp_path / "sensitive_vehicle_run.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "confidential worksheet"
    sheet.append([
        "private_time", "private_vehicle_pressure", "private_temperature",
        "private_mass_flow", "private_vehicle", "private_dispenser",
    ])
    sheet.append(["sensitive-value", 1, 2, 3, 4, 5])
    workbook.save(vehicle)

    report = inventory_schema([tmp_path])
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["schema_search_max_rows_per_table"] == 40
    assert report["schema_search_rows_examined"] == 4
    assert report["raw_rows_persisted"] is False
    assert report["candidate_schema_counts"]["full_loop_candidate"] == 1
    assert report["candidate_schema_counts"]["vehicle_fill_candidate"] == 1
    assert report["candidate_schema_counts"]["station_recharge_candidate"] == 0
    assert "owner_site_private_trace" not in rendered
    assert "private_vehicle_pressure" not in rendered
    assert "confidential worksheet" not in rendered
    assert "sensitive-value" not in rendered


def test_inventory_finds_header_after_title_rows_without_retaining_them(tmp_path: Path):
    source = tmp_path / "controlled_export.csv"
    source.write_text(
        "confidential title\n"
        "operator-only note\n"
        "clock,vehicle_pressure,inlet_temperature,mass_flow,vehicle,cascade,controller_state\n"
        "private-value,1,2,3,4,5,6\n",
        encoding="utf-8",
    )

    report = inventory_schema([tmp_path])
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["candidate_schema_counts"]["full_loop_candidate"] == 1
    assert report["measurement_rows_persisted"] is False
    assert "confidential title" not in rendered
    assert "operator-only note" not in rendered
    assert "private-value" not in rendered


def test_schema_inventory_counts_unreadable_tabular_file_without_disclosure(tmp_path: Path):
    unreadable = tmp_path / "restricted.xlsx"
    unreadable.write_bytes(b"not a workbook")

    report = inventory_schema([tmp_path])
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["source_files_scanned"] == 1
    assert report["source_tables_scanned"] == 0
    assert report["unreadable_tables"] == 1
    assert "restricted.xlsx" not in rendered


def test_schema_inventory_screens_zip_members_without_disclosing_member_names(tmp_path: Path):
    archive = tmp_path / "controlled_bundle.zip"
    with ZipFile(archive, "w") as bundle:
        bundle.writestr(
            "private-folder/secret-full-loop.csv",
            "time,vehicle_pressure,temperature,mass_flow,vehicle,cascade,controller_state\n"
            "private-value,1,2,3,4,5,6\n",
        )

    report = inventory_schema([tmp_path])
    rendered = json.dumps(report, ensure_ascii=False)

    assert report["archive_members_scanned"] == 1
    assert report["candidate_schema_counts"]["full_loop_candidate"] == 1
    assert report["tabular_content_format_counts"] == {"csv": 1}
    assert "secret-full-loop" not in rendered
    assert "private-folder" not in rendered
    assert "private-value" not in rendered
