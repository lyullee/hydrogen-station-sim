import hashlib
import json
import sys
from pathlib import Path

import pytest
from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from intake_nbsdc_station_workbook import build_receipt  # noqa: E402


def _write_workbook(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Private station export"
    worksheet.append(
        [
            "Zeit",
            "PT_bank",
            "TT_vehicle",
            "MFM_flow",
            "Vehicle_ID",
            "ESD_Status",
            "Cascade_Bank",
        ]
    )
    worksheet.append(["2026-01-01T00:00:00", 35.0, 24.0, 0.1, "car-01", "READY", "M"])
    workbook.save(path)


def test_intake_records_aggregate_schema_without_private_labels(tmp_path):
    source = tmp_path / "authorized_station_export.xlsx"
    output = tmp_path / "receipt.json"
    _write_workbook(source)

    receipt = build_receipt(
        source,
        source_url="https://www.nbsdc.cn/general/dataDetail?id=64f08267bb16e06dfdc78c57&type=1",
        persistent_identifier="CSTR 16666.11.nbsdc.8c2MpcJl",
        rights="CC0 1.0",
        access_attested=True,
        output_path=output,
    )

    assert receipt["source"]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert receipt["aggregate_schema"]["table_count"] == 1
    assert receipt["aggregate_schema"]["full_loop_channels_co_located_in_one_table"] is True
    assert receipt["aggregate_schema"]["missing_full_loop_semantic_groups"] == []
    assert receipt["aggregate_schema"]["full_loop_contract_channels_co_located_in_one_table"] is False
    assert "delivered_temperature" in receipt["aggregate_schema"]["missing_full_loop_contract_groups"]
    assert receipt["admission"]["full_loop_external_holdout_eligible"] is False
    serialized = output.read_text(encoding="utf-8")
    assert "Private station export" not in serialized
    assert "Vehicle_ID" not in serialized
    assert str(source) not in serialized
    assert json.loads(serialized)["privacy"]["raw_rows_persisted"] is False


def test_intake_rejects_repository_inputs(tmp_path):
    source = ROOT / "tests" / "_should_not_be_read.csv"
    source.write_text("time,pressure\n0,1\n", encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="outside the repository"):
            build_receipt(
                source,
                source_url="https://example.invalid",
                persistent_identifier="test",
                rights="test",
                access_attested=False,
            )
    finally:
        source.unlink(missing_ok=True)


def test_intake_accepts_explicit_station_vehicle_contract_but_keeps_admission_closed(tmp_path):
    source = tmp_path / "scoped_station_export.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append([
        "common_elapsed_s", "vehicle_pressure", "vehicle_temperature",
        "dispenser_pressure", "dispenser_temperature", "mass_flow",
        "cascade_bank", "esd_status", "vehicle_id",
    ])
    sheet.append([0, 5.0, 24.0, 70.0, 20.0, 1.0, "M", "READY", "car-01"])
    workbook.save(source)
    receipt = build_receipt(
        source,
        source_url="https://example.invalid",
        persistent_identifier="test-scoped",
        rights="test",
        access_attested=False,
    )
    assert receipt["aggregate_schema"]["full_loop_contract_channels_co_located_in_one_table"] is True
    assert receipt["aggregate_schema"]["missing_full_loop_contract_groups"] == []
    assert receipt["admission"]["full_loop_external_holdout_eligible"] is False
