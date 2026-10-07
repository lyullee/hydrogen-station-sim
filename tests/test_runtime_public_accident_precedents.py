import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_runtime_public_accident_precedents import audit  # noqa: E402


def test_committed_runtime_precedent_routing_matches_rebuild():
    recorded = json.loads((
        ROOT / "research/runtime_public_accident_precedent_routing_2026_10_07.json"
    ).read_text(encoding="utf-8"))
    rebuilt = audit()

    assert recorded["status"] == rebuilt["status"] == "PASS"
    assert recorded["source"] == rebuilt["source"]
    assert recorded["aggregate"] == rebuilt["aggregate"]
    assert recorded["response_families"] == rebuilt["response_families"]
    assert recorded["aggregate"]["public_report_count"] == 23
    assert recorded["aggregate"]["mapped_response_family_count"] == 8
    assert recorded["aggregate"]["unmatched_response_family_count"] == 0
    assert recorded["aggregate"]["manifest_routing_failure_count"] == 0
    assert recorded["aggregate"]["prompt_projection_failure_count"] == 0
    assert recorded["raw_report_text_loaded"] is False
    assert recorded["effectiveness_claimed"] is False
    assert recorded["frequency_claimed"] is False


def test_every_mapped_family_reaches_manifest_and_prompt():
    result = audit()
    assert all(row["runtime_case_count"] == row["expected_case_count"] for row in result["response_families"])
    assert all(row["representative_count"] > 0 for row in result["response_families"])
    assert all(row["runtime_manifest_matches"] for row in result["response_families"])
    assert all(row["prompt_projection_matches"] for row in result["response_families"])
