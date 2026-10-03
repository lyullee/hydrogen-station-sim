"""Run the separately labelled post-outcome PRESLHY domain diagnostic."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile

import numpy as np

from h2station.preslhy_validation import (
    eligible_pressure_window,
    evaluate_preslhy_trace,
    read_preslhy_workbook,
)


PACKAGE = re.compile(r"PRE3P1A_KIT_D(05|1|2|4)_300K_DATA\.zip$", re.I)
BOOTSTRAP_SEED = 20261003
BOOTSTRAP_REPLICATES = 10_000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pressure_group(pressure_bar_abs: float) -> str:
    if pressure_bar_abs <= 20.0:
        return "low"
    if pressure_bar_abs <= 100.0:
        return "medium"
    return "high"


def _git_commit(root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _evaluate_or_retain_failure(trace) -> dict[str, object]:
    """Evaluate one eligible trace without dropping negative model outcomes."""
    try:
        result = evaluate_preslhy_trace(trace)
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
    record.update({
        "source_package": trace.source_package,
        "source_member": trace.source_member,
        "initial_temperature_k": trace.initial_temperature_k,
        "temperature_substituted": trace.temperature_substituted,
        "ambient_pressure_substituted": trace.ambient_pressure_substituted,
        "pressure_unit_interpretation": trace.pressure_unit_interpretation,
        "pressure_group": _pressure_group(
            float(record["initial_pressure_bar_abs"])
        ),
    })
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw",
        type=Path,
        default=Path("data/public_validation/raw/preslhy"),
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("research/preslhy_blowdown_validation_protocol.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/public_validation/results/preslhy_blowdown"),
    )
    parser.add_argument(
        "--allow-post-outcome-development",
        action="store_true",
        help="Required acknowledgement that this run is not prospective evidence.",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    if protocol["source"]["outcomes_accessed_before_freeze"] is not False:
        if not args.allow_post_outcome_development:
            raise RuntimeError(
                "Post-outcome diagnostic requires --allow-post-outcome-development"
            )
        if protocol.get("status") != "post_outcome_development_diagnostic":
            raise RuntimeError(
                "Post-outcome run requires status=post_outcome_development_diagnostic"
            )

    cases = []
    exclusions = []
    packages = []
    for package in sorted(args.raw.glob("PRE3P1A_KIT_D*_300K_DATA.zip")):
        match = PACKAGE.fullmatch(package.name)
        if not match:
            continue
        token = match.group(1)
        diameter_mm = 0.5 if token == "05" else float(token)
        packages.append({
            "name": package.name,
            "bytes": package.stat().st_size,
            "sha256": _sha256(package),
        })
        with zipfile.ZipFile(package) as bundle:
            for member in sorted(bundle.namelist()):
                if not member.lower().endswith(".xlsx"):
                    continue
                if PurePosixPath(member).name.startswith("~$"):
                    continue
                try:
                    trace = read_preslhy_workbook(
                        bundle.read(member),
                        source_package=package.name,
                        source_member=member,
                        nozzle_diameter_mm=diameter_mm,
                    )
                    eligible_pressure_window(trace)
                except Exception as exc:
                    exclusions.append({
                        "source_package": package.name,
                        "source_member": member,
                        "reason": f"{type(exc).__name__}: {exc}",
                    })
                    continue
                cases.append(_evaluate_or_retain_failure(trace))

    diameter_groups = {case["nozzle_diameter_mm"] for case in cases}
    pressure_groups = {case["pressure_group"] for case in cases}
    requirements_met = (
        len(cases) >= protocol["eligibility"]["minimum_evaluable_cases"]
        and len(diameter_groups)
        >= protocol["eligibility"]["minimum_nozzle_diameter_groups"]
        and len(pressure_groups)
        >= protocol["eligibility"]["minimum_initial_pressure_groups"]
    )
    passes = np.asarray(
        [case["joint_primary_screen_pass"] for case in cases], dtype=float
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
    threshold = protocol["aggregate_decision"][
        "minimum_joint_primary_screen_pass_fraction"
    ]
    numerical_screen_supported = bool(requirements_met and pass_fraction >= threshold)
    prospective_protocol = protocol["source"]["outcomes_accessed_before_freeze"] is False
    claim_supported = bool(numerical_screen_supported and prospective_protocol)

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner_git_commit": _git_commit(root),
        "protocol_path": str(args.protocol),
        "protocol_sha256": _sha256(args.protocol),
        "packages": packages,
        "eligibility": {
            "eligible_cases": len(cases),
            "excluded_workbooks": len(exclusions),
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
            "numerical_screen_supported": numerical_screen_supported,
            "prospective_protocol": prospective_protocol,
            "ambient_direct_aperture_blowdown_claim_supported": claim_supported,
        },
        "cases": cases,
        "exclusions": exclusions,
        "claim_boundary": protocol["claim_boundary"],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / "validation.json"
    destination.write_text(
        json.dumps(_json_safe(report), indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(destination)
    print(
        f"eligible={len(cases)}, excluded={len(exclusions)}, "
        f"pass_fraction={pass_fraction:.3f}, claim_supported={claim_supported}",
        file=sys.stderr,
    )
    return 0 if requirements_met else 2


if __name__ == "__main__":
    raise SystemExit(main())
