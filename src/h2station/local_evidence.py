"""Privacy-bounded local evidence coverage for the runtime API.

The local archive is owner-controlled and is intentionally not read by the
runtime.  Only the committed aggregate audit artifacts are loaded here.  The
result is suitable for an operator or UI to understand which claims the
current run can support without exposing raw rows, source paths, identifiers,
or equipment metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_ROOT = Path(__file__).resolve().parents[2]
_DISCOVERY = _ROOT / "research/local_hydrogen_station_data_discovery_recheck_2026_10_09.json"
_DEEP_SCAN = _ROOT / "research/local_data_deep_scan_2026_10_09.json"
_CONTINUITY = _ROOT / "research/local_wide_equipment_continuity_recheck_2026_10_09.json"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("aggregate evidence artifact must contain an object")
    return value


def _privacy_boundary() -> dict[str, bool]:
    return {
        "raw_rows_persisted": False,
        "source_paths_published": False,
        "source_filenames_published": False,
        "source_headers_published": False,
        "source_identifiers_published": False,
        "site_company_manufacturer_published": False,
        "calendar_dates_published": False,
    }


def local_station_evidence_summary() -> dict[str, Any]:
    """Return a stable, privacy-bounded view of local evidence coverage.

    Missing or malformed audit artifacts fail closed.  A runtime outage or an
    incomplete checkout must never be interpreted as evidence that a
    station-to-vehicle validation cohort exists.
    """

    try:
        discovery = _read_json(_DISCOVERY)
        deep_scan = _read_json(_DEEP_SCAN)
        continuity = _read_json(_CONTINUITY)

        coverage = discovery["coverage_assessment"]
        measured = deep_scan["measured_station_bundle"]
        deep_decision = deep_scan["full_loop_decision"]
        inventory = continuity["inventory"]
        eligibility = continuity["eligibility"]
        header = discovery["independent_header_recheck"]

        return {
            "status": "available",
            "evidence_role": "privacy_bounded_local_station_coverage",
            "privacy": _privacy_boundary(),
            "measured_station": {
                "csv_file_count": int(measured["csv_files"]),
                "deduplicated_row_count": int(measured["deduplicated_rows"]),
                "raw_storage_gib_rounded": float(measured["raw_storage_gib_rounded"]),
                "eligible_use": list(measured.get("eligible_use") or []),
            },
            "wide_equipment_continuity": {
                "file_count": int(inventory["wide_file_count"]),
                "row_count": int(inventory["wide_row_count"]),
                "median_sample_period_s": float(inventory["median_positive_interval_s"]),
                "maximum_sample_gap_s": float(inventory["maximum_positive_interval_s"]),
                "timestamp_parse_failures": int(inventory["timestamp_parse_failures"]),
                "negative_interval_count": int(inventory["negative_interval_count"]),
                "state_transition_count": int(inventory["state_transition_count"]),
                "station_equipment_continuity_screen_ready": bool(
                    eligibility["station_equipment_continuity_screen_ready"]
                ),
            },
            "coverage": {
                "local_station_data_is_sparse": bool(
                    coverage["local_station_data_is_sparse"]
                ),
                "station_side_dynamic_evidence_is_substantial": bool(
                    coverage["station_side_dynamic_evidence_is_substantial"]
                ),
                "vehicle_side_full_loop_validation_ready": bool(
                    coverage["vehicle_side_full_loop_validation_ready"]
                ),
                "quantitative_consequence_validation_ready": bool(
                    coverage["quantitative_consequence_validation_ready"]
                ),
                "full_loop_decision": str(deep_decision["decision"]),
                "header_vehicle_or_dispenser_candidates": int(
                    header["candidate_file_counts"]["vehicle_or_dispenser_expanded"]
                ),
            },
            "claim_boundary": (
                "Local evidence supports station-side pressure-cycle, cascade, "
                "recharge and equipment-state screening. It does not support a "
                "synchronized station-to-vehicle full-loop or site-specific "
                "consequence claim until the custodian attests the missing channels."
            ),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return {
            "status": "unavailable",
            "evidence_role": "privacy_bounded_local_station_coverage",
            "privacy": _privacy_boundary(),
            "coverage": {
                "local_station_data_is_sparse": None,
                "station_side_dynamic_evidence_is_substantial": None,
                "vehicle_side_full_loop_validation_ready": False,
                "quantitative_consequence_validation_ready": False,
                "full_loop_decision": "UNAVAILABLE",
            },
            "claim_boundary": (
                "Aggregate local evidence artifacts are unavailable or invalid; "
                "no validation claim is permitted."
            ),
        }

