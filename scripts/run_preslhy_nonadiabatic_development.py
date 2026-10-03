"""Evaluate the revised model on consumed PRESLHY development cases."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import zipfile

import numpy as np

from h2station.preslhy_nonadiabatic import evaluate_nonadiabatic_trace
from h2station.preslhy_validation import (
    eligible_pressure_window,
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


def _json_safe(value):
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _summary(cases: list[dict[str, object]]) -> dict[str, object]:
    passes = np.asarray(
        [case["joint_primary_screen_pass"] for case in cases], dtype=float
    )
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = rng.choice(
        passes, size=(BOOTSTRAP_REPLICATES, len(passes)), replace=True
    ).mean(axis=1)
    by_diameter = {}
    by_pressure = {}
    for key, destination in (
        ("nozzle_diameter_mm", by_diameter),
        ("pressure_group", by_pressure),
    ):
        values = sorted({case[key] for case in cases}, key=str)
        for value in values:
            group = [case for case in cases if case[key] == value]
            destination[str(value)] = {
                "cases": len(group),
                "joint_passes": sum(
                    bool(case["joint_primary_screen_pass"]) for case in group
                ),
            }
    return {
        "cases": len(cases),
        "joint_primary_passes": int(passes.sum()),
        "joint_primary_pass_fraction": float(passes.mean()),
        "bootstrap_95_percent_ci": [
            float(value) for value in np.quantile(draws, [0.025, 0.975])
        ],
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "by_nozzle_diameter_mm": by_diameter,
        "by_pressure_group": by_pressure,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw",
        type=Path,
        default=Path("data/public_validation/raw/preslhy"),
    )
    parser.add_argument(
        "--plan",
        type=Path,
        default=Path("research/preslhy_nonadiabatic_development_plan.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/public_validation/results/preslhy_nonadiabatic_development.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    cases: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    packages = []
    for package in sorted(args.raw.glob("PRE3P1A_KIT_D*_300K_DATA.zip")):
        match = PACKAGE.fullmatch(package.name)
        if not match:
            continue
        token = match.group(1)
        diameter_mm = 0.5 if token == "05" else float(token)
        packages.append(
            {"name": package.name, "bytes": package.stat().st_size, "sha256": _sha256(package)}
        )
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
                    record = asdict(evaluate_nonadiabatic_trace(trace))
                except Exception as exc:
                    errors.append(
                        {
                            "source_package": package.name,
                            "source_member": member,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
                    continue
                record.update(
                    {
                        "source_package": package.name,
                        "source_member": member,
                        "initial_temperature_k": trace.initial_temperature_k,
                        "pressure_group": _pressure_group(
                            float(record["initial_pressure_bar_abs"])
                        ),
                    }
                )
                cases.append(record)
                print(
                    f"{record['case_id']}: nrmse={record['pressure_nrmse_percent_initial_absolute_pressure']:.2f}% "
                    f"half={record['time_to_50_percent_gauge_relative_error_percent']:.2f}% "
                    f"pass={record['joint_primary_screen_pass']}",
                    flush=True,
                )
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_role": "consumed_development_data_not_external_validation",
        "claim_prohibited": True,
        "plan_path": str(args.plan),
        "plan_sha256": _sha256(args.plan),
        "implementation": {
            "module": "src/h2station/preslhy_nonadiabatic.py",
            "sha256": _sha256(root / "src/h2station/preslhy_nonadiabatic.py"),
            "runner": "scripts/run_preslhy_nonadiabatic_development.py",
            "runner_sha256": _sha256(Path(__file__)),
        },
        "packages": packages,
        "aggregate": _summary(cases) if cases else None,
        "cases": cases,
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(_json_safe(report), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0 if cases and not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
