from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

import numpy as np
from openpyxl import Workbook
import pytest

from h2station.public_validation import (
    compare_traces,
    iter_dispersion_experiments,
    iter_mc_default_traces,
    read_mc_default_workbook,
    read_h2protocol_overview,
    read_h2protocol_workbook,
    read_hiad_hrs_cases,
)
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario


def _workbook_bytes(workbook: Workbook) -> bytes:
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def _overview_archive(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append([
        "Fill Number", "Lab Test #", "Test #", "P ", "Tank Size",
        "Chamber Temp", "Fill Rate", "Notes",
    ])
    sheet.append([9, 6, "1-1 B", "70 MPa", "4.7 kg", "-20 C", "12 MPa/min", "cold"])
    sheet.append([31, 29, "9-1 A", "70 MPa", "2x 2.3kg", "+20 C", 21.8, "two vessels"])
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("Test Overview.xlsx", _workbook_bytes(workbook))


def test_h2protocol_reader_handles_source_header_variants_and_active_fill(tmp_path):
    archive = tmp_path / "SAE J2601 Tables Validation Files 1.zip"
    _overview_archive(archive)
    overview = read_h2protocol_overview(archive)
    assert overview["91a"].tank_capacity_kg == pytest.approx(4.6)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "BMW Test 1-1 B, 2012Oct01"
    sheet.append([
        "Elapsed", "SOC %", "FM", "Pinlet", "Tinlet_G", "Tchamber",
        "Ttank1_G (T10)", "Ttank2_G (T11)", "Ttank3_G (T15)",
    ])
    sheet.append([0.0, 5.0, None, 2.0, -38.0, -20.0, 20.0, 21.0, 22.0])
    sheet.append([0.5, 6.0, 5.0, 3.0, -38.0, -20.0, 21.0, 22.0, 23.0])
    sheet.append([1.0, 7.0, 6.0, 4.0, -37.0, -20.0, 22.0, 23.0, 24.0])
    sheet.append([1.5, 8.0, 7.0, 5.0, -36.0, -20.0, 23.0, 24.0, 25.0])
    sheet.append([2.0, 9.0, None, 6.0, -36.0, -20.0, 24.0, 25.0, 26.0])
    sheet.append([None, None, None, "formatted trailing row", None, None, None, None, None])

    trace = read_h2protocol_workbook(
        _workbook_bytes(workbook),
        source_archive=archive.name,
        source_member="test.xlsx",
        overview=overview,
    )
    assert trace.case_id == "H2P-L06"
    assert trace.metadata.lab_test_number == 6
    assert trace.metadata.tank_capacity_kg == pytest.approx(4.7)
    assert trace.pressure_source == "Pinlet"
    assert trace.time_s.tolist() == pytest.approx([0.0, 0.5, 1.0])
    assert trace.tank_temperature_mean_c.tolist() == pytest.approx([22.0, 23.0, 24.0])


def test_compare_traces_uses_experimental_clock_without_time_warping():
    agreement = compare_traces(
        experimental_time_s=[0, 1, 2],
        experimental_pressure_mpa=[2, 4, 6],
        experimental_temperature_c=[20, 22, 24],
        experimental_soc_percent=[5, 10, 15],
        predicted_time_s=[0, 2],
        predicted_pressure_mpa=[2, 8],
        predicted_temperature_c=[20, 26],
        predicted_soc_percent=[5, 20],
    )
    assert agreement.pressure_mae_mpa == pytest.approx(1.0)
    assert agreement.pressure_rmse_mpa == pytest.approx(np.sqrt(5 / 3))
    assert agreement.temperature_mae_c == pytest.approx(1.0)
    assert agreement.soc_final_error_percentage_points == pytest.approx(5.0)


def test_mc_default_reader_preserves_protocol_schedule_and_source_pressures():
    workbook = Workbook()
    measurement = workbook.active
    measurement.title = "MC Validation Test 1-A"
    measurement.append([
        "Time (s)", "SOC (%)", "875PT1", "875PT3", "Pinlet", "FM",
        "Tinlet_G", "Ttank1_G", "Ttank2_G", "Ttank3_G", "Tchamber",
    ])
    for index, flow in enumerate((0.0, 2.0, 3.0, 4.0, 0.0)):
        measurement.append([
            float(index), 5.0 + index, 88.0 - index, 89.0 - index,
            2.0 + index, flow, -35.0, 20.0 + index, 21.0 + index,
            22.0 + index, 40.0,
        ])
    schedule = workbook.create_sheet("Sheet1")
    schedule.append(["Time", "Pressure"])
    schedule.append([0.0, 2.0])
    schedule.append([300.0, 82.0])

    trace = read_mc_default_workbook(
        _workbook_bytes(workbook),
        source_archive="mc.zip",
        source_member="MC Default Validation Test 1-A, 2013Aug01.xlsx",
    )
    assert trace.case_id == "H2P-MC-1-A"
    assert trace.metadata.tank_capacity_kg == pytest.approx(4.7)
    assert trace.time_s.tolist() == pytest.approx([0.0, 1.0, 2.0])
    assert trace.source_pressure_1_mpa.tolist() == pytest.approx([87.0, 86.0, 85.0])
    assert trace.protocol_pressure_mpa.tolist() == pytest.approx([2.0, 82.0])
    assert trace.summary()["protocol_effective_aprr_mpa_min"] == pytest.approx(16.0)


def test_mc_default_iterator_requires_every_frozen_member(tmp_path):
    archive = tmp_path / "mc.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("unrelated.txt", "data")
    with pytest.raises(ValueError, match="archive is missing"):
        list(iter_mc_default_traces(archive, ["frozen.xlsx"]))


def test_hiad_reader_joins_sheets_and_filters_core_hrs_cases(tmp_path):
    workbook = Workbook()
    workbook.remove(workbook.active)

    def add_sheet(name, headers, rows):
        sheet = workbook.create_sheet(name)
        sheet.append(headers)
        for row in rows:
            sheet.append(row)

    add_sheet("EVENTS", [
        "Event ID", "Q", "Event Title", "Event full description",
        "Event Initiating system", "Classification of the physical effects",
        "Nature of the consequences", "Summary root causes",
    ], [
        [2, "Q2", "HRS leak", "Hose released hydrogen", "Dispenser", "Leak", "Near miss", "Seal"],
        [10, "Q3", "Other", "Unrelated process", "Pipe", "Leak", "None", "Joint"],
    ])
    add_sheet("FACILITY", [
        "Event ID", "Application", "Sub-application", "Hydrogen supply chain stage",
        "Operational condition", "Event Title", "Event full description",
    ], [
        [2, "Hydrogen refuelling station", "Road vehicle", "Distribution", "Fuelling", "", ""],
        [10, "Chemical plant", "Process", "Production", "Operating", "", ""],
    ])
    add_sheet("LESSONS LEARNT", ["Event ID", "Lesson Learnt", "Corrective Measures"], [
        [2, "Verify coupling", "Replace seal"], [10, "Other", "Other"],
    ])
    add_sheet("EVENT NATURE", ["Event ID", "Emergency action"], [
        [2, "Stop fuelling and isolate"], [10, "Stop"],
    ])
    add_sheet("REFERENCES", ["Event ID", "1st Reference & weblink"], [
        [2, "https://example.test/2"], [10, "https://example.test/10"],
    ])
    add_sheet("CONSEQUENCES", ["Event ID"], [[2], [10]])
    path = tmp_path / "HIAD 2.2.xlsx"
    workbook.save(path)

    cases = read_hiad_hrs_cases(path)
    assert [case.event_id for case in cases] == ["2"]
    assert cases[0].emergency_action == "Stop fuelling and isolate"
    assert cases[0].lesson_learnt == "Verify coupling"
    assert cases[0].corrective_measures == "Replace seal"
    assert cases[0].references == ("https://example.test/2",)


def test_reference_scenario_supports_independent_experimental_tank_volumes():
    built = build_reference_scenario(
        ReferenceScenario(
            vehicle_internal_volume_m3=0.060,
            vehicle_2_internal_volume_m3=0.180,
            vehicle_effective_volume_multiplier=1.05,
            vehicle_gas_liner_ua_multiplier=2.5,
        ),
        UnavailableHyRAMBackend(),
    )
    first = built.station.partial_station.vehicle_tank
    second = built.station.secondary_partial_station.vehicle_tank
    assert first.parameters.internal_volume_m3 == pytest.approx(0.060)
    assert second.parameters.internal_volume_m3 == pytest.approx(0.180)
    assert first.effective_volume_m3 == pytest.approx(0.060 * 1.05)
    assert first.fit.gas_liner_ua_multiplier == pytest.approx(2.5)
    assert second.fit == first.fit
    assert (
        built.initial_state.secondary_partial_station.vehicle.hydrogen_mass_kg
        > built.initial_state.partial_station.vehicle.hydrogen_mass_kg
    )


def test_reference_scenario_rejects_nonpositive_experimental_tank_volume():
    with pytest.raises(ValueError, match="tank volumes"):
        build_reference_scenario(
            ReferenceScenario(vehicle_internal_volume_m3=0.0),
            UnavailableHyRAMBackend(),
        )


def test_reference_scenario_rejects_nonpositive_tank_fit_multiplier():
    with pytest.raises(ValueError, match="fit multipliers"):
        build_reference_scenario(
            ReferenceScenario(vehicle_gas_liner_ua_multiplier=0.0),
            UnavailableHyRAMBackend(),
        )


def test_dispersion_reader_uses_declared_steady_interval_and_clips_sensor_noise(tmp_path):
    (tmp_path / "ReadMe.txt").write_text(
        "23_FFI_P101_T00001 - test-01-0\n", encoding="utf-8"
    )
    csv_text = (
        ",mass flow meter 1,filling pressure sensor,various data,"
        "h2 sensor time,sensor 1 h2 concentration [%],sensor 2 h2 concentration [%]\n"
        "0,species - h2,mean pressure [bar] - 2.5,total,0,-0.1,-0.2\n"
        "1,mean mass flow - 0.5,std,mean channel temperature [C] - 25,10,1,2\n"
        "2,mass fraction - 1,,baseline duration [s] - 30,50,3,5\n"
        "3,logging frequency,,filling duration [s] - 30,55,4,6\n"
        "4,,,,60,5,7\n"
    )
    archive = tmp_path / "23_FFI_P101_T00001.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("case/case.csv", csv_text)
    experiment = list(iter_dispersion_experiments(tmp_path))[0]
    summary = experiment.summary()
    assert experiment.article_test_id == "test-01-0"
    assert experiment.mean_mass_flow_g_s == pytest.approx(0.5)
    assert experiment.mean_filling_pressure_bar == pytest.approx(2.5)
    assert summary["steady_interval_start_s"] == pytest.approx(50.0)
    assert summary["steady_mean_concentration_percent"] == pytest.approx(5.0)
    assert summary["steady_peak_concentration_percent"] == pytest.approx(7.0)
    assert summary["steady_lfl_exceedance_fraction"] == pytest.approx(5 / 6)
