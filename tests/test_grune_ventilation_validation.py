from pathlib import Path

import pytest
from openpyxl import Workbook

from h2station.public_validation import read_grune_ventilation_workbook


def _grune_workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "1 mm 1g H2 W = 1.5 co-flow"
    sheet.cell(row=7, column=4).value = "Pu/mbar"
    sheet.cell(row=7, column=5).value = "Tu / C"
    sheet.cell(row=7, column=6).value = "H2 [g/s]"
    sheet.cell(row=7, column=7).value = "nach V [bar]"
    sheet.cell(row=7, column=10).value = "x/ mm"
    sheet.cell(row=7, column=22).value = "x/ mm"
    sheet.cell(row=7, column=34).value = "x/ mm"
    for offset, y in enumerate((-175, 0, 175)):
        sheet.cell(row=7, column=11 + offset).value = y
        sheet.cell(row=7, column=23 + offset).value = y
        sheet.cell(row=7, column=35 + offset).value = y
    # The published layout has nine y-columns in each block.  Keep the
    # remaining columns present so the fixture exercises the same schema gate.
    sheet.cell(row=7, column=43).value = 175
    for row, x in enumerate((125, 250), start=8):
        sheet.cell(row=row, column=4).value = 10.0
        sheet.cell(row=row, column=5).value = 20.0
        sheet.cell(row=row, column=6).value = 1.02
        sheet.cell(row=row, column=7).value = 3.0
        sheet.cell(row=row, column=10).value = x
        for offset in range(3):
            sheet.cell(row=row, column=11 + offset).value = 1.0 + offset
            sheet.cell(row=row, column=23 + offset).value = 2.0 + offset
            sheet.cell(row=row, column=35 + offset).value = 0.5 + offset
    workbook.save(path)


def test_grune_reader_preserves_spatial_columns_and_metadata(tmp_path):
    path = tmp_path / "HTE2440PS001MIXED_300321.xlsx"
    _grune_workbook(path)

    profiles = read_grune_ventilation_workbook(path)

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.release_diameter_mm == pytest.approx(1.0)
    assert profile.nominal_release_g_s == pytest.approx(1.0)
    assert profile.wind_speed_m_s == pytest.approx(1.5)
    assert profile.wind_mode == "co-flow"
    assert len(profile.points) == 6
    assert profile.points[0].x_mm == pytest.approx(125.0)
    assert profile.points[0].y_mm == pytest.approx(-175.0)
    assert profile.points[0].concentration_average_pct == pytest.approx(1.0)
    assert profile.points[-1].concentration_maximum_pct == pytest.approx(4.0)
    assert profile.summary()["point_count"] == 6
