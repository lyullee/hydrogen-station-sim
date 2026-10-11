"""Create a post-outcome diagnostic for the Proust release-boundary mismatch.

This script deliberately does not alter the frozen evaluator, production
parameters, or the primary holdout result.  It asks a narrower question:
whether the observed diameter-dependent effective discharge coefficients are
consistent with one missing global coefficient, and records the published
source/line/orifice semantics that must be resolved before a network model can
be evaluated prospectively.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from math import pi
from pathlib import Path

from h2station.proust_release_validation import load_digitized_points, predict_mass_flow_kg_s


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data", type=Path,
        default=Path("data/public_validation/derived/proust_90mpa_release.csv"),
    )
    parser.add_argument(
        "--protocol", type=Path,
        default=Path("research/proust_release_holdout_protocol.json"),
    )
    parser.add_argument(
        "--result", type=Path,
        default=Path("research/proust_release_holdout_result.json"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("research/proust_release_boundary_semantics_diagnostic_2026_10_12.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    points = load_digitized_points(args.data)

    grouped: dict[float, list[dict[str, float | int | str]]] = defaultdict(list)
    for point in points:
        area = pi * (point.nozzle_diameter_mm / 1000.0) ** 2 / 4.0
        unit_cd_flow = predict_mass_flow_kg_s(point, discharge_coefficient=1.0)
        effective_cd = point.measured_mass_flow_kg_s / unit_cd_flow
        grouped[point.nozzle_diameter_mm].append({
            "case_id": point.case_id,
            "point_index": point.point_index,
            "source_pressure_mpa_abs": point.source_pressure_pa_abs / 1.0e6,
            "source_temperature_k": point.source_temperature_k,
            "measured_mass_flow_g_s": point.measured_mass_flow_kg_s * 1000.0,
            "nominal_area_m2": area,
            "effective_cd": effective_cd,
        })

    series = []
    for diameter, rows in sorted(grouped.items()):
        coefficients = [float(row["effective_cd"]) for row in rows]
        median = _median(coefficients)
        series.append({
            "nozzle_diameter_mm": diameter,
            "points": len(rows),
            "effective_cd_median": median,
            "effective_cd_min": min(coefficients),
            "effective_cd_max": max(coefficients),
            "effective_cd_range": max(coefficients) - min(coefficients),
            "global_cd_0_8_relative_error_percent": (median / 0.8 - 1.0) * 100.0,
            "point_diagnostics": rows,
        })

    report = {
        "schema_version": 1,
        "artifact_type": "proust_release_boundary_semantics_diagnostic",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_role": "post_outcome_diagnostic_only",
        "claim_controlling": False,
        "parameter_fitting": False,
        "production_model_parameter_changed": False,
        "frozen_primary_result": {
            "path": str(args.result).replace("\\", "/"),
            "sha256": _sha256(args.result),
            "claim_supported": json.loads(args.result.read_text(encoding="utf-8"))["aggregate"]["claim_supported"],
        },
        "input_hashes": {
            "protocol_sha256": _sha256(args.protocol),
            "data_sha256": _sha256(args.data),
        },
        "published_apparatus_semantics": {
            "source_volume_m3": 0.025,
            "supply_line_length_m": 10.0,
            "supply_line_diameter_m": 0.010,
            "terminal_orifice_diameters_mm": [1.0, 2.0, 3.0],
            "valve_opening_time_s": 0.1,
            "pressure_basis": protocol["digitization"]["pressure_basis"],
            "temperature_observation": "source/upstream temperature is paired to each digitized state; the published method describes measurement near the upstream orifice, while the pressure is reported for the source/reservoir",
            "unresolved_network_inputs": [
                "as-built line bore and dead volume",
                "complete valve position trace and valve location",
                "line pressure and line temperature",
                "terminal effective area and upstream restriction loss",
            ],
        },
        "series": series,
        "interpretation": (
            "The effective coefficient varies by nominal diameter, so one global "
            "coefficient cannot reconcile the three series. This is consistent "
            "with omitted supply-line/valve resistance or a pressure-temperature "
            "boundary semantic mismatch. It is a development diagnostic only; "
            "it does not select a new coefficient, repair the frozen holdout, "
            "or validate a network model."
        ),
        "promotion_rule": (
            "Resolve the apparatus boundary with rights-cleared synchronized "
            "line/valve/terminal measurements, freeze a new prospective protocol, "
            "and evaluate a new holdout before runtime or claim promotion."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
