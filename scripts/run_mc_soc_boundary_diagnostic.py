"""Check SOC semantics against the measured MC pressure/temperature boundary.

This is a P0 development diagnostic, not a model fit.  It asks whether the
published SOC channel is consistent with the same hydrogen EOS used by the
project and whether measured mass flow closes against the observed density.
Keeping this separate from the tank replay prevents a bad volume/thermal model
from being mislabelled as an SOC-definition failure.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import numpy as np

from h2station.tabulated import PropsSI


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data/public_validation/processed"
PROTOCOL = ROOT / "research/mc_default_external_holdout_protocol.json"
DEFAULT_OUTPUT = ROOT / "research/mc_soc_boundary_diagnostic_2026_10_10.json"
REFERENCE_PRESSURE_PA = 70.0e6
REFERENCE_TEMPERATURE_K = 288.15
SCREENING_LIMITS = {
    "soc_definition_rmse_percentage_points": 1.0,
    "soc_definition_final_abs_error_percentage_points": 1.0,
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _f(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    if value in ("", None, "None"):
        raise ValueError(f"missing {key}")
    return float(value)


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _case_summary(summary: dict[str, str], rows: list[dict[str, str]], reference_density: float) -> dict[str, float]:
    pressure = np.asarray([_f(row, "pressure_mpa") for row in rows], dtype=float)
    temperature = np.asarray([_f(row, "tank_temperature_mean_c") for row in rows], dtype=float)
    soc = np.asarray([_f(row, "soc_percent") for row in rows], dtype=float)
    flow = np.asarray([_f(row, "mass_flow_g_s") for row in rows], dtype=float)
    time_s = np.asarray([_f(row, "time_s") for row in rows], dtype=float)
    density = np.asarray([
        float(PropsSI("Dmass", "P", p * 1.0e6, "T", t + 273.15, "Hydrogen"))
        for p, t in zip(pressure, temperature)
    ])
    eos_soc = 100.0 * density / reference_density
    nominal_volume = _f(summary, "tank_capacity_kg") / reference_density
    mass = density[0] * nominal_volume + np.concatenate([
        [0.0],
        np.cumsum((flow[1:] + flow[:-1]) * 0.5 * np.diff(time_s)) / 1000.0,
    ])
    inferred_volume_ratio = mass / density / nominal_volume
    return {
        "soc_definition_rmse_percentage_points": float(
            np.sqrt(np.mean((eos_soc - soc) ** 2))
        ),
        "soc_definition_final_error_percentage_points": float(eos_soc[-1] - soc[-1]),
        "inferred_volume_ratio_median": float(np.median(inferred_volume_ratio)),
        "inferred_volume_ratio_final": float(inferred_volume_ratio[-1]),
    }


def run(
    *,
    processed: Path = PROCESSED,
    protocol: Path = PROTOCOL,
) -> dict[str, object]:
    protocol_record = json.loads(protocol.read_text(encoding="utf-8"))
    summaries = {
        row["case_id"]: row
        for row in _read_csv(processed / "mc_default_cases.csv")
        if row.get("case_id")
    }
    selected_members = protocol_record["selected_workbooks"]
    selected = [
        row for row in summaries.values()
        if row.get("source_member") in selected_members
    ]
    if len(selected) != 8:
        raise ValueError(f"expected 8 frozen MC cases, found {len(selected)}")
    reference_density = float(
        PropsSI("Dmass", "P", REFERENCE_PRESSURE_PA, "T", REFERENCE_TEMPERATURE_K, "Hydrogen")
    )
    cases = []
    for summary in selected:
        trace = processed / "mc_default_traces" / f"{summary['case_id']}.csv"
        cases.append(_case_summary(summary, _read_csv(trace), reference_density))
    rmse = np.asarray([item["soc_definition_rmse_percentage_points"] for item in cases])
    final = np.asarray([
        abs(item["soc_definition_final_error_percentage_points"])
        for item in cases
    ])
    median_ratio = np.asarray([
        item["inferred_volume_ratio_median"] for item in cases
    ])
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "artifact_type": "mc_soc_and_mass_boundary_diagnostic",
        "evidence_role": "development_diagnostic_only",
        "post_outcome": True,
        "parameter_fitting": False,
        "runtime_parameter_updated": False,
        "case_count": len(cases),
        "reference_state": {
            "pressure_mpa": REFERENCE_PRESSURE_PA / 1.0e6,
            "temperature_c": REFERENCE_TEMPERATURE_K - 273.15,
        },
        "screening_limits": SCREENING_LIMITS,
        "aggregate": {
            "soc_definition_rmse_percentage_points_mean": float(np.mean(rmse)),
            "soc_definition_rmse_percentage_points_max": float(np.max(rmse)),
            "soc_definition_final_abs_error_percentage_points_mean": float(np.mean(final)),
            "soc_definition_final_abs_error_percentage_points_max": float(np.max(final)),
            "inferred_volume_ratio_median": float(np.median(median_ratio)),
            "inferred_volume_ratio_p10": float(np.percentile(median_ratio, 10)),
            "inferred_volume_ratio_p90": float(np.percentile(median_ratio, 90)),
            "soc_definition_screen_pass_count": int(
                np.sum(
                    (rmse <= SCREENING_LIMITS["soc_definition_rmse_percentage_points"])
                    & (final <= SCREENING_LIMITS["soc_definition_final_abs_error_percentage_points"])
                )
            ),
        },
        "interpretation": (
            "The measured SOC channel is checked against EOS density calculated "
            "from the co-located observed pressure and tank temperature. The "
            "inferred volume ratio is a mass-closure diagnostic only; it is not a "
            "post-outcome parameter choice."
        ),
        "claim_boundary": (
            "This diagnostic does not validate the station controller, select a "
            "vehicle geometry, revise the frozen MC holdout, or support a safety claim."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path, default=PROCESSED)
    parser.add_argument("--protocol", type=Path, default=PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(processed=args.processed, protocol=args.protocol)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
