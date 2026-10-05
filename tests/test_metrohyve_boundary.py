import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_metrohyve_boundary_is_component_only():
    record = json.loads((ROOT / "research/metrohyve_gravimetric_hrs_calibration_boundary_2026_10_05.json").read_text(encoding="utf-8"))
    assert record["source"]["doi"] == "10.1016/j.flowmeasinst.2020.101743"
    assert "CC BY-NC-ND 4.0" in record["source"]["license"]
    assert record["observed_scope"]["real_hrs_field_tests"] is True
    assert record["observed_scope"]["maximum_pressure_bar"] == 875
    assert record["eligibility"]["component_flow_metrology_eligible"] is True
    assert record["eligibility"]["full_loop_external_holdout_eligible"] is False
    assert record["access_recheck"]["raw_machine_readable_station_logger_found"] is False
    assert record["goal_completion_permitted"] is False


def test_data_source_catalog_preserves_metrohyve_boundary():
    catalog = json.loads((ROOT / "research/data_sources.json").read_text(encoding="utf-8"))
    source = catalog["sources"]["metrohyve_gravimetric_hrs_calibration_2020"]
    assert source["component_flow_metrology_eligible"] is True
    assert source["full_loop_holdout_eligible"] is False
    assert source["boundary_record"].endswith("metrohyve_gravimetric_hrs_calibration_boundary_2026_10_05.json")
