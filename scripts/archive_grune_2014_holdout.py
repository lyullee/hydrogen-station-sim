"""Archive the ineligible Grune et al. (2014) pressure-decay holdout."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from h2station.grune_2014_validation import (
    evaluate_grune_2014_holdout,
    load_grune_2014_pressure_csv,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite_or_none(value: object) -> object:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data", type=Path,
        default=Path("data/public_validation/derived/grune_2014_figure2.csv"),
    )
    parser.add_argument(
        "--protocol", type=Path,
        default=Path("research/grune_2014_holdout_protocol.json"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("research/grune_2014_holdout_result.json"),
    )
    args = parser.parse_args()
    result = evaluate_grune_2014_holdout(load_grune_2014_pressure_csv(args.data))
    observed = {key: _finite_or_none(value) for key, value in asdict(result).items()}
    half_pressure_observed = math.isfinite(result.experimental_half_pressure_time_s)
    eligible = result.points >= 15 and half_pressure_observed
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": _sha256(args.protocol),
        "data_sha256": _sha256(args.data),
        "eligibility": {
            "minimum_unique_points_met": result.points >= 15,
            "measured_half_pressure_time_observed": half_pressure_observed,
            "minimum_requirements_met": eligible,
            "reason": (
                None if eligible else
                "The accessible publisher raster separates the valve trace only in the 0-0.01 s startup panel; the overlapping inset does not support a trace-specific half-pressure time."
            ),
        },
        "result": observed,
        "claim_supported": eligible and result.joint_primary_screen_pass,
        "claim_boundary": (
            "One 20 MPa, 0.37 L, 4 mm pressure-decay trace; no flame, ignition, "
            "dispersion, radiation, station control or safety-distance claim."
        ),
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
