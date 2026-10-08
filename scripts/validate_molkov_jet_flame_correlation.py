"""Benchmark the Molkov flame-length implementation against Table 1 rows."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.risk.jet_flame import (  # noqa: E402
    MOLKOV_SAFFERS_DOI,
    jet_flame_length_m,
)


PAPER_PDF_SHA256 = "b9b8993f06177a892053070c367af378fdfa9918aeb5eb2174a1806308ed7f86"
IMPLEMENTATION = ROOT / "src/h2station/risk/jet_flame.py"

# Direct transcription of the high-pressure Schefer and Proust rows in Table 1.
# The paper reports L_F/d_N and mass flow; measured L_F is their product.
TABLE_ROWS = (
    *(("Schefer 2006", 7.94, ratio, flow) for ratio, flow in
      ((544, 57), (363, 23), (277, 6.9), (223, 2.1), (191, 1.1))),
    *(("Schefer 2007", 5.08, ratio, flow) for ratio, flow in
      ((1969, 360), (1722, 230), (1378, 140), (965, 64), (669, 28), (472, 11))),
    *(("Proust 2009", 3.0, ratio, flow) for ratio, flow in
      ((577, 9), (1933, 250), (1377, 66), (791, 23), (1220, 50), (675, 15))),
    *(("Proust 2009", 2.0, ratio, flow) for ratio, flow in
      ((2551, 110), (1977, 46), (1186, 21), (794, 12))),
    *(("Proust 2009", 1.0, ratio, flow) for ratio, flow in
      ((3129, 32), (2567, 20), (1696, 11), (1329, 6.6))),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_report() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for source, diameter_mm, measured_ratio, mass_flow_g_s in TABLE_ROWS:
        diameter_m = diameter_mm / 1000.0
        measured_m = measured_ratio * diameter_m
        predicted_m = jet_flame_length_m(mass_flow_g_s / 1000.0, diameter_m)
        absolute_percentage_error = abs(predicted_m - measured_m) / measured_m * 100.0
        rows.append({
            "source_series": source,
            "nozzle_diameter_mm": diameter_mm,
            "paper_flame_length_over_diameter": measured_ratio,
            "paper_mass_flow_g_s": mass_flow_g_s,
            "paper_flame_length_m": measured_m,
            "implementation_flame_length_m": predicted_m,
            "absolute_percentage_error": absolute_percentage_error,
        })

    errors = [float(row["absolute_percentage_error"]) for row in rows]
    within_30 = sum(error <= 30.0 for error in errors)
    criteria = {
        "mean_absolute_percentage_error_at_most_20_percent": statistics.mean(errors) <= 20.0,
        "at_least_80_percent_of_rows_within_30_percent": within_30 / len(rows) >= 0.80,
        "maximum_absolute_percentage_error_at_most_50_percent": max(errors) <= 50.0,
    }
    passed = all(criteria.values())
    return {
        "schema_version": 1,
        "artifact_type": "molkov_2011_jet_flame_literature_benchmark",
        "status": "passed" if passed else "failed",
        "generated_date_utc": "2026-10-08",
        "source": {
            "citation": (
                "Molkov and Saffers, The Correlation for Non-Premixed Hydrogen "
                "Jet Flame Length in Still Air, Fire Safety Science 10 (2011) 933-943"
            ),
            "doi": MOLKOV_SAFFERS_DOI,
            "url": "https://doi.org/10.3801/IAFSS.FSS.10-933",
            "public_access": True,
            "redistribution_license_asserted": False,
            "paper_pdf_sha256": PAPER_PDF_SHA256,
            "experimental_case_count_reported": 123,
            "benchmark_table": "Table 1",
        },
        "implementation": {
            "path": str(IMPLEMENTATION.relative_to(ROOT)).replace("\\", "/"),
            "sha256": _sha256(IMPLEMENTATION),
            "equation": "L_F = 76 * (mass_flow_kg_s * nozzle_diameter_m)^0.347",
        },
        "predeclared_descriptive_screen": criteria,
        "rows": rows,
        "aggregate": {
            "case_count": len(rows),
            "mean_absolute_percentage_error": statistics.mean(errors),
            "median_absolute_percentage_error": statistics.median(errors),
            "maximum_absolute_percentage_error": max(errors),
            "within_30_percent_count": within_30,
            "within_30_percent_fraction": within_30 / len(rows),
            "all_passed": passed,
        },
        "runtime_contract": {
            "hybrid_replacement_of_hyram": False,
            "uses_modeled_consequence_mass_flow": True,
            "uses_physical_release_diameter": True,
            "visible_flame_length_only": True,
            "thermal_harm_distance": False,
            "site_safety_distance": False,
        },
        "claim_boundary": (
            "This is a same-publication transcription and descriptive comparison "
            "against 25 high-pressure Table 1 rows, not an independent project "
            "validation. It estimates visible free-jet flame length in still air. "
            "It does not establish radiation harm, separation, evacuation, "
            "impingement, obstacle, wind, confinement, frequency, or full-station performance."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "research/molkov_2011_jet_flame_benchmark.json",
    )
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if report["status"] != "passed":
        raise SystemExit("Molkov jet-flame literature benchmark failed")


if __name__ == "__main__":
    main()
