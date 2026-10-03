"""Compare a Proust-derived series restriction against consumed datasets."""

from __future__ import annotations

import argparse
import ast
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from h2station.proust_release_validation import load_digitized_points
from h2station.release_network_development import (
    ReleaseObservation,
    evaluate_development_series,
    predict_observations,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_imamura_hyram_test(path: Path) -> list[ReleaseObservation]:
    """Read the published arrays without importing the GPL HyRAM package."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    payload: dict[str, list[float]] | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "Test_Imamura_2008":
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Assign):
                continue
            if not any(
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
                and target.attr == "data"
                for target in child.targets
            ):
                continue
            value = child.value
            if (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id == "dict"
                and len(value.args) == 1
            ):
                candidate = ast.literal_eval(value.args[0])
                if isinstance(candidate, dict) and {"d_mm", "P_MPa", "Flow"} <= candidate.keys():
                    payload = candidate
                    break
    if payload is None:
        raise ValueError("Imamura arrays were not found in the HyRAM validation source")
    if not (len(payload["d_mm"]) == len(payload["P_MPa"]) == len(payload["Flow"])):
        raise ValueError("Imamura arrays are not aligned")
    return [
        ReleaseObservation(
            series_id=f"imamura-{diameter:g}mm",
            diameter_mm=float(diameter),
            source_pressure_pa_abs=101_325.0 + float(pressure) * 1.0e6,
            source_temperature_k=293.0,
            measured_mass_flow_kg_s=float(flow),
        )
        for diameter, pressure, flow in zip(
            payload["d_mm"], payload["P_MPa"], payload["Flow"], strict=True
        )
    ]


def _proust_observations(path: Path) -> list[ReleaseObservation]:
    return [
        ReleaseObservation(
            series_id=point.case_id,
            diameter_mm=point.nozzle_diameter_mm,
            source_pressure_pa_abs=point.source_pressure_pa_abs,
            source_temperature_k=point.source_temperature_k,
            measured_mass_flow_kg_s=point.measured_mass_flow_kg_s,
        )
        for point in load_digitized_points(path)
    ]


def _evaluate_by_series(
    observations: list[ReleaseObservation],
    *,
    nozzle_cd: float,
    supply_diameter_mm: float | None,
) -> list[dict[str, object]]:
    results = []
    for series_id in sorted({point.series_id for point in observations}):
        group = [point for point in observations if point.series_id == series_id]
        predicted = predict_observations(
            group,
            nozzle_discharge_coefficient=nozzle_cd,
            supply_diameter_mm=supply_diameter_mm,
            supply_discharge_coefficient=0.8,
        )
        results.append(asdict(evaluate_development_series(group, predicted)))
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--proust-data", type=Path,
        default=Path("data/public_validation/derived/proust_90mpa_release.csv"),
    )
    parser.add_argument(
        "--hyram-source", type=Path,
        default=Path("data/public_validation/raw/hyram-v6.1/tests/hyram/validation/test_heatflux.py"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("research/release_network_development.json"),
    )
    args = parser.parse_args()

    proust = _proust_observations(args.proust_data)
    imamura = _load_imamura_hyram_test(args.hyram_source)
    models = {
        "direct_aperture_cd_0_8": {"nozzle_cd": 0.8, "supply_diameter_mm": None},
        "direct_aperture_cd_1_0": {"nozzle_cd": 1.0, "supply_diameter_mm": None},
        "proust_selected_series_restriction": {
            "nozzle_cd": 0.91,
            "supply_diameter_mm": 2.62,
        },
    }
    comparisons: dict[str, object] = {}
    for name, parameters in models.items():
        comparisons[name] = {
            "parameters": {
                **parameters,
                "supply_discharge_coefficient": 0.8,
            },
            "proust": _evaluate_by_series(proust, **parameters),
            "imamura": _evaluate_by_series(imamura, **parameters),
        }

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_role": "consumed_development_only",
        "eligible_as_confirmatory_validation": False,
        "contamination_disclosure": {
            "proust_outcomes_viewed_before_parameter_selection": True,
            "imamura_numeric_outcomes_viewed_before_analysis_formalization": True,
            "reason": (
                "The equivalent restriction was selected after the Proust holdout failed, "
                "and the HyRAM Imamura arrays were inspected before this diagnostic was formalized."
            ),
        },
        "sources": {
            "proust_data": str(args.proust_data).replace("\\", "/"),
            "proust_data_sha256": _sha256(args.proust_data),
            "imamura_hyram_source": str(args.hyram_source).replace("\\", "/"),
            "imamura_hyram_source_sha256": _sha256(args.hyram_source),
            "imamura_original_citation": (
                "Imamura T, Mogi T, Wada Y. Sci Technol Energ Mater 2008;69(1):7-11."
            ),
        },
        "reference_screens_not_validation_gates": {
            "nrmse_percent_peak_measured_max": 15.0,
            "median_absolute_percentage_error_percent_max": 20.0,
        },
        "models": comparisons,
        "interpretation": {
            "finding": (
                "The Proust-selected fixed supply restriction improves the consumed Proust "
                "series but transfers poorly as Imamura aperture diameter increases."
            ),
            "physical_inference": (
                "The fitted restriction is apparatus-specific upstream/valve resistance, "
                "not a universal hydrogen nozzle correction."
            ),
            "next_model_requirement": (
                "Represent known valve, line-pack and pipe geometry explicitly and test the "
                "locked model on a numerically untouched external campaign."
            ),
            "claim_supported": False,
        },
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
