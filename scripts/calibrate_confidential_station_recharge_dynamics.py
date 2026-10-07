"""Derive an opt-in compressor restart-dwell profile from restricted station logs.

The command is intended for the data custodian's controlled environment.  It
reads raw rows only in memory and writes a de-identified aggregate report.  Do
not commit the mapping, raw files, absolute timestamps, or generated output
until the owner approves the aggregate values for publication.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.station_dynamics_calibration import (
    summarize_recharge_dynamics,
    validate_recharge_dynamics_temporal_holdout,
)

try:
    from calibrate_confidential_station_data import _mapping
except ModuleNotFoundError:
    from scripts.calibrate_confidential_station_data import _mapping


def _bank_role(value: str) -> tuple[str, str]:
    try:
        role, bank = value.split("=", 1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use PRESSURE_ROLE=low|medium|high") from exc
    role, bank = role.strip(), bank.strip().lower()
    if not role or bank not in {"low", "medium", "high"}:
        raise argparse.ArgumentTypeError("use PRESSURE_ROLE=low|medium|high")
    return role, bank


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a privacy-bounded station recharge-dynamics aggregate"
    )
    parser.add_argument("--input", type=Path, required=True, help="restricted raw trace or bundle")
    parser.add_argument("--mapping", type=Path, required=True, help="restricted custodian mapping JSON")
    parser.add_argument("--output", type=Path, required=True, help="approved aggregate JSON destination")
    parser.add_argument("--compressor-state-role", required=True)
    parser.add_argument(
        "--active-state", action="append", required=True,
        help="attested raw state value meaning that the compressor is loaded; repeat as needed",
    )
    parser.add_argument(
        "--bank-role", type=_bank_role, action="append", required=True,
        help="attested generic mapping, for example medium_storage_pressure=medium",
    )
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--max-rows-per-file", type=int, default=250_000)
    parser.add_argument(
        "--temporal-holdout", action="store_true",
        help=(
            "fit the earlier portion of each trace and require the later "
            "portion to support the dwell before runtime opt-in is eligible"
        ),
    )
    parser.add_argument(
        "--calibration-fraction", type=float, default=0.70,
        help="chronological fraction retained for fitting when --temporal-holdout is used",
    )
    parser.add_argument(
        "--pressure-semantics-attested", action="store_true",
        help="confirm that mapped pressure roles and units were approved by the custodian",
    )
    parser.add_argument(
        "--state-semantics-attested", action="store_true",
        help="confirm that --active-state values were approved by the custodian",
    )
    args = parser.parse_args()
    if args.stride < 1 or args.max_rows_per_file < 1:
        parser.error("--stride and --max-rows-per-file must be at least one")
    if not args.pressure_semantics_attested or not args.state_semantics_attested:
        parser.error("both pressure and state semantics attestations are required")
    bank_roles = dict(args.bank_role)
    if len(bank_roles) != len(args.bank_role):
        parser.error("a pressure role may be mapped only once")
    common = {
        "compressor_state_role": args.compressor_state_role,
        "active_state_values": args.active_state,
        "bank_by_pressure_role": bank_roles,
        "pressure_semantics_attested": args.pressure_semantics_attested,
        "state_semantics_attested": args.state_semantics_attested,
        "stride": args.stride,
        "max_rows_per_file": args.max_rows_per_file,
    }
    temporal_holdout = None
    if args.temporal_holdout:
        temporal_holdout = validate_recharge_dynamics_temporal_holdout(
            args.input,
            _mapping(args.mapping),
            calibration_fraction=args.calibration_fraction,
            **common,
        )
        summary = temporal_holdout.calibration
    else:
        summary = summarize_recharge_dynamics(
            args.input,
            _mapping(args.mapping),
            **common,
        )
    runtime_parameter_application = bool(
        temporal_holdout is not None and temporal_holdout.dwell_consistent
    )
    runtime_application_block_reason = (
        None
        if runtime_parameter_application
        else (
            "chronological_holdout_does_not_support_fitted_restart_dwell"
            if temporal_holdout is not None
            else "chronological_holdout_not_run"
        )
    )
    report = {
        "schema_version": 1,
        "artifact_type": "confidential_station_recharge_dynamics_calibration",
        "source_identifiers_published": False,
        "raw_rows_persisted": False,
        "absolute_timestamps_published": False,
        "source_paths_published": False,
        "tag_names_published": False,
        "manufacturer_or_model_published": False,
        "sampling": {
            "stride": args.stride,
            "max_rows_per_file": args.max_rows_per_file,
        },
        "channel_attestation": {
            "pressure_role_and_unit_semantics_attested": True,
            "compressor_state_semantics_attested": True,
        },
        "calibration": summary.to_public_dict(),
        "temporal_holdout": (
            temporal_holdout.to_public_dict() if temporal_holdout is not None else None
        ),
        "eligibility": {
            "station_recharge_dynamics_calibration_supported": (
                summary.recommended_minimum_recharge_off_time_s is not None
                and not summary.quality_warnings
            ),
            "runtime_parameter_application": runtime_parameter_application,
            "runtime_application_block_reason": runtime_application_block_reason,
            "full_station_vehicle_validation": False,
            "full_loop_holdout_eligible": False,
            "default_model_parameters_changed": False,
        },
        "claim_boundary": (
            "Owner-attested station-side recharge-dynamics aggregate only. "
            + (
                "The chronological holdout supports an opt-in compressor restart dwell; "
                if runtime_parameter_application
                else "The chronological holdout does not support runtime application of the fitted compressor restart dwell; "
            )
            + "it does not fit compressor capacity, validate vehicle filling, or "
            "establish a safety limit or field-safety distance."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
