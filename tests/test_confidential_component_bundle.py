from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.export_confidential_component_bundle import export_component_bundle


ROOT = Path(__file__).resolve().parents[1]


def _write_fixture(tmp_path: Path) -> tuple[list[Path], Path, Path]:
    inputs: list[Path] = []
    for event in range(3):
        path = tmp_path / f"private_event_{event}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["clock", "p", "t", "flow", "phase"])
            for index in range(20):
                writer.writerow([index * 0.5, 20.0 + index * 0.1, 25.0 + index * 0.02, 4.0, "fill" if index else "start"])
        inputs.append(path)
    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps({"schema_version": 1, "column_map": {"time_s": "clock", "station_pressure_mpa_abs": "p", "boundary_temperature_degC": "t", "mass_flow_g_s": "flow", "protocol_phase": "phase"}}), encoding="utf-8")
    attestation = tmp_path / "attestation.json"
    attestation.write_text(json.dumps({"schema_version": 1, "authorised_controlled_evaluation": True, "outcomes_accessed_before_protocol_freeze": False, "units": {"station_pressure_mpa_abs": "MPa_abs", "boundary_temperature_degC": "degC", "mass_flow_g_s": "g/s"}}), encoding="utf-8")
    return inputs, mapping, attestation


def test_component_bundle_exports_three_events_without_source_identity(tmp_path: Path) -> None:
    inputs, mapping, attestation = _write_fixture(tmp_path)
    output = tmp_path / "export"
    receipt = export_component_bundle(
        inputs, mapping, attestation, output,
        ROOT / "research/external_hrs_component_intake_protocol.json",
    )
    assert receipt["component_bundle_ready"] is True
    assert receipt["event_count"] == 3
    assert receipt["full_loop_holdout_eligible"] is False
    assert receipt["runtime_parameter_application"] is False
    assert "private_event_0.csv" not in json.dumps(receipt)
    assert (output / "component_event_001.csv").is_file()
    assert len(list(output.glob("component_event_*.csv"))) == 3


def test_component_bundle_rejects_fewer_than_three_events(tmp_path: Path) -> None:
    inputs, mapping, attestation = _write_fixture(tmp_path)
    with pytest.raises(ValueError, match="at least 3 events"):
        export_component_bundle(
            inputs[:2], mapping, attestation, tmp_path / "export",
            ROOT / "research/external_hrs_component_intake_protocol.json",
        )
