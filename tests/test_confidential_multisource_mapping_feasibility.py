from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_controlled_multisource_feasibility_rejects_nonmeasurement_candidates():
    record = json.loads((
        ROOT / "research" / "confidential_multisource_mapping_feasibility_2026_10_07.json"
    ).read_text(encoding="utf-8"))

    assert record["source_identifiers_published"] is False
    assert record["original_headers_published"] is False
    assert record["raw_rows_persisted"] is False
    assert record["controlled_review"]["sample_data_rows_structurally_inspected_in_memory"] is True
    assert record["controlled_review"]["measurement_values_persisted"] is False
    assert record["controlled_review"]["co_located_workbook_candidates"] == 0
    assert record["canonical_mapping_screen"]["all_required_full_loop_channels_have_unambiguous_header_candidates"] is False
    assert record["canonical_mapping_screen"]["decision"] == (
        "no_measurement_grade_multisource_candidate_found_in_controlled_intake"
    )
    assert "station-to-vehicle full-loop validation" in record["prohibited_evidence_use"]
