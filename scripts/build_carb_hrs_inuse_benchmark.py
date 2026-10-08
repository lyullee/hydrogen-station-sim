"""Build a bounded field benchmark from the 2024 CARB in-use HRS report.

The public report exposes station-level aggregate counts and figures, not the
synchronized dispenser/vehicle rows needed for dynamic-model validation.  The
artifact produced here therefore supports field-relevance and functional-gap
audits only.  Supplying ``--source-pdf`` additionally verifies that the local
copy is the exact document used for the curated transcription.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any


REPORT_SHA256 = "a49e46baa1151847b0d786d0a40c2cc08928e28043152e64ae95a22a06784766"
REPORT_URL = (
    "https://ww2.arb.ca.gov/sites/default/files/2024-12/"
    "Existing%20Light-Duty%20Hydrogen%20Refueling%20Stations%20In-Use%20Study%20Report%20ADA%20AL.pdf"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(source_pdf: Path | None = None) -> dict[str, Any]:
    source_verified = None
    if source_pdf is not None:
        observed_hash = _sha256(source_pdf)
        if observed_hash != REPORT_SHA256:
            raise ValueError(
                f"CARB report SHA-256 mismatch: expected {REPORT_SHA256}, got {observed_hash}"
            )
        source_verified = True

    protocol_fault = {
        "fuel_delivery_temperature_at_cooldown": [2, 0, 4],
        "fuel_delivery_temperature_tolerance": [2, 0, 4],
        "upper_pressure_tolerance": [10, 0, 12],
        "lower_pressure_tolerance": [14, 0, 8],
        "mat30_above_maximum_allowed_temperature": [9, 0, 7],
    }
    general_fault = {
        "chss_capacity_range": [21, 0, 1],
        "ambient_temperature_limits": [10, 0, 12],
        "minimum_fuel_delivery_temperature": [10, 0, 12],
        "maximum_chss_gas_temperature": [21, 0, 1],
        "minimum_initial_chss_pressure": [19, 1, 2],
        "maximum_initial_chss_pressure": [20, 1, 1],
        "maximum_chss_pressure_with_communication": [21, 0, 1],
        "maximum_chss_pressure_without_communication": [13, 0, 9],
        "maximum_state_of_charge": [19, 1, 2],
        "maximum_flow_rate": [12, 1, 9],
        "maximum_startup_mass": [13, 0, 9],
        "minimum_startup_time": [10, 0, 12],
    }
    communications = {
        "abort_signal": [19, 2, 1],
        "halt_signal": [20, 1, 1],
        "data_loss_and_resumed_fueling": [15, 4, 3],
        "invalid_crc": [13, 8, 1],
        "invalid_defined_data_value": [13, 8, 1],
    }
    fueling = {
        "chss_category_a": [14, 5, 3],
        "chss_category_b": [13, 7, 2],
        "chss_category_c": [8, 11, 3],
        "original_t40_temperature_category_met": [2, 18, 2],
    }
    return {
        "schema_version": 1,
        "artifact_type": "public_real_station_field_benchmark",
        "generated_on": str(date.today()),
        "source": {
            "title": "Existing Light-Duty Hydrogen Refueling Stations In-Use Study Report",
            "institution": "California Air Resources Board",
            "publication_date": "2024-12",
            "url": REPORT_URL,
            "sha256": REPORT_SHA256,
            "local_source_hash_verified": source_verified,
            "study_period_reported": "2023-10 to 2024-05",
            "test_basis": "abbreviated CSA/ANSI HGV 4.3:22 assessment of SAE J2601 conformance",
        },
        "population": {
            "stations_tested": 22,
            "estimated_operational_station_population": 55,
            "sample_fraction": 0.40,
            "stations_passing_all_hgv_4_3_tests": 0,
            "stations_passing_all_fault_and_communications_tests": 5,
            "stations_passing_all_nine_fueling_performance_metrics": 4,
            "in_use_protocol_counts": {"mc_formula_based": 16, "table_based": 6},
        },
        "category_station_pass_rates": {
            "general_fault": 0.455,
            "protocol_fault": 0.409,
            "communications": 0.500,
            "fueling_performance": 0.182,
        },
        "result_count_order": ["pass", "fail", "undetermined"],
        "tables": {
            "protocol_fault": {
                "report_page": 14,
                "report_table": 2,
                "population_note": "Six table-based and sixteen MC-formula stations; applicable denominators vary by test.",
                "results": protocol_fault,
            },
            "general_fault": {
                "report_page": 16,
                "report_table": 3,
                "results": general_fault,
            },
            "communications": {
                "report_page": 17,
                "report_table": 4,
                "results": communications,
            },
            "fueling_performance": {
                "report_page": 18,
                "report_table": 5,
                "results": fueling,
            },
        },
        "digital_twin_functional_coverage": {
            "represented": [
                "configurable vehicle capacity, initial pressure, target pressure and target SOC",
                "maximum mass-flow limiting",
                "maximum vehicle-gas-temperature termination",
                "delivery-temperature and precooling boundary",
                "operator stop and ESD termination",
                "dispenser-specific abort and halt communication fault injection with conservative termination",
                "dispenser-specific communication loss, invalid CRC and invalid defined-value fault injection with conservative termination",
            ],
            "partial": [
                "pressure-ramp reference control without a certified SAE J2601 lookup table",
                "HGV 4.3 communication error behavior without SAE J2799 message encoding or certified protocol tables",
            ],
            "missing": [
                "maximum-startup-mass and minimum-startup-time conformance tests",
                "upper/lower pressure-corridor conformance evaluator",
                "protocol-selectable non-communication fallback and resumed-fueling state machine",
                "explicit T30/T40 fueling-category conformance report",
            ],
        },
        "eligibility": {
            "field_relevance_benchmark": True,
            "functional_gap_audit": True,
            "llm_decision_support_grounding": True,
            "dynamic_model_parameter_calibration": False,
            "full_loop_external_holdout": False,
            "vehicle_trace_validation": False,
        },
        "claim_boundary": (
            "This CARB artifact is a public 22-station aggregate field benchmark. "
            "It demonstrates the operational importance and observed pass/fail prevalence of fault, "
            "communication and fueling-performance checks. It contains no synchronized station-dispenser-vehicle "
            "raw traces and therefore does not validate digital-twin pressure, temperature, flow or consequence predictions."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pdf", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/carb_2024_hrs_inuse_field_benchmark_2026_10_08.json"),
    )
    args = parser.parse_args()
    artifact = build(args.source_pdf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "output": str(args.output),
        "source_hash_verified": artifact["source"]["local_source_hash_verified"],
        "stations_tested": artifact["population"]["stations_tested"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
