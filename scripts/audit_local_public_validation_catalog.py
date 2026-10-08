"""Build a privacy-bounded catalog of the locally cached public corpus.

This is a discovery artifact, not a semantic validation step.  It counts files
and bytes under ``data/public_validation/raw`` and records conservative family
labels derived from the cache key.  It deliberately omits paths, filenames,
headers, rows, timestamps and channel values so the catalog can be committed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FAMILY_HINTS: dict[str, str] = {
    "h2protocol": "refueling_protocol_or_controller_cases",
    "h2protocol_j2601_tables": "refueling_protocol_or_controller_cases",
    "h2protocol_mc_default": "refueling_protocol_or_controller_cases",
    "met_hytrucks_hysam": "tank_and_refueling_measurements",
    "methytrucks_hysam": "tank_and_refueling_measurements",
    "methytrucks_group_a": "tank_and_refueling_measurements",
    "methytrucks_group_c": "tank_and_refueling_measurements",
    "methytrucks_group_d": "tank_and_refueling_measurements",
    "nrel_h2iq_2022": "tank_and_refueling_measurements",
    "uci_early_hrs": "tank_and_refueling_measurements",
    "nbsdc_liquid_hrs_2025": "station_or_hose_reference",
    "elvhys_4_2": "hydrogen_release_or_detection_experiment",
    "elvhys_detector_holdout": "hydrogen_release_or_detection_experiment",
    "elvhys_detector_holdout_v2": "hydrogen_release_or_detection_experiment",
    "hydrogen_dispersion_channel": "dispersion_or_detector_component",
    "h2safe_2026": "dispersion_or_detector_component",
    "hiad_2_2": "accident_or_ignition_component",
    "kit_lh2_consequence_1483": "dispersion_or_detector_component",
    "zenodo_17913628_accidental_self_ignition": "accident_or_ignition_component",
    "preslhy": "hydrogen_release_or_fire_experiment",
    "preslhy_e5_1": "hydrogen_release_or_fire_experiment",
    "preslhy_partb_xlsx": "hydrogen_release_or_fire_experiment",
    "proust_90mpa": "tank_and_refueling_measurements",
    "hydelta_2026": "tank_and_refueling_measurements",
    "hydelta_20817291": "tank_and_refueling_measurements",
    "figshare_26117989": "tank_and_refueling_measurements",
    "jankuj_2026": "tank_and_refueling_measurements",
}


def _catalog(root: Path) -> dict[str, Any]:
    collections: list[dict[str, Any]] = []
    total_files = 0
    total_bytes = 0
    for directory in sorted((item for item in root.iterdir() if item.is_dir()), key=lambda p: p.name):
        files = [item for item in directory.rglob("*") if item.is_file()]
        size = sum(item.stat().st_size for item in files)
        key = directory.name
        total_files += len(files)
        total_bytes += size
        collections.append(
            {
                "id": key,
                "family_hint": FAMILY_HINTS.get(key, "other_public_validation_material"),
                "file_count": len(files),
                "size_mb_decimal": round(size / 1_000_000, 3),
                "semantic_attestation": "not_performed_by_catalog",
                "full_loop_holdout_eligible": False,
                "decision": "CATALOG_ONLY_REQUIRES_DATASET_SPECIFIC_VALIDATION",
            }
        )
    return {
        "schema_version": 1,
        "artifact_type": "local_public_validation_catalog",
        "status": "privacy_bounded_catalog_only",
        "generated_at": "2026-10-09",
        "privacy": {
            "source_paths_published": False,
            "source_filenames_published": False,
            "source_headers_published": False,
            "raw_rows_persisted": False,
            "channel_values_persisted": False,
            "absolute_timestamps_published": False,
            "site_company_manufacturer_published": False,
        },
        "scope": {
            "cache_root": "local public-validation raw corpus",
            "collection_count": len(collections),
            "file_count": total_files,
            "size_gb_decimal": round(total_bytes / 1_000_000_000, 3),
            "classification_basis": "cache directory key only; family hints are not semantic attestation",
        },
        "collections": collections,
        "coverage_assessment": {
            "public_component_evidence_is_substantial": True,
            "new_full_loop_cohort_identified_by_catalog": False,
            "full_loop_holdout_eligible": False,
            "next_action": "Run dataset-specific provenance, units, time-base and boundary checks before any model fit or holdout.",
        },
        "claim_boundary": (
            "This catalog proves only local availability of cached public files. "
            "It does not validate channel meaning, units, synchronization, reuse rights, "
            "vehicle-side coverage or safety limits."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/public_validation/raw"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = _catalog(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
