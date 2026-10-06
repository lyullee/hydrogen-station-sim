from __future__ import annotations

import json
from pathlib import Path

from scripts.recheck_confidential_station_channel_quality import audit


ROOT = Path(__file__).resolve().parents[1]


def test_channel_quality_recheck_is_aggregate_only(tmp_path):
    source = tmp_path / "trace.csv"
    source.write_text(
        "time,p,t,f,state\n"
        "2025-01-01 00:00:00,40,20,1,READY\n"
        "2025-01-01 00:00:01,41,,2,RUN\n"
        "2025-01-01 00:00:02,42,22,3,RUN\n",
        encoding="utf-8",
    )
    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps({
        "time_column": "time",
        "pressure_columns": [["station_pressure", "p"]],
        "temperature_columns": [["station_temperature", "t"]],
        "flow_columns": ["f"],
        "state_columns": [["valve_state", "state"]],
        "encoding": "utf-8",
        "time_formats": ["%Y-%m-%d %H:%M:%S"],
    }), encoding="utf-8")

    result = audit(tmp_path, mapping, stride=1, max_rows_per_file=100)
    assert result["artifact_type"] == "confidential_station_channel_quality_recheck"
    assert result["files_read"] == 1
    assert result["sampled_rows"] == 3
    assert result["parseable_timestamp_fraction"] == 1.0
    assert result["roles"]["temperature"]["finite_observations"] == 2
    assert result["roles"]["temperature"]["missing_or_non_numeric_observations"] == 1
    assert result["discrete_state_transition_count"] == 1
    assert result["eligibility"]["full_loop_holdout_eligible"] is False
    serialized = json.dumps(result, ensure_ascii=False)
    assert "trace.csv" not in serialized
    assert "2025-01-01" not in serialized
    assert "station_pressure" not in serialized


def test_committed_channel_quality_recheck_keeps_scope_boundary():
    record = json.loads(
        (
            ROOT
            / "research/confidential_station_channel_quality_recheck_2026_10_06.json"
        ).read_text(encoding="utf-8")
    )
    assert record["files_read"] == 8
    assert record["sampled_rows"] == 1092
    assert record["parseable_timestamp_fraction"] == 1.0
    assert record["roles"]["pressure"]["finite_fraction"] == 1.0
    assert record["roles"]["flow"]["finite_fraction"] == 1.0
    assert record["roles"]["temperature"]["finite_fraction"] < 1.0
    assert record["eligibility"]["temperature_or_flow_parameter_fit_supported"] is False
    assert record["eligibility"]["full_loop_holdout_eligible"] is False
