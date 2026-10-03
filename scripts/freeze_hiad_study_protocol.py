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
    "research/analysis_plan.json",
    "docs/EXPERT_REVIEW_PROTOCOL.md",
    "scripts/prepare_hiad_coordinator_review.py",
    "scripts/freeze_hiad_approved_casebook.py",
    "scripts/run_hiad_decision_evaluation.py",
    "scripts/package_hiad_expert_review.py",
    "scripts/analyze_hiad_expert_review.py",
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
        "holdout_response_collection_permitted": False,
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
