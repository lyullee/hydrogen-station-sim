"""Hash-lock the HIAD expert-study protocol and governance packet."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


REQUIRED_FILES = (
    "research/HIAD_EXPERT_STUDY_PREREGISTRATION.md",
    "research/ETHICS_DETERMINATION_REQUEST.md",
    "research/EXPERT_REVIEWER_INFORMATION_SHEET.md",
    "research/HIAD_DATA_MANAGEMENT_PLAN.md",
    "research/HIAD_DESIGN_SENSITIVITY.md",
    "research/hiad_design_sensitivity.json",
    "research/analysis_plan.json",
    "docs/EXPERT_REVIEW_PROTOCOL.md",
    "scripts/prepare_hiad_coordinator_review.py",
    "scripts/freeze_hiad_approved_casebook.py",
    "scripts/run_hiad_decision_evaluation.py",
    "scripts/package_hiad_expert_review.py",
    "scripts/analyze_hiad_expert_review.py",
    "scripts/analyze_hiad_design_sensitivity.py",
)
PLACEHOLDER = "[INSTITUTION TO COMPLETE]"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit(root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def validate_manifest_integrity(
    root: Path,
    manifest: dict[str, object] | None,
    *,
    require_collection_permission: bool = False,
) -> list[str]:
    """Return protocol-lock violations without authorizing study activity.

    A resolved institutional determination alone is insufficient: response
    collection must use the exact protocol and code files hash-locked before
    the collection run.  This shared validator keeps collection and readiness
    tooling aligned with the freezer's interpretation of the guard.
    """
    if not isinstance(manifest, dict):
        return ["protocol manifest missing or invalid"]

    errors: list[str] = []
    if manifest.get("protocol_id") != "HIAD-SAGA-2601":
        errors.append("unexpected protocol ID")
    if manifest.get("protocol_frozen_before_holdout_collection") is not True:
        errors.append("protocol is not marked frozen before holdout collection")

    locked = manifest.get("required_file_sha256")
    if not isinstance(locked, dict):
        errors.append("required-file hash map missing or invalid")
        locked = {}
    required = set(REQUIRED_FILES)
    actual = set(locked)
    if actual != required:
        missing = sorted(required - actual)
        extra = sorted(actual - required)
        if missing:
            errors.append("protocol hash map omits required files: " + ", ".join(missing))
        if extra:
            errors.append("protocol hash map contains unexpected files: " + ", ".join(extra))
    for relative in sorted(required & actual):
        expected = locked.get(relative)
        path = root / relative
        if not isinstance(expected, str) or len(expected) != 64:
            errors.append(f"invalid SHA-256 for {relative}")
        elif not path.is_file() or _sha256(path) != expected:
            errors.append(f"protocol hash mismatch: {relative}")

    if require_collection_permission:
        if manifest.get("ethics_status") not in {"approved", "exempt", "not-required"}:
            errors.append("institutional ethics status does not permit holdout collection")
        if not str(manifest.get("ethics_determination_id") or "").strip():
            errors.append("institutional determination ID missing")
        if manifest.get("reviewer_recruitment_permitted") is not True:
            errors.append("reviewer recruitment is not permitted by the protocol")
        if manifest.get("holdout_response_collection_permitted") is not True:
            errors.append("holdout response collection is not permitted by the protocol")
        if manifest.get("unresolved_institution_fields"):
            errors.append("institutional fields remain unresolved")
    return errors


def build_manifest(
    root: Path, ethics_status: str, determination_id: str = ""
) -> dict[str, object]:
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    if missing:
        raise SystemExit("Protocol package is incomplete: " + ", ".join(missing))
    unresolved = {}
    for name in REQUIRED_FILES:
        if name.endswith(".md"):
            count = (root / name).read_text(encoding="utf-8").count(PLACEHOLDER)
            if count:
                unresolved[name] = count
    determination_id = determination_id.strip()
    if ethics_status != "pending" and not determination_id:
        raise SystemExit("A determination ID is required when ethics status is resolved")
    if ethics_status != "pending" and unresolved:
        raise SystemExit(
            "Institutional fields remain incomplete after ethics resolution: "
            + ", ".join(f"{name} ({count})" for name, count in unresolved.items())
        )
    preregistration = (
        root / "research/HIAD_EXPERT_STUDY_PREREGISTRATION.md"
    ).read_text(encoding="utf-8")
    if "No holdout model responses or expert ratings collected" not in preregistration:
        raise SystemExit("Preregistration does not state the pre-collection status")
    return {
        "schema_version": 1,
        "protocol_id": "HIAD-SAGA-2601",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": _git_commit(root),
        "ethics_status": ethics_status,
        "ethics_determination_id": determination_id or None,
        "reviewer_recruitment_permitted": ethics_status != "pending" and not unresolved,
        "holdout_response_collection_permitted": ethics_status != "pending" and not unresolved,
        "protocol_frozen_before_holdout_collection": True,
        "unresolved_institution_fields": unresolved,
        "required_file_sha256": {
            name: _sha256(root / name) for name in REQUIRED_FILES
        },
        "amendment_rule": (
            "After holdout collection starts, changes require a dated version, rationale, "
            "new manifest, and prospective/post-hoc classification."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--ethics-status",
        choices=("pending", "approved", "exempt", "not-required"),
        default="pending",
    )
    parser.add_argument("--determination-id", default="")
    parser.add_argument(
        "--output", type=Path,
        default=Path("research/hiad_study_protocol_manifest.json"),
    )
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = build_manifest(root, args.ethics_status, args.determination_id)
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
