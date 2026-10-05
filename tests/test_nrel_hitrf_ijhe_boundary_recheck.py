import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_nrel_hitrf_published_curve_boundary_is_traceable_and_not_promoted():
    record = json.loads(
        (
            ROOT
            / "research/nrel_hitrf_ijhe_published_curve_boundary_recheck_2026_10_05.json"
        ).read_text(encoding="utf-8")
    )
    assert record["source"]["doi"] == "10.1016/j.ijhydene.2023.12.056"
    assert record["source"]["pdf_sha256"]
    assert record["reported_experiment"]["duration_s"] == 195
    assert record["access_observation"]["raw_nrel_logger_retrieved"] is False
    assert record["access_observation"]["machine_readable_synchronized_rows_public"] is False
    assert record["classification"]["full_loop_station_vehicle_holdout_eligible"] is False
    assert record["classification"]["goal_completion_permitted"] is False
