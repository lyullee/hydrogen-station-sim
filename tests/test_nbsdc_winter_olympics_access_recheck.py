from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_nbsdc_recheck_preserves_application_boundary():
    path = ROOT / "research/nbsdc_winter_olympics_access_recheck_2026_10_05.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["status"] == "ACCESS_REQUEST_ONLY_REAL_HRS_CANDIDATE"
    assert report["source"]["cstr"] == "CSTR:16666.11.nbsdc.aI3fJrzX"
    assert report["eligibility_decision"]["full_loop_public_holdout"] is False
    files = report["public_file_inventory"]
    assert [item["file_name"] for item in files] == [
        "交易数据.xlsx",
        "加氢枪数据.xlsx",
        "压缩机数据.xlsx",
    ]
    probes = report["api_evidence"]["raw_file_probes"]
    assert len(probes) == 3
    assert all(probe["response"]["code"] == 403 for probe in probes)
    assert all("数据申请" in probe["response"]["message"] for probe in probes)
