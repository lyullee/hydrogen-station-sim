"""Run the prospectively frozen PRESLHY Cryostat Part-B ambient holdout."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

from h2station.preslhy_partb_validation import (
    CRYOSTAT_VOLUME_M3,
    evaluate_preslhy_partb_trace,
    iter_preslhy_partb_traces,
)
from h2station.preslhy_validation import eligible_pressure_window


BOOTSTRAP_SEED = 20261004
BOOTSTRAP_REPLICATES = 10_000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _pressure_group(pressure_bar_abs: float) -> str:
    return "low" if pressure_bar_abs <= 5.0 else "high"


def _git_commit(root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()


def _evaluate(trace) -> dict[str, object]:
    try:
        eligible_pressure_window(trace)
        result = evaluate_preslhy_partb_trace(trace)
    except Exception as exc:
        record: dict[str, object] = {
            "case_id": trace.case_id,
            "nozzle_diameter_mm": trace.nozzle_diameter_mm,
            "initial_pressure_bar_abs": trace.initial_pressure_pa / 1.0e5,
            "samples": None,
            "pressure_rmse_bar": None,
            "pressure_mae_bar": None,
            "pressure_nrmse_percent_initial_absolute_pressure": None,
            "experimental_time_to_50_percent_gauge_s": None,
            "predicted_time_to_50_percent_gauge_s": None,
            "time_to_50_percent_gauge_relative_error_percent": None,
            "pressure_screen_pass": False,
            "half_time_screen_pass": False,
            "joint_primary_screen_pass": False,
            "peak_mass_flow_kg_s": None,
            "cumulative_released_mass_kg": None,
            "evaluation_error": f"{type(exc).__name__}: {exc}",
        }
    else:
        record = asdict(result)
    record.update(
        {
            "source_package": trace.source_package,
            "source_member": trace.source_member,
            "initial_temperature_k": trace.initial_temperature_k,
            "ambient_pressure_pa": trace.ambient_pressure_pa,
            "source_volume_m3": CRYOSTAT_VOLUME_M3,
            "temperature_substituted": trace.temperature_substituted,
            "ambient_pressure_substituted": trace.ambient_pressure_substituted,
            "pressure_unit_interpretation": trace.pressure_unit_interpretation,
            "pressure_group": _pressure_group(float(record["initial_pressure_bar_abs"])),
        }
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw",
        type=Path,
        default=Path("data/public_validation/raw/preslhy_partb_xlsx"),
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("research/preslhy_partb_holdout_protocol.json"),
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path("data/public_validation/raw/preslhy_partb.tar"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/public_validation/results/preslhy_partb"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol["outcomes_accessed_before_freeze"] is not False:
        raise RuntimeError("PRESLHY Part-B protocol is not prospectively frozen")

    cases = [_evaluate(trace) for trace in iter_preslhy_partb_traces(args.raw)]
    eligible = [case for case in cases if case["samples"] is not None]
    diameter_groups = {case["nozzle_diameter_mm"] for case in eligible}
    pressure_groups = {case["pressure_group"] for case in eligible}
    minimum = protocol["eligibility"]
    requirements_met = (
        len(eligible) >= minimum["minimum_evaluable_cases"]
        and len(diameter_groups) >= minimum["minimum_nozzle_groups"]
        and len(pressure_groups) >= minimum["minimum_pressure_groups"]
    )
    passes = np.asarray(
        [case["joint_primary_screen_pass"] for case in eligible], dtype=float
    )
    if passes.size:
        pass_fraction = float(np.mean(passes))
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        draws = rng.choice(
            passes, size=(BOOTSTRAP_REPLICATES, len(passes)), replace=True
        ).mean(axis=1)
        bootstrap_ci = [float(value) for value in np.quantile(draws, [0.025, 0.975])]
    else:
        pass_fraction = math.nan
        bootstrap_ci = [math.nan, math.nan]
    threshold = protocol["engineering_screens"]["minimum_joint_screen_pass_fraction"]
    claim_supported = bool(requirements_met and pass_fraction >= threshold)

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner_git_commit": _git_commit(root),
        "protocol_path": str(args.protocol),
        "protocol_sha256": _sha256(args.protocol),
        "archive_sha256": _sha256(args.archive) if args.archive.exists() else None,
        "archive_access": "public_archive_extracted_after_protocol_freeze",
        "eligibility": {
            "eligible_cases": len(eligible),
            "excluded_cases": len(cases) - len(eligible),
            "diameter_groups": sorted(diameter_groups),
            "pressure_groups": sorted(pressure_groups),
            "minimum_requirements_met": requirements_met,
        },
        "aggregate": {
            "joint_primary_pass_fraction": pass_fraction,
            "bootstrap_95_percent_ci": bootstrap_ci,
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "claim_threshold": threshold,
            "ambient_cryostat_part_b_claim_supported": claim_supported,
        },
        "cases": cases,
        "claim_boundary": protocol["claim_boundary"],
        "negative_result_policy": "A failed screen is retained; no parameter or case-specific fitting was applied.",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / "validation.json"
    destination.write_text(
        json.dumps(_json_safe(report), indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(destination)
    print(
        f"eligible={len(eligible)}, pass_fraction={pass_fraction:.3f}, "
        f"claim_supported={claim_supported}",
        file=sys.stderr,
    )
    return 0 if requirements_met else 2


if __name__ == "__main__":
    raise SystemExit(main())
