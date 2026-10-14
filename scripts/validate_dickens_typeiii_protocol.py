"""Validate the pre-access contract for a fresh Dickens Type-III trace.

This checker validates only the prospective protocol and its data contract.  It
does not open a measurement archive, run the tank model, or promote any
scientific validation gate.  A valid contract is therefore a readiness result,
not an accuracy result.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_PROTOCOL = Path(
    "research/dickens_typeiii_geometry_resolved_prospective_protocol_2026_10_10.json"
)

REQUIRED_CHANNELS = {
    "time_s",
    "mass_flow_kg_s",
    "inlet_pressure_mpa",
    "inlet_temperature_k",
    "tank_pressure_mpa",
    "mean_gas_temperature_k",
    "ambient_temperature_k",
    "sampling_and_quality",
    "initial_conditions",
    "geometry_and_materials",
}

REQUIRED_SCREENS = {
    "pressure_nrmse_percent_measured_span_max",
    "pressure_rmse_mpa_max",
    "gas_temperature_rmse_k_max",
    "gas_temperature_peak_absolute_error_k_max",
    "joint_rule",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_protocol(protocol_path: Path) -> dict[str, Any]:
    """Return a fail-closed, non-numerical protocol readiness decision."""

    protocol = _load_object(protocol_path)
    reasons: list[str] = []

    if protocol.get("artifact_type") != "pre_access_geometry_resolved_prospective_protocol":
        reasons.append("artifact is not the geometry-resolved prospective Type-III protocol")
    if protocol.get("status") != "pre_access_request":
        reasons.append("protocol is not in pre-access request status")
    if protocol.get("outcome_access_status") != "awaiting_new_custodian_trace":
        reasons.append("protocol does not require a fresh custodian trace")
    if protocol.get("evidence_role") != "prospective_protocol_only":
        reasons.append("protocol evidence role is not prospective-only")

    declarations = protocol.get("pre_access_declarations")
    if not isinstance(declarations, dict):
        reasons.append("pre-access declarations are missing")
        declarations = {}
    required_false = {
        "numerical_outcomes_seen_for_this_protocol",
        "new_trace_selected_before_outcome_access",
        "model_parameters_fitted_to_outcome",
        "case_specific_multiplier_allowed",
        "same_archive_reuse_for_confirmatory_claim",
    }
    for field in sorted(required_false):
        if declarations.get(field) is not False:
            reasons.append(f"pre-access declaration is not false: {field}")
    for field in ("time_resolved_inlet_temperature_required", "tank_length_mapping_required", "failure_retention_required"):
        if declarations.get(field) is not True:
            reasons.append(f"required safeguard is not enabled: {field}")

    contract = protocol.get("required_input_contract")
    if not isinstance(contract, dict):
        reasons.append("required input contract is missing")
        contract = {}
    missing_channels = sorted(REQUIRED_CHANNELS - set(contract))
    if missing_channels:
        reasons.append("required input contract is missing: " + ", ".join(missing_channels))

    screens = protocol.get("primary_screens")
    if not isinstance(screens, dict):
        reasons.append("primary screens are missing")
        screens = {}
    missing_screens = sorted(REQUIRED_SCREENS - set(screens))
    if missing_screens:
        reasons.append("primary screens are missing: " + ", ".join(missing_screens))
    if screens.get("joint_rule") != (
        "All four screens must pass for a case to count as a joint pass; a failed or incomplete case is retained."
    ):
        reasons.append("joint screen does not retain failed or incomplete cases")

    geometry = protocol.get("geometry_to_freeze_before_outcome_access")
    if not isinstance(geometry, dict):
        reasons.append("geometry freeze contract is missing")
        geometry = {}
    inlet = geometry.get("inlet_pipe_internal_diameter_m")
    if not isinstance(inlet, dict) or inlet.get("value") != 0.005 or inlet.get("status") != "source_confirmed":
        reasons.append("inlet internal diameter is not source-confirmed at 0.005 m")
    tank_length = geometry.get("tank_internal_length_m")
    if not isinstance(tank_length, dict) or tank_length.get("value") is not None or tank_length.get("status") != "custodian_resolution_required":
        reasons.append("tank length is not held for custodian resolution before outcome access")
    tank_volume = geometry.get("tank_internal_volume_m3")
    if not isinstance(tank_volume, dict) or tank_volume.get("value") is not None or tank_volume.get("status") != "derived_only_after_length_resolution":
        reasons.append("tank volume is not deferred until length resolution")

    integrity = protocol.get("integrity_checks")
    if not isinstance(integrity, dict):
        reasons.append("integrity checks are missing")
        integrity = {}
    for field in ("source_hashes_required", "channel_units_required", "independent_outcome_access_attestation_required"):
        if integrity.get(field) is not True:
            reasons.append(f"integrity safeguard is not enabled: {field}")

    valid = not reasons
    return {
        "schema_version": 1,
        "artifact_type": "dickens_typeiii_protocol_validation",
        "generated_at": date.today().isoformat(),
        "protocol": str(protocol_path),
        "protocol_sha256": _sha256(protocol_path),
        "protocol_valid": valid,
        "outcome_access_allowed": False,
        "numerical_values_inspected": False,
        "required_input_contract": sorted(REQUIRED_CHANNELS),
        "primary_screens": screens,
        "reasons": reasons,
        "claim_boundary": (
            "A valid result only confirms that the prospective intake contract is intact. "
            "It does not validate the Type-III model, the HRS, consequence distances, or SAGA."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    result = validate_protocol(args.protocol)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    return 0 if result["protocol_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
