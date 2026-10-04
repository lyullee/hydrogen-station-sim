"""Diagnose source-boundary identifiability for the frozen MC Default holdout.

This is a development diagnostic, not a validation runner.  It compares the
published source-pressure-3 endpoints with an isothermal estimate for the
reference 0.35 m3 high cascade bank.  It deliberately does not fit a volume,
change the frozen model, or score the vehicle response.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from h2station.tabulated import PropsSI


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/public_validation/processed/mc_default_cases.csv"
OUTPUT = ROOT / "research/mc_default_source_boundary_identifiability_2026_10_04.json"


def density_kg_m3(pressure_mpa: float, temperature_k: float = 298.15) -> float:
    return float(
        PropsSI("Dmass", "P", pressure_mpa * 1.0e6, "T", temperature_k, "Hydrogen")
    )


def pressure_mpa_from_density(
    density_kg_m3_value: float, temperature_k: float = 298.15
) -> float:
    """Invert the tabulated P,T density relation without an unsupported pair."""

    lower_pa, upper_pa = 1.0e5, 150.0e6
    for _ in range(80):
        midpoint_pa = (lower_pa + upper_pa) / 2.0
        midpoint_density = density_kg_m3(midpoint_pa / 1.0e6, temperature_k)
        if midpoint_density < density_kg_m3_value:
            lower_pa = midpoint_pa
        else:
            upper_pa = midpoint_pa
    return (lower_pa + upper_pa) / 2.0e6


def main() -> None:
    rows: list[dict[str, float | str]] = []
    with INPUT.open(newline="", encoding="utf-8-sig") as handle:
        for record in csv.DictReader(handle):
            transferred_mass = float(record["integrated_mass_flow_kg"])
            observed_initial = float(record["source_pressure_3_initial_mpa"])
            observed_final = float(record["source_pressure_3_final_mpa"])

            reference_pressure = 90.0
            reference_volume = 0.35
            reference_initial_mass = (
                density_kg_m3(reference_pressure) * reference_volume
            )
            predicted_final = pressure_mpa_from_density(
                (reference_initial_mass - transferred_mass) / reference_volume
            )
            observed_density_drop = density_kg_m3(observed_initial) - density_kg_m3(
                observed_final
            )

            rows.append(
                {
                    "case_id": record["case_id"],
                    "transferred_mass_kg": transferred_mass,
                    "observed_source_pressure_initial_mpa": observed_initial,
                    "observed_source_pressure_final_mpa": observed_final,
                    "observed_source_pressure_drop_mpa": observed_initial
                    - observed_final,
                    "reference_high_bank_volume_m3": reference_volume,
                    "reference_high_bank_pressure_mpa": reference_pressure,
                    "isothermal_reference_final_pressure_mpa": predicted_final,
                    "isothermal_reference_pressure_drop_mpa": reference_pressure
                    - predicted_final,
                    "conditional_implied_constant_volume_m3": transferred_mass
                    / observed_density_drop,
                }
            )

    payload = {
        "schema_version": 1,
        "recorded_at": "2026-10-04",
        "status": "DEVELOPMENT_DIAGNOSTIC_ONLY",
        "purpose": "Separate source-boundary/topology mismatch from vehicle-model error before any future validation redesign.",
        "input": "data/public_validation/processed/mc_default_cases.csv",
        "cases": rows,
        "method": {
            "temperature_k": 298.15,
            "equation": "tabulated Hydrogen density(P,T), isothermal mass balance, binary pressure inversion",
            "reference_volume_m3": 0.35,
            "reference_initial_pressure_mpa": 90.0,
            "observed_channel": "source_pressure_3_initial_mpa/source_pressure_3_final_mpa",
            "conditional_volume_definition": "transferred_mass / (rho(observed_initial)-rho(observed_final))",
        },
        "interpretation": {
            "finding": "The observed 2.255-4.914 MPa source-pressure drops imply conditional constant volumes of 2.737-8.697 m3, while the current reference high-bank boundary is 0.35 m3 and predicts 30.734-58.621 MPa drops under the same simplified isothermal estimate.",
            "meaning": "This is evidence that source_pressure_3 is not identifiable as the current single 0.35 m3 high-bank state from the public protocol alone. It may represent a larger connected inventory, pressure-regulated upstream boundary, multiple banks, or different thermal/valve behavior.",
            "limitation": "The source channel temperature, internal topology, valve dispatch and regulator logic are not published; the conditional volumes are not fitted parameters and must not be inserted into the production model.",
        },
        "validation_boundary": {
            "full_loop_holdout_eligible": False,
            "frozen_holdout_modified": False,
            "post_outcome_tuning": False,
            "recommended_next_protocol": "Pre-register a partial-station or station-boundary evaluation that supplies source pressure and temperature as measured boundary traces, or obtain bank topology/valve-state logs before comparing internal-bank pressure.",
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
