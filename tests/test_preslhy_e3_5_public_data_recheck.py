import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_preslhy_e3_5_metadata_recheck_preserves_scope_boundary():
    record = json.loads(
        (ROOT / "research/preslhy_e3_5_public_data_recheck_2026_10_04.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["decision"] == "PUBLIC_RAW_CONSEQUENCE_CANDIDATE_METADATA_VERIFIED"
    assert record["gate_impact"] == "independent_full_loop_gate_remains_open"
    assert record["source"]["license"] == "CC BY-SA 4.0"
    assert record["source"]["archive_size_bytes"] == 11341115392
    assert record["metadata_verification"]["http_range_probe"]["status"] == 206
    assert record["metadata_verification"]["archive_not_vendored"] is True
    assert "gaseous high-pressure HRS station-to-vehicle full-loop validation" in (
        record["eligibility_assessment"]["not_eligible_for"]
    )

