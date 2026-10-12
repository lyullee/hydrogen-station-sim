from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/hiad_event_category_concordance_2026_10_11.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_hiad_category_concordance_is_complete_and_bounded():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    source = artifact["source"]
    aggregate = artifact["aggregate"]
    cases = artifact["cases"]

    assert artifact["artifact_type"] == "hiad_public_metadata_to_runtime_family_concordance"
    assert artifact["status"] == "completed_retrospective_category_concordance"
    assert source["incident_narrative_used"] is False
    assert source["emergency_action_text_used"] is False
    assert source["physical_parameters_from_incident_text"] is False
    assert _sha256(ROOT / source["hiad_inventory"]) == source["hiad_inventory_sha256"]
    assert _sha256(ROOT / source["replay_coverage"]) == source["replay_coverage_sha256"]
    assert aggregate["case_count"] == 34
    assert aggregate["integration_trace_pass_count"] == 34
    assert len(cases) == 34
    assert len({case["event_id"] for case in cases}) == 34
    assert aggregate["category_concordance_counts"] == {
        "matched": 34,
        "partial": 0,
        "metadata_runtime_conflict": 0,
        "not_comparable": 0,
    }
    assert aggregate["representation_case_counts"] == {
        "direct_physical_replay": 29,
        "proxy_partial_replay": 4,
        "response_only_no_physical_model": 1,
    }
    assert all("title" not in case and "narrative" not in case for case in cases)
    event_803 = next(case for case in cases if case["event_id"] == "803")
    assert event_803["category_concordance"] == "matched"
    assert "gas_release" not in event_803["executed_recipe_ids"]
