"""Run a disclosed post-hoc release-model sensitivity diagnostic.

This script deliberately does *not* modify or re-run any frozen validation
result.  It evaluates a small, pre-declared discharge-coefficient grid against
the already archived digitised traces so that model-form limitations can be
diagnosed.  The output is development evidence only: a grid point that happens
to pass a screen is not an independent validation result and must not be used
to change the IJHE readiness audit.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Callable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from h2station.grune_2014_validation import (  # noqa: E402
    Grune2014Inputs,
    load_grune_2014_pressure_csv,
    predict_pressure_bar_abs,
)
from h2station.schefer_2006_validation import (  # noqa: E402
    ScheferBlowdownInputs,
    load_schefer_flow_csv,
    simulate_adiabatic_blowdown_flow,
)
from h2station.schefer_2007_validation import (  # noqa: E402
    Schefer2007Inputs,
    load_schefer_2007_pressure_csv,
    simulate_adiabatic_blowdown_pressure,
)


GRID = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _crossing_time(
    time_s: np.ndarray,
    values: np.ndarray,
    target: float,
    *,
    search_from_peak: bool,
) -> float:
    start = int(np.argmax(values)) if search_from_peak else 0
    tail = values[start:]
    reached = np.flatnonzero(tail <= target)
    if not reached.size:
        return float("nan")
    index = start + int(reached[0])
    if index == start:
        return float(time_s[index])
    v0, v1 = float(values[index - 1]), float(values[index])
    t0, t1 = float(time_s[index - 1]), float(time_s[index])
    if v1 == v0:
        return t1
    return t0 + (target - v0) * (t1 - t0) / (v1 - v0)


def _metrics(
    time_s: np.ndarray,
    measured: np.ndarray,
    predicted: np.ndarray,
    *,
    kind: str,
    limits: tuple[float, float, float],
) -> dict[str, object]:
    peak = float(np.max(measured))
    nrmse = float(np.sqrt(np.mean((predicted - measured) ** 2)) / peak * 100.0)
    relative_mask = measured >= 0.1 * peak
    median_ape = float(
        np.median(
            np.abs(predicted[relative_mask] - measured[relative_mask])
            / measured[relative_mask]
        )
        * 100.0
    )
    experimental_half = _crossing_time(
        time_s,
        measured,
        0.5 * peak,
        search_from_peak=kind == "flow",
    )
    predicted_half = _crossing_time(
        time_s,
        predicted,
        0.5 * peak,
        search_from_peak=kind == "flow",
    )
    if (
        np.isfinite(experimental_half)
        and experimental_half > 0.0
        and np.isfinite(predicted_half)
    ):
        half_error = float(abs(predicted_half - experimental_half) / experimental_half * 100.0)
    else:
        half_error = float("nan")
    nrmse_limit, ape_limit, half_limit = limits
    screen_pass = {
        "nrmse": nrmse <= nrmse_limit,
        "median_ape": median_ape <= ape_limit,
        "half_time": bool(np.isfinite(half_error) and half_error <= half_limit),
    }
    normalized_score = (
        nrmse / nrmse_limit
        + median_ape / ape_limit
        + (half_error / half_limit if np.isfinite(half_error) else 99.0)
    )
    def finite_or_none(value: float) -> float | None:
        return float(value) if np.isfinite(value) else None

    return {
        "nrmse_percent": nrmse,
        "median_ape_percent": median_ape,
        "experimental_half_s": finite_or_none(experimental_half),
        "predicted_half_s": finite_or_none(predicted_half),
        "half_time_error_percent": finite_or_none(half_error),
        "screen_pass": screen_pass,
        "joint_screen_pass": all(screen_pass.values()),
        "normalized_score": float(normalized_score),
    }


def _case(
    case_id: str,
    data_path: Path,
    time_s: np.ndarray,
    measured: np.ndarray,
    *,
    base_cd: float,
    limits: tuple[float, float, float],
    kind: str,
    predict: Callable[[float], np.ndarray],
) -> dict[str, object]:
    rows = []
    for multiplier in GRID:
        effective_cd = base_cd * multiplier
        values = _metrics(
            time_s,
            measured,
            predict(effective_cd),
            kind=kind,
            limits=limits,
        )
        rows.append(
            {
                "multiplier": multiplier,
                "effective_discharge_coefficient": effective_cd,
                **values,
            }
        )
    best = min(rows, key=lambda row: float(row["normalized_score"]))
    return {
        "case_id": case_id,
        "data_path": data_path.relative_to(ROOT).as_posix(),
        "data_sha256": _sha256(data_path),
        "base_discharge_coefficient": base_cd,
        "grid": list(GRID),
        "screen_limits": {
            "nrmse_percent_max": limits[0],
            "median_ape_percent_max": limits[1],
            "half_time_error_percent_max": limits[2],
        },
        "best_grid_point_by_normalized_score": best,
        "any_grid_point_joint_screen_pass": any(
            bool(row["joint_screen_pass"]) for row in rows
        ),
        "rows": rows,
    }


def run(root: Path) -> dict[str, object]:
    data_2006 = root / "data/public_validation/derived/schefer_2006_figure3b.csv"
    trace_2006 = load_schefer_flow_csv(data_2006)
    data_2007 = root / "data/public_validation/derived/schefer_2007_figure4.csv"
    trace_2007 = load_schefer_2007_pressure_csv(data_2007)
    data_grune = root / "data/public_validation/derived/grune_2014_figure2.csv"
    trace_grune = load_grune_2014_pressure_csv(data_grune)

    cases = [
        _case(
            "schefer_2006_mass_flow",
            data_2006,
            trace_2006.time_s,
            trace_2006.measured_mass_flow_g_s,
            base_cd=1.0,
            limits=(15.0, 20.0, 20.0),
            kind="flow",
            predict=lambda cd: simulate_adiabatic_blowdown_flow(
                trace_2006.time_s,
                inputs=ScheferBlowdownInputs(discharge_coefficient=cd),
            ),
        ),
        _case(
            "schefer_2007_pressure",
            data_2007,
            trace_2007.time_s,
            trace_2007.measured_pressure_psi,
            base_cd=1.0,
            limits=(10.0, 15.0, 20.0),
            kind="pressure",
            predict=lambda cd: simulate_adiabatic_blowdown_pressure(
                trace_2007.time_s,
                inputs=Schefer2007Inputs(discharge_coefficient=cd),
            ),
        ),
        _case(
            "grune_2014_pressure",
            data_grune,
            trace_grune.time_s,
            trace_grune.measured_pressure_bar_abs,
            base_cd=0.8,
            limits=(10.0, 15.0, 20.0),
            kind="pressure",
            predict=lambda cd: predict_pressure_bar_abs(
                trace_grune.time_s,
                inputs=Grune2014Inputs(discharge_coefficient=cd),
            ),
        ),
    ]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_role": "posthoc_development_diagnostic_only",
        "status": "completed_without_modifying_frozen_results",
        "method": {
            "parameter": "discharge_coefficient_multiplier",
            "grid": list(GRID),
            "equivalent_geometry_interpretation": "A diameter multiplier is approximately sqrt(multiplier) for the same Cd because aperture area scales with diameter squared; this is diagnostic only.",
            "outcome_fitting": False,
            "frozen_primary_results_rewritten": False,
        },
        "claim_boundary": "This grid reuses digitised frozen holdout traces after outcome access to diagnose model-form sensitivity. It cannot establish an independent validation claim, select a production parameter, or change the IJHE readiness decision.",
        "cases": cases,
    }


def _markdown(report: dict[str, object]) -> str:
    lines = [
        "# Release-model post-hoc sensitivity diagnostic",
        "",
        "This report is development evidence only. The frozen Schefer 2006/2007 and Grune 2014 holdout results were not changed and no grid point is a new validation claim.",
        "",
        "| Case | Baseline Cd | Best grid Cd | NRMSE | Median APE | Half-time error | Any joint pass |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for case in report["cases"]:
        best = case["best_grid_point_by_normalized_score"]
        half_error = best["half_time_error_percent"]
        half_text = "n/a" if half_error is None else f"{half_error:.2f}%"
        lines.append(
            f"| `{case['case_id']}` | {case['base_discharge_coefficient']:.3g} | "
            f"{best['effective_discharge_coefficient']:.3g} | "
            f"{best['nrmse_percent']:.2f}% | {best['median_ape_percent']:.2f}% | "
            f"{half_text} | "
            f"{str(case['any_grid_point_joint_screen_pass']).lower()} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The declared grid does not produce a joint pass for any of the three traces. The Schefer 2006 and 2007 minima remain at the locked coefficient, while the Grune startup metrics improve at a lower coefficient but its half-pressure endpoint is unavailable. This points to missing model structure (line-pack, wall heat transfer and/or valve dynamics) rather than a defensible single global discharge coefficient.",
            "",
            "The results do not authorize post-hoc parameter replacement in the production twin. A revised model must be frozen before a new external dataset is opened.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("research/release_model_posthoc_sensitivity.json"),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("research/RELEASE_MODEL_POSTHOC_SENSITIVITY.md"),
    )
    args = parser.parse_args()
    root = args.root.resolve()
    report = run(root)
    json_path = args.json_output if args.json_output.is_absolute() else root / args.json_output
    md_path = args.report_output if args.report_output.is_absolute() else root / args.report_output
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
