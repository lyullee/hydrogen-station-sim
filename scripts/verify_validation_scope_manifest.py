"""Verify the privacy-bounded validation-scope manifest.

This verifier deliberately checks metadata and referenced-artifact hashes only.
It never opens or exports the confidential station CSV files.  The owner data
are therefore auditable as a chronology-preserving same-site holdout without
turning the repository into a copy of the private dataset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = "research/confidential_validation_split_manifest_2026_10_11.json"
DEFAULT_OUTPUT = "research/validation_scope_manifest_verification_2026_10_11.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_manifest(root: Path, manifest_path: Path) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}
    failures: list[str] = []

    def check(name: str, passed: bool, observed: Any = None, expected: Any = None) -> None:
        record: dict[str, Any] = {"pass": bool(passed)}
        if observed is not None:
            record["observed"] = observed
        if expected is not None:
            record["expected"] = expected
        checks[name] = record
        if not passed:
            failures.append(name)

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "schema_version": 1,
            "artifact_type": "validation_scope_manifest_verification",
            "status": "FAIL",
            "manifest": str(manifest_path.relative_to(root)).replace("\\", "/"),
            "failures": [f"manifest_read:{type(exc).__name__}"],
            "checks": {},
        }

    check(
        "manifest_identity",
        manifest.get("artifact_type") == "confidential_validation_split_manifest"
        and manifest.get("status") == "frozen_scope_manifest",
        {"artifact_type": manifest.get("artifact_type"), "status": manifest.get("status")},
        {"artifact_type": "confidential_validation_split_manifest", "status": "frozen_scope_manifest"},
    )

    privacy = manifest.get("privacy") or {}
    privacy_keys = (
        "source_identifiers_published",
        "source_paths_published",
        "source_filenames_published",
        "source_headers_published",
        "raw_rows_persisted",
        "absolute_timestamps_published",
        "calendar_dates_published",
        "site_company_location_manufacturer_published",
    )
    check(
        "privacy_boundary",
        all(privacy.get(key) is False for key in privacy_keys),
        {key: privacy.get(key) for key in privacy_keys},
        "all false",
    )

    owner = manifest.get("owner_station_side_split") or {}
    cohorts = {item.get("id"): item for item in owner.get("cohorts") or []}
    check(
        "owner_partition_rule",
        owner.get("partition_rule") == "episode/time order; calibration prefix and later untouched suffix; no random row mixing"
        and owner.get("fit_uses_holdout") is False
        and owner.get("default_model_parameters_changed_after_holdout") is False
        and owner.get("claim_label") == "same_site_temporal_holdout",
        {
            "partition_rule": owner.get("partition_rule"),
            "fit_uses_holdout": owner.get("fit_uses_holdout"),
            "default_model_parameters_changed_after_holdout": owner.get(
                "default_model_parameters_changed_after_holdout"
            ),
            "claim_label": owner.get("claim_label"),
        },
        "chronology-preserving same-site holdout",
    )
    check(
        "owner_counts",
        owner.get("source_scope") == "33 owner-controlled station CSV files; de-identified and retained locally"
        and owner.get("deduplicated_rows") == 56854143
        and cohorts.get("pressure_boundary", {}).get("calibration_points") == 998
        and cohorts.get("pressure_boundary", {}).get("holdout_points") == 30
        and cohorts.get("cascade_sequence", {}).get("calibration_pairs") == 8106
        and cohorts.get("cascade_sequence", {}).get("holdout_pairs") == 3664
        and cohorts.get("recharge_pressure_forecast", {}).get("calibration_cases") == 1024
        and cohorts.get("recharge_pressure_forecast", {}).get("holdout_cases") == 394,
        {
            "deduplicated_rows": owner.get("deduplicated_rows"),
            "pressure": cohorts.get("pressure_boundary"),
            "cascade": cohorts.get("cascade_sequence"),
            "recharge": cohorts.get("recharge_pressure_forecast"),
        },
        "frozen owner split counts",
    )

    public = manifest.get("public_component_split") or {}
    check(
        "public_component_split",
        public.get("partition_rule") == "lab_test_number modulo 3 equals 0 reserved before outcome inspection"
        and public.get("calibration_cases") == 23
        and public.get("holdout_cases") == 12
        and public.get("excluded_mass_closure_cases") == 1
        and public.get("claim_label") == "independent_component_holdout",
        public,
        "23 calibration, 12 holdout, 1 excluded; independent component only",
    )

    full_loop = manifest.get("station_to_vehicle_full_loop") or {}
    check(
        "full_loop_scope_exclusion",
        full_loop.get("status") == "not_available_in_rights_cleared_machine_readable_form"
        and full_loop.get("decision") == "excluded_from_current_goal_and_reported_as_limitation"
        and full_loop.get("independent_external_validation_supported") is False,
        {
            "status": full_loop.get("status"),
            "decision": full_loop.get("decision"),
            "independent_external_validation_supported": full_loop.get(
                "independent_external_validation_supported"
            ),
        },
        "excluded and reported as a limitation",
    )

    referenced = ((manifest.get("integrity") or {}).get("referenced_artifacts_sha256") or {})
    hash_results: dict[str, Any] = {}
    for relative, expected in referenced.items():
        path = root / relative
        if not path.is_file():
            hash_results[relative] = {"pass": False, "reason": "missing"}
            failures.append(f"hash:{relative}")
            continue
        actual = _sha256(path)
        passed = actual == expected
        hash_results[relative] = {"pass": passed, "expected": expected, "actual": actual}
        if not passed:
            failures.append(f"hash:{relative}")
    checks["referenced_artifact_hashes"] = {
        "pass": not any(not item["pass"] for item in hash_results.values()),
        "observed": hash_results,
        "expected": "all referenced SHA-256 digests match",
    }

    return {
        "schema_version": 1,
        "artifact_type": "validation_scope_manifest_verification",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not failures else "FAIL",
        "manifest": str(manifest_path.relative_to(root)).replace("\\", "/"),
        "checks": checks,
        "failures": failures,
        "claim_boundary": (
            "This verifier checks metadata and referenced-artifact integrity only. "
            "It does not publish private rows, convert a same-site holdout into "
            "external validation, or establish station-to-vehicle full-loop accuracy."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=Path(DEFAULT_MANIFEST))
    parser.add_argument("--output", type=Path, default=Path(DEFAULT_OUTPUT))
    args = parser.parse_args()

    root = args.root.resolve()
    manifest_path = args.manifest if args.manifest.is_absolute() else root / args.manifest
    output_path = args.output if args.output.is_absolute() else root / args.output
    result = verify_manifest(root, manifest_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "failures": result["failures"]}, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
