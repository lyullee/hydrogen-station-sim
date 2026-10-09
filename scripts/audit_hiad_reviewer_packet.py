"""Audit the HIAD reviewer packet without approving any human gate.

The packet is intentionally split into machine checks and human decisions.  This
audit verifies that the files handed to the coordinator refer to the same
24-case source, that the current machine preflight is the one being used, and
that collection remains fail-closed until the institutional and reviewer gates
are recorded.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "research/hiad_reviewer_packet_audit_2026_10_09.json"
DEFAULT_REPORT = ROOT / "research/HIAD_REVIEWER_PACKET_AUDIT_2026_10_09.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _latest_preflight() -> Path:
    candidates = sorted(ROOT.glob("research/hiad_casebook_machine_preflight_*.json"))
    if not candidates:
        raise FileNotFoundError("No HIAD machine preflight record found")
    return candidates[-1]


def _required_paths() -> dict[str, Path]:
    return {
        "casebook": ROOT / "data/public_validation/results/hiad_holdout_preparation/casebook_for_approval.json",
        "prescreen_manifest": ROOT / "data/public_validation/results/hiad_coordinator_prescreen/prescreen_manifest.json",
        "review_csv": ROOT / "data/public_validation/results/hiad_coordinator_prescreen/coordinator_review.csv",
        "review_html": ROOT / "data/public_validation/results/hiad_coordinator_prescreen/coordinator_review.html",
        "protocol": ROOT / "research/hiad_study_protocol_manifest.json",
        "readiness": ROOT / "data/public_validation/results/hiad_holdout_preparation/readiness_audit.json",
        "gate_recheck": ROOT / "research/hiad_casebook_gate_recheck_2026_10_09.json",
        "machine_preflight": _latest_preflight(),
        "coordinator_handoff": ROOT / "research/HIAD_COORDINATOR_REVIEW_HANDOFF.md",
        "ethics_request": ROOT / "research/ETHICS_DETERMINATION_REQUEST.md",
    }


def _check(check_id: str, passed: bool, observed: Any, requirement: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "PASS" if passed else "FAIL",
        "observed": observed,
        "requirement": requirement,
    }


def audit_packet(
    *,
    paths: dict[str, Path],
    casebook: dict[str, Any],
    prescreen: dict[str, Any],
    protocol: dict[str, Any],
    readiness: dict[str, Any],
    gate_recheck: dict[str, Any],
    machine_preflight: dict[str, Any],
    review_csv_rows: int,
) -> dict[str, Any]:
    cases = casebook.get("cases") if isinstance(casebook.get("cases"), list) else []
    expected = int(casebook.get("holdout_count") or 24)
    required_files_ok = all(path.is_file() for path in paths.values())
    prescreen_hash_ok = prescreen.get("casebook_sha256") == sha256(paths["casebook"])
    output_hashes = prescreen.get("output_sha256") or {}
    output_hashes_ok = (
        output_hashes.get("coordinator_review.csv") == sha256(paths["review_csv"])
        and output_hashes.get("coordinator_review.html") == sha256(paths["review_html"])
    )
    preflight_count = machine_preflight.get("case_count")
    gate_status = gate_recheck.get("human_gates") or {}
    unresolved_human_gates = {
        key: value for key, value in gate_status.items()
        if value not in {"COMPLETE", "APPROVED", "PERMITTED"}
    }
    readiness_aggregate = readiness.get("aggregate") or {}
    collection_allowed = bool(
        readiness.get("collection_allowed") is True
        and protocol.get("holdout_response_collection_permitted") is True
    )
    checks = [
        _check(
            "required_packet_files_present",
            required_files_ok,
            {key: path.is_file() for key, path in paths.items()},
            "The coordinator must receive every source, prescreen, protocol and gate record.",
        ),
        _check(
            "casebook_and_review_counts_align",
            len(cases) == expected == int(prescreen.get("case_count") or -1) == review_csv_rows == int(preflight_count or -1),
            {
                "casebook": len(cases),
                "declared": expected,
                "prescreen": prescreen.get("case_count"),
                "review_csv": review_csv_rows,
                "machine_preflight": preflight_count,
            },
            "The same 24 candidate cases must be represented in every machine-readable packet file.",
        ),
        _check(
            "prescreen_hash_links_casebook",
            prescreen_hash_ok,
            {"recorded": prescreen.get("casebook_sha256"), "actual": sha256(paths["casebook"])},
            "The prescreen must be generated from the casebook currently handed to the coordinator.",
        ),
        _check(
            "prescreen_hash_links_exports",
            output_hashes_ok,
            {"csv": sha256(paths["review_csv"]), "html": sha256(paths["review_html"])},
            "The prescreen manifest must identify the CSV and HTML actually delivered for review.",
        ),
        _check(
            "machine_preflight_passes",
            machine_preflight.get("machine_preflight_pass") is True
            and int(machine_preflight.get("case_count") or -1) == expected,
            {
                "machine_preflight_pass": machine_preflight.get("machine_preflight_pass"),
                "forbidden_model_input_cases": (machine_preflight.get("leakage_advisory") or {}).get("cases_with_forbidden_model_input_keys", []),
            },
            "Only the current machine preflight may establish structural readiness; it cannot approve human gates.",
        ),
        _check(
            "human_gates_remain_explicit",
            bool(unresolved_human_gates),
            unresolved_human_gates,
            "The audit must show unresolved human gates instead of inferring approval from machine output.",
        ),
        _check(
            "collection_fails_closed",
            collection_allowed is False,
            {
                "readiness_collection_allowed": readiness.get("collection_allowed"),
                "protocol_collection_permitted": protocol.get("holdout_response_collection_permitted"),
                "gate_status": gate_status,
            },
            "No masked responses may be collected until the institutional and reviewer gates are explicitly complete.",
        ),
    ]
    ready_for_human_review = required_files_ok and all(
        item["status"] == "PASS" for item in checks[:5]
    )
    return {
        "schema_version": 1,
        "artifact_type": "hiad_reviewer_packet_audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "READY_FOR_HUMAN_REVIEW_COLLECTION_BLOCKED" if ready_for_human_review else "PACKET_INCOMPLETE",
        "ready_for_human_review": ready_for_human_review,
        "ready_for_response_collection": False,
        "checks": checks,
        "human_gate_status": gate_status,
        "packet": {
            key: {"path": _relative(path), "sha256": sha256(path)}
            for key, path in paths.items()
            if path.is_file()
        },
        "casebook": {
            "candidate_count": len(cases),
            "expected_holdout_count": expected,
            "advisory_tier_counts": prescreen.get("tier_counts", {}),
            "approved_case_count": readiness_aggregate.get("approved_case_count", 0),
            "unresolved_case_count": readiness_aggregate.get("unresolved_case_count", len(cases)),
        },
        "next_human_actions": [
            "Institution records ethics, exemption or not-required determination and identifier.",
            "Qualified non-rating coordinator reviews all 24 cases and exports approved_holdout_casebook.json.",
            "Freeze the approved casebook with the hash-locked freeze script.",
            "Only after the freeze and ethics gate, collect masked holdout responses and obtain independent expert ratings.",
        ],
        "claim_boundary": "This audit verifies packet integrity and fail-closed workflow only. It is not an ethics determination, casebook approval, holdout result, SAGA effectiveness result, safety claim, or publication approval.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    paths = _required_paths()
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise SystemExit("Missing HIAD reviewer packet files:\n" + "\n".join(missing))
    loaded = {
        key: json.loads(paths[key].read_text(encoding="utf-8"))
        for key in ("casebook", "prescreen_manifest", "protocol", "readiness", "gate_recheck", "machine_preflight")
    }
    with paths["review_csv"].open(encoding="utf-8-sig", newline="") as handle:
        review_csv_rows = sum(1 for _ in csv.DictReader(handle))
    result = audit_packet(
        paths=paths,
        casebook=loaded["casebook"],
        prescreen=loaded["prescreen_manifest"],
        protocol=loaded["protocol"],
        readiness=loaded["readiness"],
        gate_recheck=loaded["gate_recheck"],
        machine_preflight=loaded["machine_preflight"],
        review_csv_rows=review_csv_rows,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checks = result["checks"]
    report = [
        "# HIAD reviewer packet audit",
        "",
        f"- Status: **{result['status']}**",
        f"- Ready for human review: **{'YES' if result['ready_for_human_review'] else 'NO'}**",
        "- Response collection: **BLOCKED**",
        f"- Candidate cases: **{result['casebook']['candidate_count']}**",
        f"- Advisory flags: **{result['casebook']['advisory_tier_counts']}**",
        "",
        "## Machine checks",
        "",
    ]
    report.extend(f"- `{item['id']}`: **{item['status']}**" for item in checks)
    report.extend([
        "",
        "The package is ready to hand to a qualified non-rating coordinator, but no machine result closes the ethics, leakage, casebook-freeze, response-collection, or independent-review gates.",
        "",
        "## Required human actions",
        "",
    ])
    report.extend(f"1. {action}" for action in result["next_human_actions"])
    report.extend(["", result["claim_boundary"], ""])
    args.report.write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "ready_for_human_review": result["ready_for_human_review"],
        "ready_for_response_collection": result["ready_for_response_collection"],
        "failed_checks": [item["id"] for item in checks if item["status"] == "FAIL"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
