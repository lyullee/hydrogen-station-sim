"""Archive the Grune et al. (2014) result with an explicit eligibility boundary.

The numerical evaluator and its frozen runner are intentionally left unchanged.
This wrapper only adds the publication-safe eligibility metadata and converts
non-finite endpoint values to JSON ``null`` when the digitized curve does not
contain the required crossing.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from h2station.grune_2014_validation import (
    evaluate_grune_2014_holdout,
    load_grune_2014_pressure_csv,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def build_result(data_path: Path, protocol_path: Path, access_path: Path) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    access = json.loads(access_path.read_text(encoding="utf-8"))
    result = evaluate_grune_2014_holdout(load_grune_2014_pressure_csv(data_path))
    result_dict = _json_safe(asdict(result))
    minimum_points = int((protocol.get("eligibility") or {}).get("minimum_unique_points") or 0)
    minimum_points_met = result.points >= minimum_points
    measured_half_observed = math.isfinite(result.experimental_half_pressure_time_s)
    minimum_requirements_met = minimum_points_met and measured_half_observed
    return {
        "schema_version": 1,
        "artifact_type": "grune_2014_pressure_decay_holdout_result",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": _sha256(protocol_path),
        "data_sha256": _sha256(data_path),
        "result": result_dict,
        "eligibility": {
            "minimum_unique_points_met": minimum_points_met,
            "measured_half_pressure_time_observed": measured_half_observed,
            "minimum_requirements_met": minimum_requirements_met,
            "full_raw_holdout_eligible": bool(
                ((access.get("eligibility") or {}).get("full_raw_holdout_eligible"))
            ),
            "reason": (
                "The digitized Figure 2 measured curve never reaches half of its initial pressure; "
                "the timing endpoint is therefore unavailable and the holdout claim remains closed."
                if not measured_half_observed
                else "All minimum trace requirements are present; apply the frozen endpoint screens."
            ),
        },
        "claim_supported": bool(result.joint_primary_screen_pass and minimum_requirements_met),
        "claim_boundary": (
            "One 20 MPa, 0.37 L, 4 mm pressure-decay trace; no flame, ignition, dispersion, "
            "radiation, station control or safety-distance claim. The digitized measured curve "
            "does not provide the required half-pressure crossing, so no validation claim is made."
        ),
    }


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
        "--access", type=Path,
        default=Path("research/grune_2014_publisher_access_recheck_2026_10_06.json"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("research/grune_2014_holdout_result.json"),
    )
    args = parser.parse_args()
    payload = build_result(args.data, args.protocol, args.access)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
