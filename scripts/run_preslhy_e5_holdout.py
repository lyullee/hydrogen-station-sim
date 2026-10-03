"""Run the frozen PRESLHY E5.1 source-depletion holdout evaluation."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from h2station.preslhy_e5_validation import iter_preslhy_e5_traces
from h2station.preslhy_nonadiabatic import evaluate_nonadiabatic_trace
from h2station.preslhy_validation import eligible_pressure_window


BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20261003


def _hash(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def _aggregate(cases, protocol):
    passes = np.asarray(
        [case["joint_primary_screen_pass"] for case in cases], dtype=float
    )
    if not len(passes):
        return {
            "joint_primary_pass_fraction": None,
            "bootstrap_95_percent_ci": [None, None],
            "claim_supported": False,
        }
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.choice(
        passes, size=(BOOTSTRAP_REPLICATES, len(passes)), replace=True
    ).mean(axis=1)
    diameters = {case["nozzle_diameter_mm"] for case in cases}
    pressure_groups = {case["pressure_group"] for case in cases}
    eligibility = protocol["eligibility"]
    minima_met = (
        len(cases) >= eligibility["minimum_primary_cases"]
        and len(diameters) >= eligibility["minimum_nozzle_diameter_groups"]
        and len(pressure_groups) >= eligibility["minimum_initial_pressure_groups"]
    )
    fraction = float(passes.mean())
    threshold = protocol["aggregate_decision"][
        "minimum_joint_primary_screen_pass_fraction"
    ]
    return {
        "cases": len(cases),
        "joint_primary_passes": int(passes.sum()),
        "joint_primary_pass_fraction": fraction,
        "bootstrap_95_percent_ci": [
            float(value) for value in np.quantile(draws, [0.025, 0.975])
        ],
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "diameter_groups": sorted(diameters),
        "pressure_groups": sorted(pressure_groups),
        "minimum_requirements_met": minima_met,
        "claim_threshold": threshold,
        "claim_supported": bool(minima_met and fraction >= threshold),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path(
            "data/public_validation/raw/preslhy_e5_1/10.35097-1258/"
            "data/dataset/E5.1_Benchmark.zip"
        ),
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("research/preslhy_e5_1_holdout_protocol.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/public_validation/results/preslhy_e5_1_holdout.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    locked = protocol["locked_model"]
    if _hash(root / locked["module"]) != locked["sha256"]:
        raise RuntimeError("locked holdout model hash mismatch")
    execution = protocol.get("locked_evaluation_implementation") or {}
    for key in ("adapter", "runner"):
        item = execution.get(key) or {}
        if not item or _hash(root / item["path"]) != item["sha256"]:
            raise RuntimeError(f"locked holdout {key} hash mismatch")

    primary, transfer, failures = [], [], []
    for definition, trace in iter_preslhy_e5_traces(str(args.archive)):
        try:
            eligible_pressure_window(trace)
            record = asdict(evaluate_nonadiabatic_trace(trace))
        except Exception as exc:
            record = {
                "case_id": definition.case_id,
                "nozzle_diameter_mm": definition.nozzle_diameter_mm,
                "initial_pressure_bar_abs": trace.initial_pressure_pa / 1.0e5,
                "pressure_screen_pass": False,
                "half_time_screen_pass": False,
                "joint_primary_screen_pass": False,
                "evaluation_error": f"{type(exc).__name__}: {exc}",
            }
            failures.append(record)
        record.update(
            {
                "source_member": trace.source_member,
                "nominal_temperature_class": definition.nominal_temperature_class,
                "nominal_pressure_bar": definition.nominal_pressure_bar,
                "ignition_distance_cm": definition.ignition_distance_cm,
                "initial_temperature_k": trace.initial_temperature_k,
                "pressure_group": _pressure_group(
                    float(record["initial_pressure_bar_abs"])
                ),
                "pressure_unit_interpretation": trace.pressure_unit_interpretation,
                "ambient_pressure_substituted": trace.ambient_pressure_substituted,
            }
        )
        target = (
            primary
            if 280.0 <= trace.initial_temperature_k <= 330.0
            else transfer
        )
        target.append(record)
        print(
            f"{definition.case_id}: T0={trace.initial_temperature_k:.2f} K "
            f"primary={target is primary} pass={record['joint_primary_screen_pass']}",
            flush=True,
        )
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol_path": str(args.protocol),
        "protocol_sha256": _hash(args.protocol),
        "archive": {
            "path": str(args.archive),
            "bytes": args.archive.stat().st_size,
            "md5": _hash(args.archive, "md5"),
        },
        "primary_ambient": {
            "aggregate": _aggregate(primary, protocol),
            "cases": primary,
        },
        "cryogenic_transfer": {
            "claim_controlling": False,
            "cases": transfer,
        },
        "retained_failures": failures,
        "claim_boundary": protocol["claim_boundary"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(_json_safe(report), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
