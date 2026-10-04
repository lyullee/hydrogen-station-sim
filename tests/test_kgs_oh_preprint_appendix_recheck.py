import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_kgs_appendix_and_code_boundary_is_reproducibly_recorded():
    record = json.loads(
        (ROOT / "research/kgs_oh_preprint_appendix_recheck_2026_10_05.json")
        .read_text(encoding="utf-8")
    )
    appendix = record["appendix_access"]
    code = record["code_access"]
    assert record["source"]["published_doi"] == "10.1007/s11814-025-00551-9"
    assert record["source"]["reported_real_hrs_scenarios"] == 6
    assert appendix["pdf_pages"] == 2
    assert appendix["appendix_sha256_matches_expected"] is True
    assert all(appendix["required_table_terms_present"].values())
    assert appendix["raw_synchronized_logger_present"] is False
    assert code["result"] == "REDIRECTED_TO_SIGN_IN"
    assert code["files_retrieved"] == 0
    assert record["classification"]["full_loop_station_vehicle_holdout_eligible"] is False
    assert record["classification"]["goal_completion_permitted"] is False
