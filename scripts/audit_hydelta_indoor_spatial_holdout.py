"""Audit HyDelta D6A.1 against the pre-access spatial-holdout protocol.

The protocol deliberately forbids digitising plotted traces or colour-coded
tables to rescue eligibility.  This audit therefore records report structure,
file identity and the availability of each frozen input, then stops before any
model score when a required machine-readable spatial field is absent.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DOI = "10.5281/zenodo.8154318"
EXPECTED_FILE = (
    "D6A_1_HyDelta_Tweede_Tranche_Experiments_"
    "Hydrogen_Outflow_in_Closed_Spaces_EN.pdf"
)
EXPECTED_BYTES = 7_112_634
EXPECTED_MD5 = "686abfae74bc1c2b04345731b4fdc323"
EXPECTED_SHA256 = "fbbc2ce6b411c15cb36f20f6e283a67f8a02a3bd53e919e6bcef88fcf2a4e9f7"


def _digest(path: Path, algorithm: str) -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def audit(pdf_path: Path, protocol_path: Path) -> dict[str, Any]:
    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_path)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    reader = PdfReader(pdf_path)
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    text = _normalise(extracted)

    identity = {
        "file": pdf_path.name,
        "bytes": pdf_path.stat().st_size,
        "md5": _digest(pdf_path, "md5"),
        "sha256": _digest(pdf_path, "sha256"),
        "page_count": len(reader.pages),
    }
    identity_match = bool(
        identity["file"] == EXPECTED_FILE
        and identity["bytes"] == EXPECTED_BYTES
        and identity["md5"] == EXPECTED_MD5
        and identity["sha256"] == EXPECTED_SHA256
        and identity["page_count"] == 85
    )

    report_checks = {
        "actual_hydrogen_test_medium_reported": "gas types hydrogen/natural gas" in text,
        "fifty_sensor_matrix_reported": "matrix of 50 gas sensors" in text,
        "sensor_locations_change_by_experiment_reported": (
            "for each experiment, the location of the sensors can be changed" in text
        ),
        "four_hydrogen_release_rates_reported": all(
            item in text for item in ("50", "100", "300", "1000 dm3/h")
        ),
        "eight_configuration_codes_reported": (
            "configuration code 1 3 4 7 7/0.5 7/1 8/0.5 8/1" in text
        ),
        "source_location_is_figure_only": (
            "location of the outflow (blue dot)" in text
        ),
        "responses_are_graphs": (
            "measurement graphs are included in full in appendix v" in text
        ),
        "summary_uses_colour_categories": (
            "the final concentration of each measurement is indicated by colour" in text
        ),
        "aggregate_final_average_table_reported": (
            "ventilation rate and final average concentration" in text
        ),
    }

    # Table 4 reports eight configurations and four H2 flow rates.  This is an
    # experiment-count inventory, not a sensor-response extraction.
    hydrogen_experiments_reported = 32 if (
        report_checks["actual_hydrogen_test_medium_reported"]
        and report_checks["eight_configuration_codes_reported"]
        and report_checks["four_hydrogen_release_rates_reported"]
    ) else None

    eligibility = {
        "minimum_hydrogen_experiments": {
            "required": protocol["eligibility"]["minimum_hydrogen_experiments"],
            "observed": hydrogen_experiments_reported,
            "passed": bool(hydrogen_experiments_reported and hydrogen_experiments_reported >= 4),
        },
        "minimum_mapped_sensors_per_experiment": {
            "required": protocol["eligibility"]["minimum_mapped_sensors_per_experiment"],
            "observed": 50 if report_checks["fifty_sensor_matrix_reported"] else None,
            "passed": bool(report_checks["fifty_sensor_matrix_reported"]),
            "qualification": (
                "The report states 50 sensors, but this does not satisfy the separate "
                "same-frame numeric coordinate requirement."
            ),
        },
        "source_coordinates": {
            "required": True,
            "observed": "top-view blue-dot figure only",
            "passed": False,
        },
        "sensor_coordinates_in_same_frame": {
            "required": True,
            "observed": (
                "layout photographs/figures and height groups; no tabulated numeric "
                "per-sensor coordinates or report companion data"
            ),
            "passed": False,
        },
        "release_orientation_class": {
            "required": True,
            "observed": "gas-valve photograph/schematic without a declared orientation class",
            "passed": False,
        },
        "per_sensor_numeric_response": {
            "required": True,
            "observed": (
                "multi-sensor plots plus colour-coded final-concentration categories; "
                "no tabulated per-sensor maximum, plateau or release-window mean"
            ),
            "passed": False,
        },
    }
    failed = [name for name, item in eligibility.items() if not item["passed"]]
    eligible = identity_match and not failed

    return {
        "schema_version": 1,
        "artifact_type": "pre_access_frozen_hydelta_spatial_holdout_eligibility_result",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": (
            "ELIGIBLE_FOR_FROZEN_SPATIAL_EVALUATION"
            if eligible else "INELIGIBLE_NO_MODEL_EVALUATION"
        ),
        "protocol": {
            "id": protocol["protocol_id"],
            "frozen_at": protocol["frozen_at"],
            "pre_access_status": protocol["status"],
            "path": str(protocol_path.relative_to(ROOT)).replace("\\", "/"),
            "formula_change_after_access": False,
            "figure_digitisation_performed": False,
        },
        "source": {
            "title": protocol["source"]["title"],
            "doi": DOI,
            "record_url": "https://zenodo.org/records/8154318",
            "publication_date": "2023-07-17",
            "license": "CC BY 4.0",
            "access_right": "open",
            "publisher_file_identity": {
                "expected_bytes": EXPECTED_BYTES,
                "expected_md5": EXPECTED_MD5,
                "expected_sha256": EXPECTED_SHA256,
                "observed": identity,
                "identity_match": identity_match,
            },
            "raw_pdf_committed": False,
        },
        "report_checks": report_checks,
        "eligibility": eligibility,
        "decision": {
            "eligible_for_primary_spatial_holdout": eligible,
            "failed_required_fields": failed,
            "model_evaluation_executed": False if not eligible else None,
            "independent_validation_pass": False,
            "runtime_candidate_enabled": False,
            "reason": (
                "The report supplies an actual-hydrogen experiment matrix and 50-sensor "
                "coverage, but the frozen rank test cannot be reproduced without numeric "
                "source/sensor coordinates, a declared orientation class and tabulated "
                "per-sensor responses. The protocol prohibits graph or colour digitisation."
            ),
        },
        "usable_evidence": {
            "actual_hydrogen_experiment_count_inventory": hydrogen_experiments_reported,
            "sensor_count": 50 if report_checks["fifty_sensor_matrix_reported"] else None,
            "release_rates_normal_dm3_h": [50, 100, 300, 1000],
            "configuration_count": 8,
            "container_internal_dimensions_m": [6.0, 2.5, 2.5],
            "container_working_volume_m3": 36.0,
            "qualitative_roles": [
                "actual-hydrogen concentration stratification context",
                "detector-height and multi-location coverage rationale",
                "ventilation and compartment-opening sensitivity context",
            ],
            "not_used_for": [
                "detector amplitude or alarm-threshold calibration",
                "outdoor HRS detector-placement validation",
                "consequence distance, ignition, ESD or full-loop validation",
            ],
        },
        "next_acquisition_requirement": (
            "Obtain a rights-cleared companion export containing experiment ID, sensor ID, "
            "source XYZ, sensor XYZ, release orientation and per-sensor numerical H2 response, "
            "or freeze the same candidate against another untouched actual-hydrogen cohort."
        ),
        "claim_boundary": (
            "HyDelta D6A.1 is retained as public actual-hydrogen report-level evidence for "
            "indoor concentration stratification, sensor coverage and ventilation context. "
            "It does not independently validate the frozen spatial ranker because the report "
            "does not publish the machine-readable spatial outcome fields required by the "
            "pre-access protocol."
        ),
    }


def _markdown(result: dict[str, Any]) -> str:
    decision = result["decision"]
    lines = [
        "# HyDelta D6A.1 indoor spatial holdout eligibility",
        "",
        f"Decision: **{result['status']}**.",
        "",
        "The report is a strong public actual-hydrogen source, but it cannot be scored as the "
        "frozen independent spatial holdout. It reports 50 sensors across 32 hydrogen "
        "configuration/flow combinations; however, the exact source and sensor coordinates, "
        "release orientation and per-sensor numeric responses required before access are not "
        "published as tables or companion data.",
        "",
        "| Frozen requirement | Result |",
        "|---|---|",
    ]
    for name, item in result["eligibility"].items():
        lines.append(f"| `{name}` | {'PASS' if item['passed'] else 'FAIL'} — {item['observed']} |")
    lines.extend([
        "",
        "No graph or colour-table digitisation was used. The locked formula was not changed, "
        "the model evaluation was not run, and the candidate remains disabled at runtime.",
        "",
        "## Evidence retained",
        "",
        "The report remains useful as actual-hydrogen evidence for concentration "
        "stratification, multi-height detector coverage, compartment connectivity and "
        "ventilation effects. These are report-level physical-context claims only.",
        "",
        "## Next data requirement",
        "",
        result["next_acquisition_requirement"],
        "",
        f"Source: [HyDelta D6A.1, DOI {DOI}](https://doi.org/{DOI}).",
        "",
        "## Claim boundary",
        "",
        result["claim_boundary"],
        "",
    ])
    assert decision["eligible_for_primary_spatial_holdout"] is False
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdf",
        type=Path,
        default=ROOT / "data/public_validation/raw/hydelta_2026" / EXPECTED_FILE,
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "research/hydelta_indoor_spatial_holdout_protocol_2026_10_08.json",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=ROOT / "research/hydelta_indoor_spatial_holdout_eligibility_2026_10_08.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=ROOT / "research/HYDELTA_INDOOR_SPATIAL_HOLDOUT_ELIGIBILITY_2026_10_08.md",
    )
    args = parser.parse_args()
    result = audit(args.pdf, args.protocol)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    args.markdown_output.write_text(
        _markdown(result), encoding="utf-8", newline="\n"
    )
    print(json.dumps({
        "status": result["status"],
        "failed_required_fields": result["decision"]["failed_required_fields"],
        "json_output": str(args.json_output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
