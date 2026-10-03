import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_byrnes_screen_is_explicitly_exploratory_and_not_a_validation_pass():
    result = json.loads(
        (ROOT / "research/byrnes_zenodo_exploratory_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert result["evidence_role"] == "post_access_exploratory_screening"
    assert result["source"]["doi"] == "10.5281/zenodo.20728325"
    assert result["aggregate"]["case_count"] == 3
    assert result["aggregate"]["joint_screen_pass_count"] == 2
    assert result["aggregate"]["claim_supported"] is False
    assert "not a prospective validation gate" in result["claim_boundary"]
