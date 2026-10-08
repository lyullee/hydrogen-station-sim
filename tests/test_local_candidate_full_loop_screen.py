import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research" / "local_candidate_full_loop_screen_2026_10_09.json"


def test_local_candidate_screen_keeps_partial_and_simulated_sources_bounded():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["artifact_type"] == "local_candidate_full_loop_screen"
    assert record["coverage_assessment"]["local_station_data_is_sparse"] is False
    assert record["coverage_assessment"]["full_loop_holdout_eligible"] is False
    candidates = {item["id"]: item for item in record["candidates"]}
    assert candidates["local_confidential_station_measurement_bundle"]["decision"] == "STATION_SIDE_ONLY"
    assert candidates["nrel_h2fills_2022_hdvs_typeiv"]["decision"] == "PARTIAL_TANK_BOUNDARY_ONLY"
    assert candidates["dtu_tes_hydrogen_fuelling_station_v2_1"]["decision"] == "SIMULATOR_REFERENCE_ONLY"
    assert candidates["dtu_tes_hydrogen_fuelling_station_v2_1"]["measured_time_series_present"] is False
    assert "station-to-vehicle full-loop validation" in candidates[
        "nrel_h2fills_2022_hdvs_typeiv"
    ]["ineligible_use"]
