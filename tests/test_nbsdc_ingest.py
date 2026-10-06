from io import BytesIO

import numpy as np
import pytest
from openpyxl import Workbook

from h2station.nbsdc_ingest import NbsdcColumnMap, read_nbsdc_workbook
from h2station.validation import OutputChannel


def _workbook_bytes(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Time", "Pressure", "Bottle temperature", "Flow", "Mass"])
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_nbsdc_reader_converts_units_and_keeps_relative_clock(tmp_path):
    path = tmp_path / "approved.xlsx"
    path.write_bytes(_workbook_bytes([
        ["2025-01-01T00:00:00", 20.0, 25.0, 60.0, 0.0],
        ["2025-01-01T00:00:01", 21.0, 26.0, 66.0, 0.0183333333],
        ["2025-01-01T00:00:02", 22.0, 27.0, 72.0, 0.0383333333],
    ]))
    trace = read_nbsdc_workbook(
        path,
        NbsdcColumnMap(
            time="Time",
            pressure="Pressure",
            pressure_unit="MPa",
            temperature="Bottle temperature",
            temperature_unit="C",
            mass_flow="Flow",
            mass_flow_unit="kg/min",
            transferred_mass="Mass",
            transferred_mass_unit="kg",
        ),
        case_id="NBS-TEST-01",
        source="approved-sha256:test",
    )
    assert trace.time_s.tolist() == pytest.approx([0.0, 1.0, 2.0])
    assert trace.pressure_pa.tolist() == pytest.approx([20e6, 21e6, 22e6])
    assert trace.temperature_k.tolist() == pytest.approx([298.15, 299.15, 300.15])
    assert trace.mass_flow_kg_s.tolist() == pytest.approx([1.0, 1.1, 1.2])
    assert trace.transferred_mass_kg.tolist() == pytest.approx([0.0, 0.0183333333, 0.0383333333])
    assert trace.summary()["median_sample_period_s"] == pytest.approx(1.0)
    traces = trace.validation_traces()
    assert traces[OutputChannel.VEHICLE_GAS_PRESSURE].unit == "Pa"
    assert traces[OutputChannel.DISPENSED_MASS_FLOW].values.tolist() == pytest.approx([1.0, 1.1, 1.2])


def test_nbsdc_reader_rejects_duplicate_timestamps(tmp_path):
    path = tmp_path / "duplicate.xlsx"
    path.write_bytes(_workbook_bytes([
        [0.0, 20.0, 25.0, 60.0, 0.0],
        [0.0, 20.1, 25.1, 61.0, 0.01],
        [1.0, 21.0, 26.0, 62.0, 0.02],
    ]))
    with pytest.raises(ValueError, match="duplicate timestamps"):
        read_nbsdc_workbook(
            path,
            NbsdcColumnMap(time="Time", pressure="Pressure", pressure_unit="MPa"),
            case_id="NBS-TEST-02",
            source="approved-sha256:test",
        )


def test_nbsdc_column_map_rejects_unknown_units():
    with pytest.raises(ValueError, match="unsupported unit"):
        NbsdcColumnMap(time="t", pressure="p", pressure_unit="psi")
