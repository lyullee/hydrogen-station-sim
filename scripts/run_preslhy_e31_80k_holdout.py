"""Run the frozen public PRESLHY E3.1 80 K release holdout.

The protocol is read before any numerical trace is evaluated.  The runner
stores only aggregate case metrics and source hashes; raw workbook rows are
never copied into the repository.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

import numpy as np

from h2station.preslhy_80k_holdout import read_preslhy_80k_workbook
from h2station.preslhy_validation import (
    eligible_pressure_window,
    evaluate_preslhy_trace,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "research/preslhy_e31_80k_holdout_protocol_2026_10_09.json"
DEFAULT_OUTPUT = ROOT / "data/public_validation/results/preslhy_e31_80k_holdout"
PACKAGE_NAME = "PRE3P1A_KIT_D4_80K_DATA.zip"
BOOTSTRAP_REPLICATES = 10_000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
    ).strip()


def _pressure_group(pressure_bar_abs: float) -> str:
    if pressure_bar_abs <= 20.0:
        return "low"
    if pressure_bar_abs <= 100.0:
        return "medium"
    return "high"


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _evaluate(trace, *, protocol: dict) -> dict[str, object]:
    """Evaluate one trace and retain a structured failure when it errors."""

    try:
        eligible_pressure_window(trace)
        result = evaluate_preslhy_trace(trace)
        record = asdict(result)
        evaluation_error = None
    except Exception as exc:  # retain failures instead of silently excluding them
        record = {
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
        evaluation_error = record["evaluation_error"]
    record.update({
        "source_package": trace.source_package,
        "source_member": trace.source_member,
        "initial_temperature_k": trace.initial_temperature_k,
        "temperature_substituted": trace.temperature_substituted,
        "ambient_pressure_substituted": trace.ambient_pressure_substituted,
        "pressure_unit_interpretation": trace.pressure_unit_interpretation,
        "pressure_group": _pressure_group(float(record["initial_pressure_bar_abs"])),
        "eligible_for_aggregate": evaluation_error is None,
    })
    return record


def run(package: Path, protocol_path: Path = DEFAULT_PROTOCOL) -> dict[str, object]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("status") != "frozen_before_numerical_outcome_access":
        raise RuntimeError("80 K protocol is not prospectively frozen")
    if (protocol.get("source") or {}).get("outcomes_accessed_before_freeze") is True:
        raise RuntimeError("80 K outcomes were marked as accessed before freeze")
    if package.name != PACKAGE_NAME:
        raise RuntimeError(f"unexpected package name: {package.name}")
    expected_hash = str((protocol.get("source") or {}).get("package_sha256") or "")
    actual_hash = _sha256(package)
    if actual_hash != expected_hash:
        raise RuntimeError("80 K package hash does not match the frozen protocol")

    cases: list[dict[str, object]] = []
    read_errors: list[dict[str, str]] = []
    with zipfile.ZipFile(package) as bundle:
        for member in sorted(bundle.namelist()):
            if not member.lower().endswith(".xlsx"):
                continue
            if PurePosixPath(member).name.startswith("~$"):
                continue
            try:
                trace = read_preslhy_80k_workbook(
                    bundle.read(member),
                    source_package=package.name,
                    source_member=member,
                    nozzle_diameter_mm=4.0,
                )
            except Exception as exc:
                read_errors.append({
                    "source_member": member,
                    "reason": f"{type(exc).__name__}: {exc}",
                })
                continue
            cases.append(_evaluate(trace, protocol=protocol))

    eligible = [
        case for case in cases
        if case.get("eligible_for_aggregate") is True
        and case.get("temperature_substituted") is False
        and case.get("ambient_pressure_substituted") is False
        and float(case.get("initial_temperature_k") or 0.0)
        >= float(protocol["eligibility"]["minimum_initial_temperature_k"])
        and float(case.get("initial_temperature_k") or 0.0)
        <= float(protocol["eligibility"]["maximum_initial_temperature_k"])
    ]
    diameter_groups = {float(case["nozzle_diameter_mm"]) for case in eligible}
    pressure_groups = {str(case["pressure_group"]) for case in eligible}
    eligibility_cfg = protocol["eligibility"]
    requirements_met = bool(
        len(eligible) >= int(eligibility_cfg["minimum_evaluable_cases"])
        and len(diameter_groups) >= int(eligibility_cfg["minimum_nozzle_diameter_groups"])
        and len(pressure_groups) >= int(eligibility_cfg["minimum_initial_pressure_groups"])
    )
    passes = np.asarray(
        [bool(case["joint_primary_screen_pass"]) for case in eligible], dtype=float,
    )
    if passes.size:
        pass_fraction = float(np.mean(passes))
        seed = int(protocol["aggregate_decision"]["bootstrap_seed"])
        rng = np.random.default_rng(seed)
        draws = rng.choice(passes, size=(BOOTSTRAP_REPLICATES, len(passes)), replace=True)
        bootstrap_ci = [float(value) for value in np.quantile(draws.mean(axis=1), [0.025, 0.975])]
    else:
        pass_fraction = math.nan
        bootstrap_ci = [math.nan, math.nan]
    threshold = float(protocol["aggregate_decision"]["minimum_joint_primary_screen_pass_fraction"])
    claim_supported = bool(requirements_met and pass_fraction >= threshold)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner_git_commit": _git_commit(),
        "protocol_path": str(protocol_path.relative_to(ROOT)).replace("\\", "/"),
        "protocol_sha256": _sha256(protocol_path),
        "package": {
            "name": package.name,
            "bytes": package.stat().st_size,
            "sha256": actual_hash,
        },
        "eligibility": {
            "evaluable_cases": len(cases),
            "aggregate_eligible_cases": len(eligible),
            "read_errors": len(read_errors),
            "diameter_groups": sorted(diameter_groups),
            "pressure_groups": sorted(pressure_groups),
            "minimum_requirements_met": requirements_met,
        },
        "aggregate": {
            "joint_primary_screen_pass_fraction": pass_fraction,
            "bootstrap_95_percent_ci": bootstrap_ci,
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "bootstrap_seed": int(protocol["aggregate_decision"]["bootstrap_seed"]),
            "claim_threshold": threshold,
            "ambient_80k_direct_aperture_blowdown_claim_supported": claim_supported,
        },
        "cases": cases,
        "read_errors": read_errors,
        "raw_rows_persisted": False,
        "claim_boundary": protocol["claim_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    protocol_path = args.protocol if args.protocol.is_absolute() else ROOT / args.protocol
    package = args.package if args.package.is_absolute() else ROOT / args.package
    report = run(package, protocol_path)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "validation.json"
    destination.write_text(
        json.dumps(_json_safe(report), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(destination),
        "evaluable_cases": report["eligibility"]["evaluable_cases"],
        "aggregate_eligible_cases": report["eligibility"]["aggregate_eligible_cases"],
        "pass_fraction": report["aggregate"]["joint_primary_screen_pass_fraction"],
        "claim_supported": report["aggregate"]["ambient_80k_direct_aperture_blowdown_claim_supported"],
    }, ensure_ascii=False))
    return 0 if report["eligibility"]["minimum_requirements_met"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
