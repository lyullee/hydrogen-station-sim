import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_zbt_hrs_article_is_logged_as_real_station_context_without_holdout_promotion():
    record = json.loads(
        (ROOT / "research/zbt_hrs_sampling_article_data_boundary_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    assert record["source"]["doi"] == "10.3390/cleantechnol8030091"
    observed = record["observed_evidence"]
    assert observed["facility"].startswith("ZBT hydrogen test field")
    assert observed["station_configuration"]["storage_banks"] == 7
    assert observed["raw_synchronized_rows_public"] is False
    decision = record["eligibility_decision"]
    assert decision["full_loop_external_holdout_eligible"] is False
    assert "raw measurements" in record["source"]["license"]
    assert "does not change" in record["claim_boundary"]
