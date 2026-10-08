import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_reference_leak_detector_protocol_is_preaccess_frozen_and_bounded() -> None:
    protocol = json.loads(
        (ROOT / "research/hydrogen_reference_leak_detector_protocol_2026_10_08.json").read_text(
            encoding="utf-8"
        )
    )

    assert protocol["status"] == "FROZEN_BEFORE_RAW_EXCEL_OUTCOME_ACCESS"
    assert protocol["pre_access_statement"]["raw_workbook_downloaded"] is False
    assert protocol["pre_access_statement"]["raw_workbook_opened"] is False
    assert protocol["pre_access_statement"]["numerical_detector_outcomes_seen"] is False
    assert protocol["source"]["doi"] == "10.5281/zenodo.12180368"
    assert protocol["source"]["license"] == "CC BY 4.0"
    assert protocol["frozen_primary_screens"]["eligible_detector_count_min"] == 2
    assert protocol["frozen_primary_screens"][
        "distinct_reference_levels_per_detector_min"
    ] == 3
    assert protocol["decision_policy"]["runtime_application"] is False
    assert "full digital twin" in protocol["claim_boundary"]
