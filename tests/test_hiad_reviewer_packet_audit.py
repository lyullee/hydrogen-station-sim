import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_hiad_reviewer_packet import _required_paths, audit_packet  # noqa: E402


def _load(paths):
    return {
        key: json.loads(paths[key].read_text(encoding="utf-8"))
        for key in ("casebook", "prescreen_manifest", "protocol", "readiness", "gate_recheck", "machine_preflight")
    }


def test_packet_audit_is_ready_for_human_review_but_fail_closed_for_collection():
    paths = _required_paths()
    loaded = _load(paths)
    with paths["review_csv"].open(encoding="utf-8-sig") as handle:
        row_count = sum(1 for _ in handle) - 1
    result = audit_packet(
        paths=paths,
        casebook=loaded["casebook"],
        prescreen=loaded["prescreen_manifest"],
        protocol=loaded["protocol"],
        readiness=loaded["readiness"],
        gate_recheck=loaded["gate_recheck"],
        machine_preflight=loaded["machine_preflight"],
        review_csv_rows=row_count,
    )
    assert result["ready_for_human_review"] is True
    assert result["ready_for_response_collection"] is False
    assert result["status"] == "READY_FOR_HUMAN_REVIEW_COLLECTION_BLOCKED"
    assert all(item["status"] == "PASS" for item in result["checks"])
    assert result["casebook"]["candidate_count"] == 24


def test_packet_audit_does_not_infer_collection_from_machine_preflight():
    paths = _required_paths()
    loaded = _load(paths)
    loaded["machine_preflight"]["machine_preflight_pass"] = True
    loaded["readiness"]["collection_allowed"] = True
    loaded["protocol"]["holdout_response_collection_permitted"] = True
    result = audit_packet(
        paths=paths,
        casebook=loaded["casebook"],
        prescreen=loaded["prescreen_manifest"],
        protocol=loaded["protocol"],
        readiness=loaded["readiness"],
        gate_recheck=loaded["gate_recheck"],
        machine_preflight=loaded["machine_preflight"],
        review_csv_rows=24,
    )
    assert result["ready_for_response_collection"] is False
    assert result["checks"][-1]["status"] == "FAIL"
