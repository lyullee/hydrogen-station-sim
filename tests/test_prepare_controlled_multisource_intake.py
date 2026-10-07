from __future__ import annotations

import json
import sys
from pathlib import Path

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_controlled_multisource_intake import prepare_workbench  # noqa: E402


def test_private_workbench_writes_mapping_templates_without_measurement_values(
    tmp_path: Path,
):
    source = tmp_path / "private-event.xlsx"
    workbook = Workbook()
    vehicle = workbook.active
    vehicle.title = "private vehicle sheet"
    vehicle.append(["private time", "private pressure", "private temperature", "private flow"])
    vehicle.append([0, 12.0, 20.0, 2.0])
    vehicle.append([1, 12.0, 20.0, 2.0])
    station = workbook.create_sheet("private station sheet")
    station.append(["private clock", "private cascade pressure", "private compressor state"])
    station.append([0, 70.0, "running"])
    station.append([1, 70.0, "running"])
    workbook.save(source)

    output = tmp_path / "private-workbench"
    receipt = prepare_workbench(source, output)
    catalog = json.loads((output / "private_source_catalog.json").read_text(encoding="utf-8"))
    mapping = json.loads((output / "event-mapping.template.json").read_text(encoding="utf-8"))
    attestation = json.loads((output / "event-attestation.template.json").read_text(encoding="utf-8"))
    rendered_receipt = json.dumps(receipt)

    assert receipt["source_count"] == 2
    assert receipt["measurement_values_persisted"] is False
    assert catalog["sample_data_rows_structurally_inspected_in_memory"] is True
    assert catalog["measurement_values_persisted"] is False
    assert catalog["sources"][0]["original_headers"][0] == "private time"
    assert mapping["sources"][0]["time_column"] == "<select one time_column_candidate>"
    assert mapping["sources"][0]["event_group_token"].startswith("<custodian-approved")
    assert attestation["authorised_controlled_evaluation"] is False
    assert attestation["source_synchronization"]["same_physical_event_confirmed"] is False
    assert attestation["temperature_observation"]["vehicle_temperature_degC"]["sensor_location_verified"] is False
    assert "private vehicle sheet" not in rendered_receipt
    assert "do-not-persist" not in catalog["sources"][0]["original_headers"]


def test_private_workbench_catalogs_declared_csv_directory_sources(tmp_path: Path):
    controlled = tmp_path / "private-logger-directory"
    controlled.mkdir()
    (controlled / "private-logger.csv").write_text(
        "LocalTimeCol,COMP.AI.PT_201,COMP.AI.TT_201,FQI_0001\n"
        "0,1,2,3\n"
        "1,1,2,3\n",
        encoding="utf-16",
    )

    output = tmp_path / "private-directory-workbench"
    receipt = prepare_workbench(controlled, output)
    catalog = json.loads((output / "private_source_catalog.json").read_text(encoding="utf-8"))
    mapping = json.loads((output / "event-mapping.template.json").read_text(encoding="utf-8"))

    assert receipt["input_kind"] == "directory"
    assert catalog["source_count"] == 1
    assert catalog["sources"][0]["file"] == "private-logger.csv"
    assert "worksheet" not in mapping["sources"][0]
    assert "private-logger.csv" not in json.dumps(receipt)
