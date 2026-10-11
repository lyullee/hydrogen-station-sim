"""Run the frozen PRESLHY E3.1 D05/D2 80 K holdout.

The protocol must be committed before package workbooks are read.  The runner
retains aggregate case metrics and hashes only; workbook rows are never saved.
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
import zipfile

import numpy as np

from h2station.preslhy_80k_holdout import read_preslhy_80k_workbook
from h2station.preslhy_validation import eligible_pressure_window, evaluate_preslhy_trace


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "research/preslhy_e31_80k_d05_d2_holdout_protocol_2026_10_12.json"
DEFAULT_OUTPUT = ROOT / "data/public_validation/results/preslhy_e31_80k_d05_d2_holdout"


def _hash(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
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
    if pressure_bar_abs <= 20.0:
        return "low"
    if pressure_bar_abs <= 100.0:
        return "medium"
    return "high"


def _evaluate(trace) -> dict[str, object]:
    try:
        eligible_pressure_window(trace)
        record = asdict(evaluate_preslhy_trace(trace))
        error = None
    except Exception as exc:
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
        }
        error = f"{type(exc).__name__}: {exc}"
    record.update({
        "source_package": trace.source_package,
        "source_member": trace.source_member,
        "initial_temperature_k": trace.initial_temperature_k,
        "temperature_substituted": trace.temperature_substituted,
        "ambient_pressure_substituted": trace.ambient_pressure_substituted,
        "pressure_unit_interpretation": trace.pressure_unit_interpretation,
        "pressure_group": _pressure_group(float(record["initial_pressure_bar_abs"])),
        "evaluation_error": error,
        "eligible_for_aggregate": error is None,
    })
    return record


def run(packages: list[Path], protocol_path: Path) -> dict[str, object]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("status") != "frozen_before_numerical_outcome_access":
        raise RuntimeError("80 K D05/D2 protocol is not prospectively frozen")
    if (protocol.get("independence") or {}).get("outcomes_accessed_before_freeze") is not False:
        raise RuntimeError("protocol does not certify pre-outcome freeze")
    package_cfg = {item["package_name"]: item for item in protocol["source"]["packages"]}
    if {p.name for p in packages} != set(package_cfg):
        raise RuntimeError("exactly the two protocol packages must be supplied")
    cases = []
    read_errors = []
    for package in packages:
        cfg = package_cfg[package.name]
        if _hash(package, "md5") != cfg["manifest_md5"]:
            raise RuntimeError(f"manifest MD5 mismatch for {package.name}")
        with zipfile.ZipFile(package) as bundle:
            for member in sorted(bundle.namelist()):
                if not member.lower().endswith(".xlsx") or PurePosixPath(member).name.startswith("~$"):
                    continue
                try:
                    trace = read_preslhy_80k_workbook(
                        bundle.read(member),
                        source_package=package.name,
                        source_member=member,
                        nozzle_diameter_mm=float(cfg["nozzle_diameter_mm"]),
                    )
                    cases.append(_evaluate(trace))
                except Exception as exc:
                    read_errors.append({
                        "source_package": package.name,
                        "source_member": member,
                        "reason": f"{type(exc).__name__}: {exc}",
                    })
    ecfg = protocol["eligibility"]
    eligible = [
        c for c in cases
        if c["eligible_for_aggregate"]
        and not c["temperature_substituted"]
        and not c["ambient_pressure_substituted"]
        and ecfg["minimum_initial_temperature_k"] <= float(c["initial_temperature_k"]) <= ecfg["maximum_initial_temperature_k"]
    ]
    diameters = sorted({float(c["nozzle_diameter_mm"]) for c in eligible})
    pressure_groups = sorted({c["pressure_group"] for c in eligible})
    requirements_met = bool(
        len(eligible) >= ecfg["minimum_evaluable_cases"]
        and len(diameters) >= ecfg["minimum_nozzle_diameter_groups"]
        and len(pressure_groups) >= ecfg["minimum_initial_pressure_groups"]
    )
    passes = np.asarray([bool(c["joint_primary_screen_pass"]) for c in eligible], dtype=float)
    if passes.size:
        fraction = float(passes.mean())
        rng = np.random.default_rng(int(protocol["aggregate_decision"]["bootstrap_seed"]))
        draws = rng.choice(passes, size=(int(protocol["aggregate_decision"]["bootstrap_replicates"]), len(passes)), replace=True)
        ci = [float(v) for v in np.quantile(draws.mean(axis=1), [0.025, 0.975])]
    else:
        fraction, ci = math.nan, [math.nan, math.nan]
    threshold = float(protocol["aggregate_decision"]["minimum_joint_primary_screen_pass_fraction"])
    return {
        "schema_version": 1,
        "status": "completed_frozen_holdout",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runner_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "protocol_path": str(protocol_path.relative_to(ROOT)).replace("\\", "/"),
        "protocol_sha256": _hash(protocol_path),
        "packages": [{"name": p.name, "bytes": p.stat().st_size, "sha256": _hash(p), "md5": _hash(p, "md5")} for p in packages],
        "eligibility": {
            "evaluable_cases": len(cases),
            "aggregate_eligible_cases": len(eligible),
            "read_errors": len(read_errors),
            "diameter_groups": diameters,
            "pressure_groups": pressure_groups,
            "minimum_requirements_met": requirements_met,
        },
        "aggregate": {
            "joint_primary_passes": int(passes.sum()) if passes.size else 0,
            "joint_primary_pass_fraction": fraction,
            "bootstrap_95_percent_ci": ci,
            "bootstrap_replicates": int(protocol["aggregate_decision"]["bootstrap_replicates"]),
            "bootstrap_seed": int(protocol["aggregate_decision"]["bootstrap_seed"]),
            "claim_threshold": threshold,
            "claim_supported": bool(requirements_met and fraction >= threshold),
        },
        "cases": cases,
        "read_errors_detail": read_errors,
        "raw_rows_persisted": False,
        "claim_boundary": protocol["claim_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", action="append", required=True, type=Path)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    protocol = args.protocol if args.protocol.is_absolute() else ROOT / args.protocol
    packages = [p if p.is_absolute() else ROOT / p for p in args.package]
    report = run(packages, protocol)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "validation.json"
    destination.write_text(json.dumps(_json_safe(report), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(destination), "evaluable_cases": report["eligibility"]["evaluable_cases"], "aggregate_eligible_cases": report["eligibility"]["aggregate_eligible_cases"], "pass_fraction": report["aggregate"]["joint_primary_pass_fraction"], "claim_supported": report["aggregate"]["claim_supported"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
