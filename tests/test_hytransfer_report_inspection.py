import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hytransfer_public_report_inspection_keeps_data_request_boundary():
    record = json.loads(
        (ROOT / "research/hytransfer_public_report_inspection.json").read_text(
            encoding="utf-8"
        )
    )
    source = record["source"]
    findings = record["document_findings"]
    assert source["pages"] == 192
    assert source["bytes"] == 13_363_085
    assert len(source["sha256"]) == 64
    assert findings["reported_gastef_recorded_files"] == 18
    assert findings["reported_file_groups"] == {"group_1": 14, "group_2": 4}
    assert findings["machine_readable_files_embedded"] is False
    assert findings["external_data_download_links_found"] == []
    assert "controlled-access request lead" in findings["interpretation"]
    assert "does not authorize redistribution" in record["claim_boundary"]
