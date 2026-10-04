"""Audit the pre-approval state of the HIAD decision-support casebook.

This command is deliberately a *readiness* audit.  It never marks a case as
approved, never creates model responses, and never enables expert collection.
It records whether a coordinator still needs to inspect the candidate vignettes
and whether the ethics gate permits collection.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASEBOOK = ROOT / "data/public_validation/results/hiad_holdout_preparation/casebook_for_approval.json"
DEFAULT_PRESCREEN = ROOT / "data/public_validation/results/hiad_coordinator_prescreen/prescreen_manifest.json"
DEFAULT_PROTOCOL = ROOT / "research/hiad_study_protocol_manifest.json"
DEFAULT_OUTPUT = ROOT / "data/public_validation/results/hiad_holdout_preparation/readiness_audit.json"
DEFAULT_REPORT = ROOT / "data/public_validation/results/hiad_holdout_preparation/READINESS_AUDIT.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(casebook: dict[str, Any], prescreen: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    cases = casebook.get("cases") if isinstance(casebook.get("cases"), list) else []
    approvals = Counter(str(case.get("expert_vignette_approved") or "PENDING").upper() for case in cases)
    leakage = Counter(str(case.get("narrative_action_leakage_review") or "PENDING").upper() for case in cases)
    expected = int(casebook.get("holdout_count") or 24)
    ethics_ready = (
        protocol.get("ethics_status") in {"approved", "exempt", "not_required"}
        and bool(protocol.get("ethics_determination_id"))
        and protocol.get("holdout_response_collection_permitted") is True
    )
    prescreen_count = int(prescreen.get("case_count") or 0)
    aggregate = {
        "candidate_case_count": len(cases),
        "expected_holdout_count": expected,
        "candidate_count_matches_protocol": len(cases) == expected,
        "prescreen_count": prescreen_count,
        "prescreen_count_matches_candidate": prescreen_count == len(cases),
        "prescreen_is_advisory_only": prescreen.get("advisory_only") is True,
        "approval_counts": dict(approvals),
        "leakage_review_counts": dict(leakage),
        "approved_case_count": approvals.get("YES", 0),
        "unresolved_case_count": len(cases) - approvals.get("YES", 0),
        "ethics_gate_ready": ethics_ready,
    }
    collection_allowed = bool(
        aggregate["candidate_count_matches_protocol"]
        and aggregate["prescreen_count_matches_candidate"]
        and aggregate["prescreen_is_advisory_only"]
        and aggregate["approved_case_count"] == len(cases)
        and ethics_ready
    )
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pre_approval_readiness_audit",
        "aggregate": aggregate,
        "collection_allowed": collection_allowed,
        "next_action": (
            "A qualified non-rating coordinator must review every vignette, remove hindsight action leakage without adding facts, obtain the institutional determination, and only then export the approved casebook."
            if not collection_allowed else "Use only the hash-locked approved casebook and frozen allocation."
        ),
        "claim_boundary": "This audit is a workflow guard. It is not an ethics determination, expert approval, model-effectiveness result, or safety claim.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--casebook", type=Path, default=DEFAULT_CASEBOOK)
    parser.add_argument("--prescreen", type=Path, default=DEFAULT_PRESCREEN)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    for path in (args.casebook, args.prescreen, args.protocol):
        if not path.exists():
            raise SystemExit(f"required HIAD readiness input not found: {path}")
    result = audit(
        json.loads(args.casebook.read_text(encoding="utf-8")),
        json.loads(args.prescreen.read_text(encoding="utf-8")),
        json.loads(args.protocol.read_text(encoding="utf-8")),
    )
    result["inputs"] = {
        "casebook_sha256": _sha256(args.casebook),
        "prescreen_sha256": _sha256(args.prescreen),
        "protocol_sha256": _sha256(args.protocol),
        "outputs_local_only": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    aggregate = result["aggregate"]
    args.report.write_text("\n".join([
        "# HIAD casebook readiness audit",
        "",
        f"- Candidate cases: **{aggregate['candidate_case_count']}**",
        f"- Approved cases: **{aggregate['approved_case_count']}**",
        f"- Unresolved cases: **{aggregate['unresolved_case_count']}**",
        f"- Ethics gate ready: **{'YES' if aggregate['ethics_gate_ready'] else 'NO'}**",
        f"- Response collection allowed: **{'YES' if result['collection_allowed'] else 'NO'}**",
        "",
        "The prescreen is advisory. A qualified non-rating coordinator must complete every case before any holdout response collection.",
        "",
    ]) + "\n", encoding="utf-8")
    print(json.dumps({"aggregate": aggregate, "collection_allowed": result["collection_allowed"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
