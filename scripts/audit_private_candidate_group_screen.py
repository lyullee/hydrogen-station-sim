"""Aggregate a privacy-bounded screen of private candidate manifests.

The manifest is kept outside the repository and may contain source paths,
file names, and opaque candidate identifiers.  This command reads those
fields only to locate each candidate's parent directory, then emits aggregate
coverage counts.  The output intentionally contains no paths, names,
identifiers, timestamps, headers, or measurements.

This is a discovery/intake receipt.  Header semantics cannot prove that
station and vehicle channels are co-timed, calibrated, licensed, or suitable
for a frozen external holdout.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _outside_repo(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError("private candidate input must be outside the repository worktree")


def _load_manifest(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("candidate manifest must be a JSON list")
    rows = [row for row in payload if isinstance(row, dict) and row.get("path")]
    if not rows:
        raise ValueError("candidate manifest has no path-bearing records")
    return rows


def screen(manifest_path: Path) -> dict[str, Any]:
    """Return aggregate candidate coverage without persisting private identity."""

    manifest_path = _outside_repo(manifest_path)
    rows = _load_manifest(manifest_path)
    # Import lazily so importing this module remains safe in environments that
    # only want to inspect the schema receipt.
    sys.path.insert(0, str(ROOT / "scripts"))
    from audit_private_full_loop_schema import audit  # noqa: PLC0415

    parent_by_group: dict[str, set[Path]] = {}
    for row in rows:
        group = str(row.get("group_id") or "unassigned")
        try:
            parent = _outside_repo(Path(str(row["path"])).parent)
        except ValueError:
            # Candidate manifests may include repository-derived diagnostics as
            # a duplicate comparison group.  They are not private intake and
            # must not be re-scanned as part of this receipt.
            continue
        parent_by_group.setdefault(group, set()).add(parent)

    receipts: list[dict[str, Any]] = []
    for parents in parent_by_group.values():
        for parent in sorted(parents, key=str):
            if not parent.is_dir():
                receipts.append({"available": False})
                continue
            try:
                result = audit(parent, source_label="authorized-private-candidate")
            except (OSError, ValueError, UnicodeError):
                receipts.append({"available": False})
                continue
            aggregate = result.get("aggregate") or {}
            receipts.append({"available": True, "aggregate": aggregate})

    available = [item["aggregate"] for item in receipts if item.get("available")]
    semantic_union = sorted({
        group
        for item in available
        for group in item.get("observed_semantic_groups") or []
    })
    contract_union = sorted({
        group
        for item in available
        for group in item.get("observed_full_loop_contract_groups") or []
    })
    required = {
        "cascade_or_storage",
        "common_time",
        "controller_state",
        "delivered_temperature",
        "mass_flow",
        "station_pressure",
        "vehicle_identity",
        "vehicle_pressure",
        "vehicle_temperature",
    }
    return {
        "schema_version": 1,
        "artifact_type": "privacy_bounded_private_candidate_group_screen",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "privacy_boundary": {
            "source_paths_persisted": False,
            "source_filenames_persisted": False,
            "source_identifiers_persisted": False,
            "original_headers_persisted": False,
            "raw_rows_persisted": False,
            "absolute_timestamps_persisted": False,
            "measurement_values_persisted": False,
        },
        "manifest_scope": {
            "candidate_records_screened": len(rows),
            "candidate_group_count": len(parent_by_group),
            "candidate_root_count": sum(len(value) for value in parent_by_group.values()),
            "available_candidate_root_count": len(available),
        },
        "aggregate": {
            "csv_files_seen": sum(int(item.get("csv_files_seen") or 0) for item in available),
            "readable_csv_files": sum(int(item.get("readable_csv_files") or 0) for item in available),
            "monotonic_numeric_time_files": sum(
                int(item.get("monotonic_numeric_time_files") or 0) for item in available
            ),
            "duplicate_numeric_time_files": sum(
                int(item.get("duplicate_numeric_time_files") or 0) for item in available
            ),
            "observed_semantic_groups": semantic_union,
            "observed_full_loop_contract_groups": contract_union,
            "missing_contract_groups": sorted(required - set(contract_union)),
            "roots_with_all_required_contract_groups": sum(
                int(set(item.get("observed_full_loop_contract_groups") or []) >= required)
                for item in available
            ),
            "roots_with_vehicle_semantic_group": sum(
                int("vehicle" in (item.get("observed_semantic_groups") or []))
                for item in available
            ),
        },
        "admission": {
            "full_loop_external_holdout_eligible": False,
            "runtime_parameter_application": False,
            "validation_gate_effect": "none",
            "reason": (
                "Private candidate discovery shows complementary channel labels, but does not "
                "attest station/vehicle linkage, common clock, units, calibration, rights, or "
                "a model-and-split freeze before outcome access."
            ),
            "next_actions": [
                "attest every required station/dispenser/vehicle channel role",
                "attest common-clock event linkage and units/calibration",
                "freeze the model and split before numerical outcome access",
                "obtain independent reviewer access under declared rights",
            ],
        },
        "claim_boundary": (
            "This is a privacy-bounded candidate inventory screen only. It does not validate "
            "the model, establish a station-to-vehicle full-loop holdout, or support safety or "
            "regulatory claims."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = screen(args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload["aggregate"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
