"""Explain the negative MC Default tank-boundary diagnostic.

The eight MC Default outcomes were already opened, so this report is a
post-outcome diagnostic.  It does not select a geometry, alter the runtime,
or turn a sensitivity result into independent validation.  It records the
physical reasons the frozen tank replay cannot be interpreted as an EOS bug:
the frozen effective-volume rule does not transfer to the declared vessel
capacities, while the public temperature label does not identify an observed
model state.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import numpy as np

from h2station.scenario import capacity_eos_volume_m3
from h2station.tabulated import PropsSI


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED = ROOT / "data/public_validation/processed"
DEFAULT_PROTOCOL = ROOT / "research/mc_default_external_holdout_protocol.json"
DEFAULT_TEMPERATURE_INVENTORY = ROOT / "research/mc_temperature_channel_inventory_2026_10_11.json"
DEFAULT_OUTPUT = ROOT / "research/mc_tank_boundary_failure_diagnosis_2026_10_11.json"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _case(summary: dict[str, str], rows: list[dict[str, str]], frozen_multiplier: float) -> dict:
    capacity_kg = _f(summary, "tank_capacity_kg")
    nominal_volume_m3 = 0.122 * capacity_kg / 4.7
    capacity_eos_volume = capacity_eos_volume_m3(capacity_kg, 70.0e6)
    times = np.asarray([_f(row, "time_s") for row in rows], dtype=float)
    flow_kg_s = np.asarray([_f(row, "mass_flow_g_s") for row in rows], dtype=float) / 1000.0
    pressure_pa = np.asarray([_f(row, "pressure_mpa") for row in rows], dtype=float) * 1.0e6
    temperature_k = np.asarray([_f(row, "tank_temperature_mean_c") for row in rows], dtype=float) + 273.15
    soc = np.asarray([_f(row, "soc_percent") for row in rows], dtype=float)
    initial_density = float(PropsSI("Dmass", "P", pressure_pa[0], "T", temperature_k[0], "Hydrogen"))
    final_density = float(PropsSI("Dmass", "P", pressure_pa[-1], "T", temperature_k[-1], "Hydrogen"))
    measured_mass = float(np.trapezoid(flow_kg_s, times))
    positive_mass = float(np.trapezoid(np.maximum(flow_kg_s, 0.0), times))
    soc_mass_delta = float((soc[-1] - soc[0]) / 100.0 * capacity_kg)
    inferred_volume = measured_mass / (final_density - initial_density)
    temp_columns = [key for key in rows[0] if key.startswith("Ttank") and key.endswith("_G")]
    temp_matrix = np.asarray([[float(row[key]) for key in temp_columns] for row in rows], dtype=float)
    spread = np.ptp(temp_matrix, axis=1) if temp_matrix.size else np.asarray([], dtype=float)
    return {
        "case_id": summary["case_id"],
        "tank_capacity_kg": capacity_kg,
        "temperature_channels": temp_columns,
        "nominal_volume_m3": nominal_volume_m3,
        "frozen_effective_volume_m3": nominal_volume_m3 * frozen_multiplier,
        "capacity_eos_volume_m3": capacity_eos_volume,
        "frozen_to_capacity_eos_volume_ratio": nominal_volume_m3 * frozen_multiplier / capacity_eos_volume,
        "outcome_derived_inferred_volume_m3": inferred_volume,
        "outcome_derived_inferred_to_capacity_eos_ratio": inferred_volume / capacity_eos_volume,
        "initial_pressure_mpa": float(pressure_pa[0] / 1.0e6),
        "final_pressure_mpa": float(pressure_pa[-1] / 1.0e6),
        "initial_temperature_c": float(temperature_k[0] - 273.15),
        "final_temperature_c": float(temperature_k[-1] - 273.15),
        "integrated_signed_flow_mass_kg": measured_mass,
        "integrated_positive_flow_mass_kg": positive_mass,
        "soc_implied_mass_change_kg": soc_mass_delta,
        "flow_to_soc_mass_ratio": measured_mass / soc_mass_delta if soc_mass_delta else None,
        "negative_flow_sample_count": int(np.sum(flow_kg_s < 0.0)),
        "temperature_channel_spread_mean_c": float(np.mean(spread)) if spread.size else None,
        "temperature_channel_spread_peak_c": float(np.max(spread)) if spread.size else None,
    }


def build_report(
    processed: Path = DEFAULT_PROCESSED,
    protocol_path: Path = DEFAULT_PROTOCOL,
    temperature_inventory_path: Path = DEFAULT_TEMPERATURE_INVENTORY,
) -> dict:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    summaries = {
        row["source_member"]: row
        for row in _read_csv(processed / "mc_default_cases.csv")
    }
    frozen_multiplier = float(protocol["frozen_model"]["effective_volume_multiplier"])
    cases = []
    for member in protocol["selected_workbooks"]:
        summary = summaries[member]
        trace = _read_csv(processed / "mc_default_traces" / f"{summary['case_id']}.csv")
        cases.append(_case(summary, trace, frozen_multiplier))
    inventory = json.loads(temperature_inventory_path.read_text(encoding="utf-8"))
    inventory_cases = inventory.get("inventory", {}).get("cases", [])
    inventory_spreads = [
        row["individual_channel_spread_c"]["peak_c"]
        for row in inventory_cases
        if row.get("individual_channel_spread_c", {}).get("peak_c") is not None
    ]
    def mean(key: str) -> float:
        return float(np.mean([row[key] for row in cases]))
    spread_peaks = [
        row["temperature_channel_spread_peak_c"]
        for row in cases
        if row["temperature_channel_spread_peak_c"] is not None
    ]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(),
        "artifact_type": "mc_tank_boundary_failure_diagnosis",
        "evidence_role": "post_outcome_development_diagnostic_only",
        "post_outcome": True,
        "parameter_fitting": False,
        "runtime_parameter_changed": False,
        "frozen_model": {
            "effective_volume_multiplier": frozen_multiplier,
            "source": _display_path(protocol_path),
        },
        "aggregate": {
            "case_count": len(cases),
            "frozen_to_capacity_eos_volume_ratio_mean": mean("frozen_to_capacity_eos_volume_ratio"),
            "frozen_to_capacity_eos_volume_ratio_median": float(np.median([row["frozen_to_capacity_eos_volume_ratio"] for row in cases])),
            "outcome_derived_inferred_to_capacity_eos_ratio_median": float(np.median([row["outcome_derived_inferred_to_capacity_eos_ratio"] for row in cases])),
            "flow_to_soc_mass_ratio_mean": mean("flow_to_soc_mass_ratio"),
            "temperature_channel_spread_peak_max_c": max(spread_peaks) if spread_peaks else None,
            "source_inventory_temperature_spread_peak_max_c": max(inventory_spreads) if inventory_spreads else None,
            "negative_flow_sample_count_total": int(sum(row["negative_flow_sample_count"] for row in cases)),
        },
        "diagnosis": [
            {
                "finding": "eos_mass_closure_is_not_the_primary_failure",
                "evidence": "The independent MC SOC/EOS boundary screen passes 8/8 cases; this report also retains co-located pressure/temperature density and flow/SOC closure diagnostics.",
            },
            {
                "finding": "frozen_effective_volume_does_not_transfer_cleanly",
                "evidence": "The prospectively frozen effective-volume rule is compared with each declared capacity converted using the runtime Hydrogen EOS. The comparison is diagnostic only because the MC outcomes were already inspected.",
            },
            {
                "finding": "temperature_observation_semantics_are_unresolved",
                "evidence": "The source-channel inventory records individual tank channels for all eight cases, with a maximum within-case peak spread of 8.532 °C. The processed replay keeps only the declared mean projection, and the public tank-mean label does not identify gas, liner, shell, or sensor weighting.",
            },
            {
                "finding": "flow_channel_has_small_reverse_flow_segments",
                "evidence": "Negative mass-flow samples are recorded rather than silently treated as an independent leak or station boundary; the replay clips them because it is a fill-only tank diagnostic.",
            },
        ],
        "cases": cases,
        "temperature_channel_inventory": {
            "artifact": _display_path(temperature_inventory_path),
            "case_count": len(inventory_cases),
            "cases_with_individual_channels": sum(
                bool(row.get("individual_temperature_channels"))
                for row in inventory_cases
            ),
            "peak_spread_max_c": max(inventory_spreads) if inventory_spreads else None,
            "claim_limit": inventory.get("interpretation", {}).get("claim_boundary"),
        },
        "required_next_data": [
            "manufacturer-certified internal volume or a predeclared capacity-to-volume rule for each MC vessel",
            "sensor location and channel definition for the reported tank temperature",
            "independent net mass channel or uncertainty for the flow integrator",
            "a new untouched external tank/vehicle experiment if this geometry rule is to be claimed prospectively",
        ],
        "claim_boundary": "This report explains a negative vehicle-tank boundary diagnostic. It cannot select a production geometry, revise the frozen MC holdout, validate station control or safety response, or close the full-loop station-to-vehicle gate.",
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", type=Path, default=DEFAULT_PROCESSED)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--temperature-inventory", type=Path, default=DEFAULT_TEMPERATURE_INVENTORY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(args.processed, args.protocol, args.temperature_inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["aggregate"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
