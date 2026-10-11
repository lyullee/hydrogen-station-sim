from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_jrc_gastef_recheck_preserves_raw_trace_boundary() -> None:
    record = json.loads(
        (
            ROOT
            / "research/jrc_gastef_public_access_recheck_2026_10_12.json"
        ).read_text(encoding="utf-8")
    )
    assert record["evidence_role"] == "public_access_recheck_only"
    assert record["eligibility_decision"] == "CONTROLLED_ACCESS_LEAD_NO_PUBLIC_RAW_ARCHIVE"
    assert record["access_observation"]["official_records_retrieved"] is True
    assert record["access_observation"]["machine_readable_raw_trace_retrieved"] is False
    assert record["access_observation"]["datasets_table_public_url_found"] is False
    assert record["full_loop_holdout_eligible"] is False
    assert record["numeric_holdout_added"] is False
    assert record["runtime_model_changed"] is False
    assert len(record["source_records"]) == 3
    archived = record["hytransfer_archived_site_recheck"]
    assert archived["archived_site_retrieved"] is True
    assert archived["public_document_or_image_links_count"] == 15
    assert archived["machine_readable_data_links_found"] is False
    assert archived["raw_gastef_files_exposed"] is False
