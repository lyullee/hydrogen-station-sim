from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_controlled_multisource_review import build_review  # noqa: E402


def test_private_review_finds_complementary_workbook_without_reading_rows(tmp_path: Path):
    workbook_path = tmp_path / "private-workbook.xlsx"
    workbook = Workbook()
    vehicle = workbook.active
    vehicle.title = "secret vehicle"
    vehicle.append(["비공개 시간", "차량 압력", "차량 온도", "차량 유량"])
    vehicle.append(["do-not-read", 1, 2, 3])
    station = workbook.create_sheet("secret station")
    station.append(["시각", "저장탱크 압력", "운전 상태", "압축기"])
    station.append(["do-not-read", 4, "private", "private"])
    workbook.save(workbook_path)

    review = build_review([tmp_path])

    assert review["publication_prohibited"] is True
    assert review["repository_storage_prohibited"] is True
    assert review["sample_data_rows_structurally_inspected_in_memory"] is True
    assert review["measurement_values_persisted"] is False
    assert review["candidate_count"] == 1
    source = review["candidates"][0]
    assert source["review_status"] == "requires_custodian_mapping_and_synchronization_attestation"
    assert len(source["sources"]) == 2
