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


def _channel_ok(channels: dict[str, Any], name: str) -> bool:
    value = channels.get(name)
    if not _present(value):
        return False
    if isinstance(value, dict):
        if name == "common_time_base":
            return True
        unit = value.get("unit")
        return isinstance(unit, str) and bool(unit.strip())
    # A boolean declaration is accepted only for common_time_base, whose unit
    # is not applicable.  All measured channels must declare their units.
    return name == "common_time_base"


def validate(manifest_path: Path, declaration_path: Path, protocol_path: Path) -> dict[str, Any]:
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
    for index, record in enumerate(manifest.get("files") or []):
        if not isinstance(record, dict) or len(str(record.get("sha256", ""))) != 64:
            reasons.append(f"intake file record {index} has no valid SHA-256")

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
    for required in protocol.get("required_channels") or []:
        if not _channel_ok(channels, required):
            reasons.append(f"missing required channel or unit: {required}")

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
        "reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--declaration", type=Path, required=True)
    parser.add_argument(
        "--protocol", type=Path,
        default=Path("research/external_hrs_intake_protocol.json"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/public_validation/results/external_hrs_intake/eligibility.json"),
    )
    args = parser.parse_args()
    report = validate(args.manifest, args.declaration, args.protocol)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0 if report["eligible_for_numerical_evaluation"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
