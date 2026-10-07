"""Build an attestation-gated station thermal operating diagnostic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.restricted_attestation import load_restricted_channel_attestation
from h2station.station_thermal_diagnostic import (
    validate_station_thermal_temporal_stability,
)

from calibrate_confidential_station_data import _mapping


def _component_role(value: str) -> tuple[str, str]:
    try:
        role, component = value.split("=", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use ROLE=compressor|cooler_inlet|cooler_outlet") from exc
    role, component = role.strip(), component.strip()
    if not role or component not in {"compressor", "cooler_inlet", "cooler_outlet"}:
        raise argparse.ArgumentTypeError("use ROLE=compressor|cooler_inlet|cooler_outlet")
    return role, component


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze owner-attested compressor/cooler thermal dynamics"
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--attestation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cooling-state-role", required=True)
    parser.add_argument("--active-state", action="append", required=True)
    parser.add_argument("--component-role", type=_component_role, action="append", required=True)
    parser.add_argument("--calibration-fraction", type=float, default=0.70)
    parser.add_argument("--minimum-holdout-rows", type=int, default=100)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--max-rows-per-file", type=int, default=250_000)
    args = parser.parse_args()

    mapping = _mapping(args.mapping)
    try:
        attestation = load_restricted_channel_attestation(args.attestation, mapping)
    except ValueError as exc:
        parser.error(str(exc))
    components = dict(args.component_role)
    if len(components) != len(args.component_role):
        parser.error("a temperature role may be mapped only once")
    result = validate_station_thermal_temporal_stability(
        args.input,
        mapping,
        cooling_state_role=args.cooling_state_role,
        cooling_active_state_values=args.active_state,
        component_by_temperature_role=components,
        temperature_semantics_attested=(
            attestation.temperature_role_and_unit_semantics_attested
        ),
        state_semantics_attested=attestation.state_semantics_attested,
        calibration_fraction=args.calibration_fraction,
        minimum_holdout_rows=args.minimum_holdout_rows,
        stride=args.stride,
        max_rows_per_file=args.max_rows_per_file,
    )
    public_attestation = attestation.to_public_dict()
    report = {
        "schema_version": 1,
        "artifact_type": "confidential_station_thermal_dynamics_diagnostic",
        "status": "completed_attested_within_trace_diagnostic",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "absolute_timestamps_published": False,
        "source_paths_published": False,
        "tag_names_published": False,
        "manufacturer_or_model_published": False,
        "channel_attestation": public_attestation,
        "temporal_stability": result.to_public_dict(),
        "eligibility": {
            "station_component_thermal_envelope_supported": result.stability_supported,
            "runtime_parameter_application": False,
            "vehicle_fill_thermal_validation": False,
            "full_station_vehicle_validation": False,
            "full_loop_holdout_eligible": False,
            "default_model_parameters_changed": False,
        },
        "claim_boundary": (
            "Owner-attested, de-identified compressor/cooler within-record stability "
            "diagnostic only. No raw rows or identifiers are published and no runtime "
            "parameter, vehicle-fill validation or safety claim is authorized."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
