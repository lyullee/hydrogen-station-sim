from __future__ import annotations

from io import BytesIO

import numpy as np
from openpyxl import Workbook
import pytest

from h2station.preslhy_partb_validation import (
    CRYOSTAT_VOLUME_M3,
    read_preslhy_partb_workbook,
)


def _workbook_bytes() -> bytes:
    workbook = Workbook()
    release = workbook.active
    release.title = "20200520-000000-W01-VD10"
    release.append([None, "record", "P-Vessel", "P-Nozzle"])
    release.append([None, "Date", None, None])
    release.append([None, "Time", None, None])
    release.append([None, "Unit", "bar", "bar"])
    release.append([None, "dt", 0.01, 0.01])
    release.append(["Time new [s]", "X_Value", "P-Innen", "P-Duese"])
    release.append([])
    for time_s in np.arange(-1.0, 2.0, 0.01):
        nozzle = 0.0 if time_s < 0.0 else 3.0
        pressure = 4.0 - 0.8 * max(time_s, 0.0)
        release.append([float(time_s), float(time_s), pressure, nozzle])
    temperature = workbook.create_sheet("20200520-000001-W01-TE")
    temperature.append([None, "Thermoelemente", "Cryo-1", "Cryo-2", "Cryo-3"])
    temperature.append([None, "Date"])
    temperature.append([None, "Time"])
    temperature.append([None, "Unit", "Kelvin", "Kelvin", "Kelvin"])
    temperature.append([None, "dt"])
    temperature.append(["Time new [s]", "X_Value", "Cryo-1", "Cryo-2", "Cryo-3"])
    temperature.append([])
    for time_s in np.arange(-1.0, 2.0, 0.01):
        temperature.append([float(time_s), float(time_s), 300.0, 301.0, 302.0])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_partb_reader_uses_published_cryostat_volume_and_event_channel():
    trace = read_preslhy_partb_workbook(
        _workbook_bytes(),
        source_package="preslhy_partb_xlsx",
        source_member="20200520-000000_290K-2mm-5bar_W01-Final.xlsx",
    )
    assert CRYOSTAT_VOLUME_M3 == pytest.approx(0.225)
    assert trace.nozzle_diameter_mm == pytest.approx(2.0)
    assert trace.initial_pressure_pa == pytest.approx(5.01325e5)
    assert trace.initial_temperature_k == pytest.approx(301.0)
    assert trace.pressure_unit_interpretation == "header_gauge_plus_standard_ambient"
    assert np.min(trace.time_s) < 0.0
    assert np.count_nonzero(trace.time_s >= 0.0) >= 20
