from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from inspect_privacy_safe_event import inspect_event  # noqa: E402


def _event(path: Path) -> None:
    path.write_text(
        "elapsed_time_s,station_pressure_mpa,delivered_gas_temperature_c,"
        "mass_flow_g_s,protocol_phase\n"
        "0,20,20,1,start\n"
        "1,21,21,1.2,fill\n",
        encoding="utf-8",
    )


def test_single_event_preview_is_raw_row_free_and_does_not_claim_validation(
    tmp_path: Path,
) -> None:
    event = tmp_path / "operator-export.csv"
    _event(event)

    report = inspect_event(event)

    assert report["artifact_type"] == "privacy_safe_single_event_schema_preview"
    assert report["status"] == "READY_FOR_PROTOCOL_FREEZE"
    assert report["claim_boundary"].startswith("Schema preview only")
    serialized = json.dumps(report, ensure_ascii=False)
    assert "operator-export.csv" not in serialized
    assert str(tmp_path) not in serialized
    assert '"protocol_phase": "start"' not in serialized


def test_single_event_preview_can_require_vehicle_channels(tmp_path: Path) -> None:
    event = tmp_path / "operator-export.csv"
    _event(event)

    report = inspect_event(event, require_vehicle_boundary=True)

    assert report["status"] == "SCHEMA_INCOMPLETE"
    assert "missing_vehicle_boundary_channel" in report["event_reports"][0]["errors"]
