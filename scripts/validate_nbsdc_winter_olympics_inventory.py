"""Validate the NBSDC Winter Olympics package inventory without opening cells.

The checker operates only on the generic byte-level intake manifest and a
custodian-supplied file-role declaration. It verifies that the expected NBSDC
roles are represented and hash-linked. A passing result is an inventory gate,
not channel eligibility or numerical validation.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_inventory(manifest_path: Path, declaration_path: Path, protocol_path: Path) -> dict[str, Any]:
    manifest = _json(manifest_path)
    declaration = _json(declaration_path)
    protocol = _json(protocol_path)
    reasons: list[str] = []

    if protocol.get("status") != "prospective_intake_contract":
        reasons.append("NBSDC protocol is not prospective")
    if protocol.get("outcomes_accessed_before_freeze") is not False:
        reasons.append("NBSDC protocol does not prohibit pre-outcome access")
    if manifest.get("manifest_type") != "external_hrs_metadata_only_intake":
        reasons.append("manifest is not a generic byte-level HRS intake")
    if manifest.get("numerical_values_inspected") is not False:
        reasons.append("manifest does not prove numerical values were unopened")
    if manifest.get("archive_members_parsed") is not False:
        reasons.append("manifest does not prove archive members were unopened")
    if manifest.get("protocol_sha256") != _sha256(protocol_path):
        reasons.append("manifest protocol hash does not match NBSDC protocol")

    files = manifest.get("files")
    by_path: dict[str, dict[str, Any]] = {}
    if not isinstance(files, list) or not files:
        reasons.append("manifest contains no files")
        files = []
    for index, record in enumerate(files):
        if not isinstance(record, dict):
            reasons.append(f"manifest file record {index} is not an object")
            continue
        relative_path = record.get("relative_path")
        digest = record.get("sha256")
        if not isinstance(relative_path, str) or not relative_path:
            reasons.append(f"manifest file record {index} has no relative path")
        elif relative_path in by_path:
            reasons.append(f"manifest contains duplicate relative path: {relative_path}")
        else:
            by_path[relative_path] = record
        if not isinstance(digest, str) or len(digest) != 64:
            reasons.append(f"manifest file record {index} has no valid SHA-256")

    if declaration.get("declaration_type") != "nbsdc_winter_olympics_file_roles":
        reasons.append("unsupported NBSDC file-role declaration type")
    roles = declaration.get("roles")
    if not isinstance(roles, dict):
        reasons.append("file-role declaration has no roles object")
        roles = {}

    used_paths: set[str] = set()
    role_results: dict[str, dict[str, Any]] = {}
    for role in protocol.get("required_file_roles_before_channel_mapping", []):
        value = roles.get(role)
        paths = value.get("relative_paths") if isinstance(value, dict) else None
        if not isinstance(paths, list) or not paths or not all(isinstance(item, str) and item for item in paths):
            reasons.append(f"missing file role or relative path: {role}")
            role_results[role] = {"present": False, "relative_paths": paths or []}
            continue
        missing = [item for item in paths if item not in by_path]
        duplicates = [item for item in paths if item in used_paths]
        if missing:
            reasons.append(f"file role {role} references files absent from manifest: {missing}")
        if duplicates:
            reasons.append(f"file role {role} reuses a path assigned to another role: {duplicates}")
        used_paths.update(paths)
        role_results[role] = {
            "present": not missing and not duplicates,
            "relative_paths": paths,
            "source_file_id": value.get("source_file_id") if isinstance(value, dict) else None,
        }

    eligible = not reasons
    return {
        "schema_version": 1,
        "decision": "INVENTORY_READY_FOR_CHANNEL_MAPPING" if eligible else "INVENTORY_INCOMPLETE",
        "inventory_ready": eligible,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "declaration": str(declaration_path),
        "declaration_sha256": _sha256(declaration_path),
        "protocol": str(protocol_path),
        "protocol_sha256": _sha256(protocol_path),
        "numerical_values_inspected": False,
        "role_results": role_results,
        "claim_boundary": "Inventory integrity only; no channel eligibility, physics validation, safety certification or SAGA effectiveness claim.",
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--declaration", type=Path, required=True)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("research/nbsdc_winter_olympics_intake_protocol_2026_10_04.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/public_validation/results/external_hrs_intake/nbsdc_winter_olympics_inventory.json"),
    )
    args = parser.parse_args()
    report = validate_inventory(args.manifest, args.declaration, args.protocol)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0 if report["inventory_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
