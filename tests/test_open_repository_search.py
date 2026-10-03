import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_open_repository_recheck_keeps_full_loop_claim_boundary():
    record = json.loads(
        (ROOT / "research/open_repository_search_2026_10_04.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["decision"] == "NO_NEW_ELIGIBLE_PUBLIC_RAW_SET"
    assert record["gate_impact"] == "unchanged_independent_full_loop_gate_remains_open"
    assert len(record["zenodo_api_recheck"]["queries"]) >= 5
    assert any(
        candidate["record_id"] == "22892319"
        and candidate["decision"] == "PUBLIC_PUBLICATION_ONLY"
        for candidate in record["zenodo_api_recheck"]["candidate_classifications"]
    )
    assert any(
        item["doi"] == "10.17632/8km9z62tct.1"
        and item["decision"] == "COMPONENT_STORAGE_TANK_ONLY"
        for item in record["public_repository_followups"]
    )
    assert "No candidate is promoted" in record["claim_boundary"]


def test_external_search_mirror_contains_same_recheck_decision():
    mirror = json.loads(
        (ROOT / "research/external_full_loop_data_search.json").read_text(
            encoding="utf-8"
        )
    )
    assert mirror["last_reviewed"] == "2026-10-04"
    assert mirror["zenodo_api_and_mendeley_recheck_2026_10_04"]["decision"] == (
        "NO_NEW_ELIGIBLE_PUBLIC_RAW_SET"
    )
