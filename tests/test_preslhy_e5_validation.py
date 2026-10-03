from __future__ import annotations

from io import BytesIO

import numpy as np
from openpyxl import Workbook

from h2station.preslhy_e5_validation import E5_CASES, read_preslhy_e5_workbook


def _workbook_payload() -> bytes:
    workbook = Workbook()
    pressure = workbook.active
    pressure.title = "case-presV"
    pressure.append([])
    pressure.append([])
    pressure.append([])
    pressure.append([])
    pressure.append([])
    pressure.append(["Time [s]", "X_Value", "Druck_Behälter", "Druck_Düse", "Trigger"])
    for time_s in np.linspace(-0.5, 5.0, 221):
        gauge_bar = max(0.0, 50.0 * (1.0 - (time_s + 0.5) / 2.5))
        pressure.append([time_s, time_s, gauge_bar, 0.0, 0.0])
    temperature = workbook.create_sheet("case-TE")
    for _ in range(5):
        temperature.append([])
    temperature.append(
        [
            "Time [s]",
            "X_Value",
            "Behälter_Innen",
            "Behälter_Mitte",
            "Behälter_Aussen",
        ]
    )
    for time_s in np.linspace(-0.5, 5.0, 221):
        temperature.append([time_s, time_s, 300.0, 301.0, 302.0])
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_e5_case_manifest_is_frozen_to_seven_published_runs():
    assert len(E5_CASES) == 7
    ambient = [case for case in E5_CASES if case.nominal_temperature_class == "ambient"]
    assert len(ambient) == 5
    assert {case.nozzle_diameter_mm for case in ambient} == {2.0, 4.0}
    assert {case.nominal_pressure_bar for case in ambient} == {50.0, 200.0}


def test_e5_reader_maps_synchronised_pressure_and_temperature():
    case = E5_CASES[0]
    trace = read_preslhy_e5_workbook(
        _workbook_payload(),
        source_package="synthetic.zip",
        source_member=case.se_member_suffix,
        case=case,
    )
    assert trace.pressure_unit_interpretation.startswith("terminal_near_zero_gauge")
    assert trace.pressure_bar_abs[-1] == 1.01325
    assert trace.initial_temperature_k == 301.0
    assert trace.nozzle_diameter_mm == 4.0
    assert np.any(trace.time_s < 0.0)
    assert np.any(trace.time_s >= 0.1)
