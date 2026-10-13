"""Audit the public HyDelta natural-ventilation hydrogen experiments.

The report contains controlled hydrogen releases into three pressure-reducing
station cabinet geometries.  The evidence is used to ground operator guidance
that ventilation is a mitigation layer whose performance must be confirmed by
gas measurements.  It is not used to calibrate the station dispersion proxy,
set alarm thresholds, or establish site separation distances.
"""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re

from pypdf import PdfReader


EXPECTED_BYTES = 8_542_387
EXPECTED_MD5 = "7941752237175c0c0e012b06879d00aa"
EXPECTED_SHA256 = "0b0dbe668c17de4f819da30dca9b02b5695cb9ffe34dea20736dc26cda80200e"
DOI = "10.5281/zenodo.8164602"


def _digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _contains(normalized: str, *fragments: str) -> bool:
    return all(fragment in normalized for fragment in fragments)


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
        "actual_hydrogen_reference_leaks_reported": _contains(
            normalized, "125 l/h for hydrogen", "5.6 m3n /h hydrogen"
        ),
        "half_cubic_metre_low_flow_result_reported": _contains(
            normalized, "concentration rises to 2.7 vol%", "3.2 vol% as a local"
        ),
        "four_cubic_metre_hydrogen_combustible_case_reported": _contains(
            normalized,
            "measurement results 4 m3 cabinet station",
            "hydrogen, a combustible mixture was measured",
        ),
        "mini_cabinet_hydrogen_combustible_case_reported": _contains(
            normalized,
            "measurement results mini-cabinet",
            "while it was measured with hydrogen (125l/h)",
        ),
        "hydrogen_blanket_stratification_reported": _contains(
            normalized,
            'there is a "blanket" effect',
            "concentrations are higher at the top than at the bottom",
        ),
        "cross_ventilation_does_not_guarantee_safe_concentration": _contains(
            normalized,
            "top ventilation (up to 4%) + bottom ventilation (2%)",
            "flammable mixtures are still possible",
        ),
        "ventilation_rate_alone_is_not_comprehensive": _contains(
            normalized,
            "at a ventilation rate of more than 5",
            "is thus not a comprehensive means of ensuring adequate ventilation",
        ),
        "measure_before_opening_recommended": _contains(
            normalized,
            "take a gas concentration measurement in the vent opening before opening the cabinet",
        ),
    }
    measured_cases = [
        {
            "cabinet": "0.5 m3",
            "hydrogen_flow_nm3_h": 0.125,
            "nominal_pressure_barg": 1.0,
            "nominal_opening_mm2": 0.025,
            "maximum_inside_volpct_h2": 2.9,
            "maximum_vent_opening_volpct_h2": 3.2,
            "flammable_mixture_observed": False,
        },
        {
            "cabinet": "0.5 m3",
            "hydrogen_flow_nm3_h": 0.558,
            "nominal_pressure_barg": 8.0,
            "nominal_opening_mm2": 0.025,
            "maximum_inside_volpct_h2": 6.9,
            "maximum_vent_opening_volpct_h2": 6.4,
            "flammable_mixture_observed": True,
        },
        {
            "cabinet": "0.5 m3",
            "hydrogen_flow_nm3_h": 1.25,
            "nominal_pressure_barg": 1.0,
            "nominal_opening_mm2": 0.25,
            "maximum_inside_volpct_h2": 11.0,
            "maximum_vent_opening_volpct_h2": 11.0,
            "flammable_mixture_observed": True,
        },
        {
            "cabinet": "0.5 m3",
            "hydrogen_flow_nm3_h": 5.8,
            "nominal_pressure_barg": 8.0,
            "nominal_opening_mm2": 0.25,
            "maximum_inside_volpct_h2": 24.0,
            "maximum_vent_opening_volpct_h2": 21.0,
            "flammable_mixture_observed": True,
        },
        {
            "cabinet": "4 m3",
            "hydrogen_flow_nm3_h": 0.125,
            "nominal_pressure_barg": 1.0,
            "nominal_opening_mm2": 0.025,
            "maximum_inside_volpct_h2": 1.0,
            "maximum_vent_opening_volpct_h2": 0.4,
            "flammable_mixture_observed": False,
        },
        {
            "cabinet": "4 m3",
            "hydrogen_flow_nm3_h": 0.558,
            "nominal_pressure_barg": 8.0,
            "nominal_opening_mm2": 0.025,
            "maximum_inside_volpct_h2": 2.2,
            "maximum_vent_opening_volpct_h2": 1.3,
            "flammable_mixture_observed": False,
        },
        {
            "cabinet": "4 m3",
            "hydrogen_flow_nm3_h": 1.25,
            "nominal_pressure_barg": 1.0,
            "nominal_opening_mm2": 0.25,
            "maximum_inside_volpct_h2": 5.5,
            "maximum_vent_opening_volpct_h2": 4.1,
            "flammable_mixture_observed": True,
        },
        {
            "cabinet": "4 m3",
            "hydrogen_flow_nm3_h": 5.8,
            "nominal_pressure_barg": 8.0,
            "nominal_opening_mm2": 0.25,
            "maximum_inside_volpct_h2": 12.0,
            "maximum_vent_opening_volpct_h2": 9.3,
            "flammable_mixture_observed": True,
        },
        {
            "cabinet": "mini (<0.5 m3)",
            "hydrogen_flow_nm3_h": 0.125,
            "nominal_pressure_barg": 1.0,
            "nominal_opening_mm2": 0.025,
            "maximum_inside_volpct_h2": 5.6,
            "maximum_vent_opening_volpct_h2": 4.1,
            "flammable_mixture_observed": True,
            "indicative_only": True,
        },
        {
            "cabinet": "mini (<0.5 m3)",
            "hydrogen_flow_nm3_h": 0.558,
            "nominal_pressure_barg": 8.0,
            "nominal_opening_mm2": 0.025,
            "maximum_inside_volpct_h2": 12.0,
            "maximum_vent_opening_volpct_h2": 12.0,
            "flammable_mixture_observed": True,
            "indicative_only": True,
            "experiment_stopped_early_for_safety": True,
        },
    ]
    status = (
        "verified_report_level_natural_ventilation_evidence"
        if identity_match and all(checks.values())
        else "source_or_claim_check_failed"
    )
    return {
        "schema_version": 1,
        "recorded_at": date.today().isoformat(),
        "status": status,
        "source": {
            "title": (
                "D6B.1A & D6B.1B Inventory, modeling and experiments related "
                "to ventilation in pressure reducing stations"
            ),
            "publisher": "HyDelta / Kiwa",
            "doi": DOI,
            "record_url": f"https://doi.org/{DOI}",
            "publication_date": "2023-07-19",
            "license": "CC BY 4.0",
            "language": "English",
            "file": pdf.name,
            "publisher_file_identity": {
                "expected_bytes": EXPECTED_BYTES,
                "expected_md5": EXPECTED_MD5,
                "expected_sha256": EXPECTED_SHA256,
                "observed": identity,
                "identity_match": identity_match,
            },
            "page_count": len(reader.pages),
            "raw_pdf_committed": False,
        },
        "experiment_scope": {
            "actual_hydrogen": True,
            "cabinet_families": ["0.5 m3", "4 m3", "mini (<0.5 m3)"],
            "hydrogen_flow_nm3_h": [0.125, 0.558, 1.25, 5.8],
            "nominal_pressure_barg": [1.0, 8.0],
            "nominal_opening_mm2": [0.025, 0.25],
            "hydrogen_lfl_volpct_used_by_source": 4.0,
            "measured_case_count": len(measured_cases),
        },
        "measured_case_summary": measured_cases,
        "reported_findings": {
            "hydrogen_accumulates_as_upper_blanket": True,
            "ventilation_mitigates_but_does_not_guarantee_below_lfl": True,
            "gas_measurement_before_opening_recommended": True,
            "ventilation_rate_above_five_per_hour_not_sufficient_by_itself": True,
            "additional_top_and_bottom_ventilation_can_still_leave_flammable_mixtures": True,
            "maximum_reported_inside_concentration_volpct_h2": 24.0,
            "smallest_reported_flow_with_flammable_mini_cabinet_nm3_h": 0.125,
        },
        "claim_checks": checks,
        "runtime_use": {
            "emergency_response_grounding": True,
            "ventilation_as_single_safe_state_proof_authorized": False,
            "measured_gas_clearance_required": True,
            "dispersion_proxy_calibration": False,
            "alarm_setpoint_calibration": False,
            "station_release_model_validation": False,
            "site_safety_distance_validation": False,
            "raw_machine_readable_time_series_available": False,
        },
        "claim_boundary": (
            "The CC BY 4.0 report provides actual-hydrogen, cabinet-scale measured "
            "concentration evidence for ventilation and response wording. The values "
            "are report tables rather than machine-readable time series, the mini-cabinet "
            "tests are explicitly indicative, and the geometries are low-pressure gas "
            "distribution cabinets. They do not validate the H70 station dispersion "
            "proxy, detector placement, alarm thresholds, ESD effectiveness, release "
            "rate, or site separation distance."
        ),
    }


def _markdown(result: dict[str, object]) -> str:
    findings = result["reported_findings"]
    scope = result["experiment_scope"]
    return "\n".join(
        [
            "# HyDelta natural-ventilation evidence audit",
            "",
            f"- Status: **{result['status']}**",
            f"- DOI: <https://doi.org/{DOI}>",
            "- License: `CC BY 4.0`",
            f"- Actual-hydrogen cabinet cases transcribed: `{scope['measured_case_count']}`",
            "- Runtime calibration: **false**",
            "",
            "## Decision-support finding",
            "",
            "The controlled cabinet experiments show that natural or enlarged ventilation "
            "can reduce hydrogen accumulation, but it does not by itself prove that a "
            "cabinet is below the 4 vol% hydrogen LFL. Hydrogen accumulated preferentially "
            "near the top, and some enlarged top-plus-bottom ventilation configurations "
            "still permitted flammable mixtures. Operator guidance must therefore require "
            "a gas measurement before opening or declaring the area safe.",
            "",
            "## Bounded facts exposed to SAGA",
            "",
            f"- Upper hydrogen blanket reported: `{findings['hydrogen_accumulates_as_upper_blanket']}`",
            f"- Ventilation alone proves safe state: `false`",
            f"- Maximum tabulated inside concentration: `{findings['maximum_reported_inside_concentration_volpct_h2']} vol% H2`",
            f"- Smallest indicative mini-cabinet flow with a flammable reading: `{findings['smallest_reported_flow_with_flammable_mini_cabinet_nm3_h']} Nm3/h H2`",
            "",
            "## Claim boundary",
            "",
            f"> {result['claim_boundary']}",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("data/public_validation/raw/hydelta_8164602/")
        / "D6B_1_2_HyDelta_Tweede_Tranche_Ventilation_in_Gas_Stations_EN.pdf",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/hydelta_natural_ventilation_evidence_2026_10_13.json"),
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("research/HYDELTA_NATURAL_VENTILATION_EVIDENCE_2026_10_13.md"),
    )
    args = parser.parse_args()
    result = audit(args.pdf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    args.markdown.write_text(_markdown(result), encoding="utf-8", newline="\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "verified_report_level_natural_ventilation_evidence" else 1


if __name__ == "__main__":
    raise SystemExit(main())
