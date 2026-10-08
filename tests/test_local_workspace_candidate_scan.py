from __future__ import annotations

import json
from pathlib import Path

from scripts.scan_local_workspace_candidates import scan_workspace


def test_workspace_scan_is_aggregate_only(tmp_path: Path) -> None:
    (tmp_path / "vehicle_trace.csv").write_text(
        "time,vehicle_pressure,vehicle_temperature,flow\n"
        "0,1,20,0\n",
        encoding="utf-8",
    )
    (tmp_path / "notes.md").write_text("station notes", encoding="utf-8")

    result = scan_workspace([tmp_path])

    assert result["scan"]["machine_readable_files"] == 2
    assert result["scan"]["path_keyword_candidates"] == 1
    assert result["scan"]["csv_tsv_headers_screened"] == 1
    assert result["scan"]["header_family_candidate_counts"]["vehicle_or_dispenser"] == 1
    assert result["scan"]["coarse_candidate_classes"][
        "vehicle_pressure_temperature_candidate"
    ] == 1
    assert result["eligibility"]["full_loop_candidate_count"] == 0
    assert all(value is False for value in result["privacy"].values())

    serialized = json.dumps(result, ensure_ascii=False)
    assert str(tmp_path) not in serialized
    assert "vehicle_trace.csv" not in serialized
    assert "vehicle_pressure,vehicle_temperature" not in serialized


def test_workspace_scan_skips_virtualenv_and_build_outputs(tmp_path: Path) -> None:
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "hidden.csv").write_text("pressure\n1\n", encoding="utf-8")
    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "hidden.csv").write_text("pressure\n1\n", encoding="utf-8")

    result = scan_workspace([tmp_path])

    assert result["scan"]["machine_readable_files"] == 0


def test_release_rig_nozzle_trace_is_not_classified_as_vehicle_loop(tmp_path: Path) -> None:
    (tmp_path / "release_rig.csv").write_text(
        "Time,PT1ReleaseRig,PT2Nozzle\n0,10,9\n", encoding="utf-8"
    )

    result = scan_workspace([tmp_path])

    classes = result["scan"]["coarse_candidate_classes"]
    assert classes["release_rig_experiment_candidate"] == 1
    assert classes.get("vehicle_pressure_temperature_candidate", 0) == 0
