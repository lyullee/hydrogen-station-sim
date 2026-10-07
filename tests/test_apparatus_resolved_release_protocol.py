from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "research" / "apparatus_resolved_release_protocol.json"
SECONDARY_PROTOCOL_PATH = ROOT / "research" / "release_network_prospective_protocol.json"
MODEL_PATH = ROOT / "src" / "h2station" / "release_network.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_protocol_is_explicitly_prospective_and_not_a_validation_claim():
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    gate = protocol["promotion_gate"]

    assert protocol["status"] == "PROSPECTIVE_PROTOCOL_SPECIFICATION_ONLY"
    assert gate["full_loop_holdout_eligible"] is False
    assert gate["external_validation_status"] == "NOT_ESTABLISHED"
    assert gate["current_proust_holdout_reused"] is False
    assert gate["goal_completion_permitted"] is False


def test_locked_model_hash_matches_protocol():
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    assert protocol["locked_model"]["path"] == "src/h2station/release_network.py"
    assert protocol["locked_model"]["sha256"] == _sha256(MODEL_PATH)


def test_protocol_requires_apparatus_boundary_channels_and_published_gap():
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    required = {item["name"] for item in protocol["required_channels"] if item["required"]}

    assert {
        "source_pressure_pa_abs",
        "source_temperature_k",
        "line_pressure_pa_abs",
        "line_temperature_k",
        "terminal_mass_flow_kg_s",
        "valve_position_fraction",
        "source_mass_kg",
        "ambient_pressure_pa",
    } <= required
    assert "line pressure" in protocol["known_source_gap"]["not_reported_as_primary_channels"]
    assert "valve position trace" in protocol["known_source_gap"]["not_reported_as_primary_channels"]


def test_protocol_locks_conservation_instrumentation_before_target_data_access():
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))

    assert protocol["protocol_revision"]["target_campaign_outcome_data_accessed"] is False
    assert protocol["protocol_revision"]["physical_trajectory_equations_changed"] is False
    assert protocol["quality_controls"]["energy_closure_relative_tolerance"] == 0.002
    assert protocol["primary_endpoints"]["energy_closure"]["maximum_relative_error"] == 0.002


def test_secondary_protocol_tracks_the_locked_conservation_outputs():
    protocol = json.loads(SECONDARY_PROTOCOL_PATH.read_text(encoding="utf-8"))

    assert protocol["model_sha256"] == _sha256(MODEL_PATH)
    assert {
        "cumulative_terminal_release",
        "cumulative_terminal_enthalpy",
        "cumulative_thermal_boundary_energy",
        "mass_balance_residual",
        "energy_balance_residual",
    } <= set(protocol["model_boundary"]["outputs"])
    assert protocol["numerical_conservation_screens"] == {
        "mass_closure_relative_error_max": 0.002,
        "energy_closure_relative_error_max": 0.002,
        "instrumentation_added_before_target_campaign_outcome_access": True,
        "physical_trajectory_equations_changed": False,
    }


def test_protocol_keeps_nominal_line_volume_as_derived_only():
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    geometry = protocol["source_target"]["derived_geometry"]

    assert geometry["status"] == "derived_from_nominal_dimensions_only"
    assert geometry["line_internal_volume_m3"] > 0.0
    assert "replace it with as-built bore" in geometry["use_rule"]
