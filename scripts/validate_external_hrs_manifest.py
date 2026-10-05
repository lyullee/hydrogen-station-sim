"""Check whether an externally supplied HRS bundle is eligible for mapping.

The checker consumes only the byte-level intake manifest and a custodian-supplied
metadata declaration.  It deliberately never opens, parses, or samples the
underlying CSV/XLSX/Parquet/archive files.  Passing this check means that the
package is *eligible for a separately frozen numerical evaluation*; it is not a
model-validation result.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
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


def _present(value: Any) -> bool:
    if isinstance(value, dict):
        return value.get("present") is True
    return value is True


def _channel_error(
    channels: dict[str, Any],
    name: str,
    accepted_units: dict[str, Any] | None = None,
) -> str | None:
    value = channels.get(name)
    if not _present(value):
        return f"missing required channel or unit: {name}"
    if isinstance(value, dict):
        if name == "common_time_base":
            return None
        unit = value.get("unit")
        if not isinstance(unit, str) or not unit.strip():
            return f"missing required channel or unit: {name}"
        allowed = (accepted_units or {}).get(name)
        if isinstance(allowed, list) and allowed and unit not in allowed:
            allowed_text = ", ".join(str(item) for item in allowed)
            return f"unsupported unit for {name}: {unit} (accepted: {allowed_text})"
        return None
    # A boolean declaration is accepted only for common_time_base, whose unit
    # is not applicable.  All measured channels must declare their units.
    return None if name == "common_time_base" else f"missing required channel or unit: {name}"


def _channel_ok(
    channels: dict[str, Any],
    name: str,
    accepted_units: dict[str, Any] | None = None,
) -> bool:
    return _channel_error(channels, name, accepted_units) is None


def _bundle_root(manifest: dict[str, Any], override: Path | None) -> Path | None:
    """Resolve the quarantined package root without parsing measurement files."""

    candidate = override or Path(str(manifest.get("source_path", "")))
    if not str(candidate):
        return None
    candidate = candidate.expanduser()
    if not candidate.exists():
        return None
    return candidate if candidate.is_dir() else candidate.parent


def _safe_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def validate(
    manifest_path: Path,
    declaration_path: Path,
    protocol_path: Path,
    *,
    bundle_root: Path | None = None,
) -> dict[str, Any]:
    """Return an auditable, non-numerical eligibility decision."""
    manifest = _json(manifest_path)
    declaration = _json(declaration_path)
    protocol = _json(protocol_path)
    reasons: list[str] = []

    if manifest.get("manifest_type") != "external_hrs_metadata_only_intake":
        reasons.append("manifest is not an external HRS metadata-only intake")
    if manifest.get("numerical_values_inspected") is not False:
        reasons.append("manifest does not prove that numerical values were unopened")
    if manifest.get("archive_members_parsed") is not False:
        reasons.append("manifest does not prove that archive members were unopened")
    if not isinstance(manifest.get("files"), list) or not manifest["files"]:
        reasons.append("intake manifest contains no files")
    records = manifest.get("files") or []
    if manifest.get("file_count") != len(records):
        reasons.append("intake manifest file_count does not match files")

    # Hashing is the only operation performed on the quarantined package.  No
    # CSV/XLSX/Parquet/archive parser is called here.
    root = _bundle_root(manifest, bundle_root)
    integrity = {
        "source_available": root is not None,
        "source_root": str(root) if root is not None else None,
        "records_checked": 0,
        "records_hash_verified": 0,
    }
    if root is None:
        reasons.append("quarantined bundle source path is unavailable for integrity verification")
    seen_paths: set[str] = set()
    sha_pattern = re.compile(r"^[0-9a-f]{64}$")
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            reasons.append(f"intake file record {index} is not an object")
            continue
        relative_path = record.get("relative_path")
        if not _safe_relative_path(relative_path):
            reasons.append(f"intake file record {index} has an unsafe relative_path")
            continue
        if relative_path in seen_paths:
            reasons.append(f"intake manifest contains duplicate relative_path: {relative_path}")
        seen_paths.add(relative_path)
        expected_bytes = record.get("bytes")
        expected_sha = str(record.get("sha256", ""))
        if not isinstance(expected_bytes, int) or expected_bytes < 0:
            reasons.append(f"intake file record {index} has no valid byte count")
            continue
        if not sha_pattern.fullmatch(expected_sha):
            reasons.append(f"intake file record {index} has no valid SHA-256")
            continue
        integrity["records_checked"] += 1
        if root is None:
            continue
        path = root / relative_path
        try:
            path.relative_to(root)
        except ValueError:
            reasons.append(f"intake file record {index} escapes the quarantined root")
            continue
        if not path.is_file():
            reasons.append(f"intake file record {index} is missing from quarantined root: {relative_path}")
            continue
        if path.stat().st_size != expected_bytes:
            reasons.append(f"intake file record {index} byte count does not match: {relative_path}")
            continue
        if _sha256(path) != expected_sha:
            reasons.append(f"intake file record {index} SHA-256 does not match: {relative_path}")
            continue
        integrity["records_hash_verified"] += 1

    if protocol.get("status") != "prospective_intake_contract":
        reasons.append("protocol is not a prospective intake contract")
    if protocol.get("outcomes_accessed_before_freeze") is not False:
        reasons.append("protocol does not prohibit pre-freeze outcome access")
    if manifest.get("protocol_sha256") != _sha256(protocol_path):
        reasons.append("intake manifest protocol hash does not match the supplied protocol")

    if declaration.get("declaration_type") != "external_hrs_bundle_metadata":
        reasons.append("metadata declaration has an unsupported declaration_type")
    if declaration.get("outcomes_accessed_before_freeze") is not False:
        reasons.append("metadata declaration does not prove pre-outcome freezing")

    channels = declaration.get("channels")
    if not isinstance(channels, dict):
        reasons.append("metadata declaration has no channels object")
        channels = {}
    accepted_units = protocol.get("accepted_units")
    if not isinstance(accepted_units, dict):
        reasons.append("protocol has no accepted_units contract")
        accepted_units = {}
    for required in protocol.get("required_channels") or []:
        error = _channel_error(channels, required, accepted_units)
        if error:
            reasons.append(error)

    metadata = declaration.get("metadata")
    if not isinstance(metadata, dict):
        reasons.append("metadata declaration has no metadata object")
        metadata = {}
    for required in protocol.get("required_metadata") or []:
        value = metadata.get(required)
        if value in (None, False, "", [], {}):
            reasons.append(f"missing required metadata: {required}")

    eligible = not reasons
    return {
        "schema_version": 1,
        "decision": "ELIGIBLE_FOR_PROSPECTIVE_MAPPING" if eligible else "INELIGIBLE_MISSING_METADATA",
        "eligible_for_numerical_evaluation": eligible,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "declaration": str(declaration_path),
        "declaration_sha256": _sha256(declaration_path),
        "protocol": str(protocol_path),
        "protocol_sha256": _sha256(protocol_path),
        "numerical_values_inspected": False,
        "claim_boundary": (
            "Eligibility metadata only; this is not a model-validation result, "
            "accuracy claim, or IJHE completion evidence."
        ),
        "integrity": integrity,
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--declaration", type=Path, required=True)
    parser.add_argument(
        "--bundle-root",
        type=Path,
        default=None,
        help="Optional quarantined package root to hash-verify against the manifest.",
    )
    parser.add_argument(
        "--protocol", type=Path,
        default=Path("research/external_hrs_intake_protocol.json"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/public_validation/results/external_hrs_intake/eligibility.json"),
    )
    args = parser.parse_args()
    report = validate(
        args.manifest,
        args.declaration,
        args.protocol,
        bundle_root=args.bundle_root,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0 if report["eligible_for_numerical_evaluation"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
