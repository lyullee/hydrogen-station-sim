import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research" / "nrel_h2fills_geometry_sensitivity_recheck_2026_10_11.json"


def test_geometry_recheck_is_claim_bounded_and_hash_linked():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert data["status"] == "exploratory_geometry_sensitivity_only"
    assert "No variant is an independent confirmatory pass" in data["claim_limit"]
    assert data["source"]["workbook_sha256"]
    assert data["source"]["fit_source_sha256"]
    assert set(data["variants"]) == {
        "legacy_frozen",
        "capacity_eos_with_frozen_fit",
        "capacity_eos_no_volume_fit",
    }


def test_geometry_recheck_does_not_claim_a_runtime_or_gate_change():
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert "no parameter or default model was changed" in data["claim_limit"]
    assert data["source_worktree_dirty"] is False
