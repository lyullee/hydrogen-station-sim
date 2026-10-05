import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from intake_external_hrs_bundle import build_manifest  # noqa: E402
from validate_external_hrs_manifest import validate  # noqa: E402


REQUIRED_CHANNELS = {
    "common_time_base": {"present": True},
    "vehicle_or_receptacle_pressure": {"present": True, "unit": "MPa_abs"},
    "gas_or_tank_temperature": {"present": True, "unit": "degC"},
    "mass_flow_or_transferred_mass": {"present": True, "unit": "g/s"},
}
REQUIRED_METADATA = {
    "initial_conditions": True,
    "tank_capacity_or_geometry": True,
    "protocol_mode_or_pressure_ramp": True,
    "source_cascade_state": True,
    "compressor_state": True,
    "precooler_state": True,
    "stop_abort_fault_markers": True,
    "quality_and_calibration_metadata": True,
    "reuse_terms": "research reuse permitted",
    "units_and_sampling_interval": "declared",
    "source_identity": "dataset-id",
    "custodian_or_archive": "custodian",
    "acquired_at_utc": "2026-10-05T00:00:00Z",
    "license_or_reuse_reference": "license-url",
}


def _write_inputs(tmp_path: Path, *, remove_channel: str | None = None):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    # The checker must never open or parse this file.
    (bundle / "trace.csv").write_text("time,pressure\n0,999999\n", encoding="utf-8")
    protocol = ROOT / "research/external_hrs_intake_protocol.json"
    manifest = build_manifest(bundle, protocol)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    declaration = {
        "declaration_type": "external_hrs_bundle_metadata",
        "outcomes_accessed_before_freeze": False,
        "channels": dict(REQUIRED_CHANNELS),
        "metadata": dict(REQUIRED_METADATA),
    }
    if remove_channel:
        declaration["channels"].pop(remove_channel, None)
    declaration_path = tmp_path / "declaration.json"
    declaration_path.write_text(json.dumps(declaration), encoding="utf-8")
    return manifest_path, declaration_path, protocol


def test_metadata_gate_accepts_complete_declaration_without_reading_trace(tmp_path):
    manifest, declaration, protocol = _write_inputs(tmp_path)
    report = validate(manifest, declaration, protocol)
    assert report["decision"] == "ELIGIBLE_FOR_PROSPECTIVE_MAPPING"
    assert report["eligible_for_numerical_evaluation"] is True
    assert report["numerical_values_inspected"] is False
    assert report["reasons"] == []


def test_metadata_gate_retains_missing_channel_as_ineligible(tmp_path):
    manifest, declaration, protocol = _write_inputs(
        tmp_path, remove_channel="vehicle_or_receptacle_pressure"
    )
    report = validate(manifest, declaration, protocol)
    assert report["decision"] == "INELIGIBLE_MISSING_METADATA"
    assert report["eligible_for_numerical_evaluation"] is False
    assert "missing required channel or unit: vehicle_or_receptacle_pressure" in report["reasons"]


def test_metadata_gate_rejects_outcome_access_before_freeze(tmp_path):
    manifest, declaration, protocol = _write_inputs(tmp_path)
    value = json.loads(declaration.read_text(encoding="utf-8"))
    value["outcomes_accessed_before_freeze"] = True
    declaration.write_text(json.dumps(value), encoding="utf-8")
    report = validate(manifest, declaration, protocol)
    assert report["eligible_for_numerical_evaluation"] is False
    assert "metadata declaration does not prove pre-outcome freezing" in report["reasons"]


def test_metadata_gate_rechecks_quarantined_bytes_without_parsing_trace(tmp_path):
    manifest, declaration, protocol = _write_inputs(tmp_path)
    trace = tmp_path / "bundle" / "trace.csv"
    trace.write_text("time,pressure\n0,123\n", encoding="utf-8")
    report = validate(manifest, declaration, protocol)
    assert report["eligible_for_numerical_evaluation"] is False
    assert report["integrity"]["records_hash_verified"] == 0
    assert any(
        "byte count does not match" in reason
        or "SHA-256 does not match" in reason
        for reason in report["reasons"]
    )


def test_metadata_gate_rejects_manifest_path_traversal(tmp_path):
    manifest, declaration, protocol = _write_inputs(tmp_path)
    value = json.loads(manifest.read_text(encoding="utf-8"))
    value["files"][0]["relative_path"] = "../trace.csv"
    manifest.write_text(json.dumps(value), encoding="utf-8")
    report = validate(manifest, declaration, protocol)
    assert report["eligible_for_numerical_evaluation"] is False
    assert "intake file record 0 has an unsafe relative_path" in report["reasons"]
