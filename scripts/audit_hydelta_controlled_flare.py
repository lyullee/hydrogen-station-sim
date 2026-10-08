"""Audit the public HyDelta controlled-hydrogen-flare report.

The report is used only to ground emergency-response wording for a deliberately
engineered flare.  It is not converted into raw test data, a generic vent-to-
flare instruction, or validation of the station release/consequence models.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re

from pypdf import PdfReader


EXPECTED_BYTES = 1_535_209
EXPECTED_MD5 = "71bbe9dfd128a6a3be27e62d9a23423c"
EXPECTED_SHA256 = "a36fc96f10a6d9b9fe009d0b152a64508caae1f1c48c5cc6212f5a53df00d5c0"
DOI = "10.5281/zenodo.20817291"


def _digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(pdf: Path) -> dict[str, object]:
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    reader = PdfReader(pdf)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    normalized = re.sub(r"\s+", " ", text).lower()
    identity = {
        "bytes": pdf.stat().st_size,
        "md5": _digest(pdf, "md5"),
        "sha256": _digest(pdf, "sha256"),
    }
    identity_match = (
        identity["bytes"] == EXPECTED_BYTES
        and identity["md5"] == EXPECTED_MD5
        and identity["sha256"] == EXPECTED_SHA256
    )
    checks = {
        "controlled_flare_efficiency_above_99_percent_reported": (
            "efficiency of more than 99%" in normalized
        ),
        "nox_reduction_about_factor_ten_reported": (
            "reduced by about a factor of 10" in normalized
        ),
        "nitrogen_34_volpct_operating_boundary_reported": (
            "remains in operation, is 34 vol%" in normalized
        ),
        "flame_protection_shutdown_reported": (
            "shuts off the gas supply based on the flame protection" in normalized
        ),
        "gas_prepressure_low_high_trip_reported": (
            "switch off if the gas line pressure is too low or too high" in normalized
        ),
        "gas_valve_leak_check_reported": (
            "check for leakage through the gas valve" in normalized
        ),
    }
    return {
        "schema_version": 1,
        "recorded_at": date.today().isoformat(),
        "status": (
            "verified_report_level_controlled_flare_evidence"
            if identity_match and all(checks.values())
            else "source_or_claim_check_failed"
        ),
        "source": {
            "title": "D5e.1 Experimental results of the controlled hydrogen flaring installation",
            "publisher": "HyDelta 4 / Kiwa",
            "doi": DOI,
            "record_url": f"https://doi.org/{DOI}",
            "publication_date": "2026-06-23",
            "license": "CC BY 4.0",
            "language": "English",
            "file": pdf.name,
            "publisher_file_identity": {
                "expected_bytes": EXPECTED_BYTES,
                "expected_md5": EXPECTED_MD5,
                "observed": identity,
                "identity_match": identity_match,
            },
            "page_count": len(reader.pages),
            "raw_pdf_committed": False,
        },
        "reported_findings": {
            "controlled_flare_combustion_efficiency_lower_bound_percent": 99.0,
            "nox_reduction_factor_approximate": 10.0,
            "maximum_reported_nitrogen_fraction_for_continued_operation_volpct": 34.0,
            "above_reported_nitrogen_boundary": (
                "tested burner's flame-protection system shuts off gas supply; "
                "this is equipment-specific and not a universal station trip setpoint"
            ),
            "tested_safeguards": [
                "inhibit start when gas pre-pressure is too low",
                "check leakage through the paired gas valves",
                "trip on gas-line pressure that is too low or too high",
                "electronically regulate burner gas and combustion-air flow",
            ],
        },
        "claim_checks": checks,
        "runtime_use": {
            "emergency_response_grounding": True,
            "applies_only_to_engineered_approved_controlled_flare": True,
            "ad_hoc_ignition_of_vent_stream_authorized": False,
            "station_release_model_validation": False,
            "site_safety_distance_validation": False,
            "numerical_raw_trace_available": False,
        },
        "claim_boundary": (
            "A CC BY 4.0 report-level experiment supports planning and verification "
            "language for an engineered controlled flare. The reported 34 vol% nitrogen "
            "boundary, >99% conversion and approximate tenfold NOx reduction belong to "
            "the tested burner and must not be reused as universal HRS setpoints, raw "
            "time-series validation, vent ignition instructions or site safety distances."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("data/public_validation/raw/hydelta_20817291/")
        / "D5_E1_HyDelta_Vierde_Tranche_Experimental_Results_Of_The_Controlled_Hydrogen_Flaring_Installation_EN.pdf",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/hydelta_controlled_flare_evidence_2026_10_08.json"),
    )
    args = parser.parse_args()
    result = audit(args.pdf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "verified_report_level_controlled_flare_evidence" else 1


if __name__ == "__main__":
    raise SystemExit(main())
