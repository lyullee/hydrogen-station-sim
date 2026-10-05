"""Create a conservative, hash-linked HIAD reviewer handoff recheck."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def build() -> dict:
    casebook = ROOT / "data/public_validation/results/hiad_holdout_preparation/casebook_for_approval.json"
    prescreen = ROOT / "data/public_validation/results/hiad_coordinator_prescreen/prescreen_manifest.json"
    review_csv = ROOT / "data/public_validation/results/hiad_coordinator_prescreen/coordinator_review.csv"
    review_html = ROOT / "data/public_validation/results/hiad_coordinator_prescreen/coordinator_review.html"
    protocol = ROOT / "research/hiad_study_protocol_manifest.json"
    preflight = ROOT / "research/hiad_casebook_machine_preflight_2026_10_05.json"
    readiness = ROOT / "data/public_validation/results/hiad_holdout_preparation/readiness_audit.json"
    for path in (casebook, prescreen, review_csv, review_html, protocol, preflight, readiness):
        if not path.is_file():
            raise FileNotFoundError(path)
    preflight_data = json.loads(preflight.read_text(encoding="utf-8"))
    readiness_data = json.loads(readiness.read_text(encoding="utf-8"))
    readiness_view = readiness_data.get("readiness", {})
    aggregate = readiness_data.get("aggregate", {})
    # The holdout-preparation audit intentionally uses a pre-approval schema
    # (aggregate/collection_allowed).  Accept both that schema and the older
    # readiness object without inferring approval from a populated casebook.
    casebook_frozen = bool(readiness_view.get("casebook_frozen", False))
    ethics_ready = bool(
        readiness_view.get("ethics_and_collection_permitted", False)
        or readiness_data.get("collection_allowed", False)
        and aggregate.get("ethics_gate_ready", False)
    )
    coordinator_complete = bool(
        readiness_view.get("coordinator_review_complete", False)
        or aggregate.get("approved_case_count", 0) == aggregate.get("candidate_case_count", -1)
    )
    independent_complete = bool(readiness_view.get("independent_review_complete", False))
    return {
        "schema_version": 1,
        "rechecked_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": git_commit(),
        "status": "PENDING_COORDINATOR_APPROVAL_AND_ETHICS_DETERMINATION",
        "machine_preflight": {
            "pass": preflight_data.get("machine_preflight_pass") is True,
            "case_count": preflight_data.get("case_count"),
            "record": str(preflight.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(preflight),
        },
        "review_package": {
            "casebook": {"path": str(casebook.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(casebook), "case_count": 24},
            "prescreen_manifest": {"path": str(prescreen.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(prescreen), "advisory_only": True},
            "review_csv": {"path": str(review_csv.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(review_csv)},
            "review_html": {"path": str(review_html.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(review_html)},
            "protocol_manifest": {"path": str(protocol.relative_to(ROOT)).replace("\\", "/"), "sha256": sha256(protocol)},
        },
        "current_readiness": {
            "casebook_frozen": casebook_frozen,
            "ethics_and_collection_permitted": ethics_ready,
            "coordinator_review_complete": coordinator_complete,
            "independent_review_complete": independent_complete,
            "readiness_record": str(readiness.relative_to(ROOT)).replace("\\", "/"),
            "readiness_sha256": sha256(readiness),
        },
        "required_next_evidence": [
            "institutional ethics, exemption or not-required determination with identifier",
            "qualified non-rating coordinator KEEP/REWRITE decision for all 24 cases",
            "hash-locked approved casebook freeze manifest",
            "168 retained masked responses",
            "three independent qualified reviewer rating files and locked analysis",
        ],
        "claim_boundary": "This recheck proves package integrity and machine preflight only. It is not casebook approval, ethics approval, response collection, expert review, SAGA effectiveness, or safety evidence.",
    }


def main() -> None:
    path = ROOT / "research/hiad_reviewer_handoff_recheck_2026_10_05.json"
    path.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
