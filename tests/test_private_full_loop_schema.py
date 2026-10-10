import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_private_full_loop_schema import audit  # noqa: E402


def test_private_schema_recheck_excludes_raw_content_and_repo(tmp_path):
    source = tmp_path / "preamble.csv"
    source.write_text(
        "export metadata,private station\n"
        "time,pressure,temperature,mass_flow,vehicle,cascade,status\n"
        "0,20,25,1,car-1,M,READY\n"
        "1,21,26,1.1,car-1,M,RUN\n",
        encoding="utf-8",
    )
    output = tmp_path / "receipt.json"
    report = audit(tmp_path, source_label="test-private")
    output.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    aggregate = report["aggregate"]
    assert aggregate["csv_files_seen"] == 1
    assert aggregate["files_with_all_required_full_loop_groups"] == 1
    # The broad inventory groups are intentionally insufficient for admission:
    # this fixture has no explicit dispenser-side temperature or vehicle-side
    # pressure column.
    assert aggregate["files_with_full_loop_contract_groups"] == 0
    assert "delivered_temperature" in aggregate["missing_full_loop_contract_groups"]
    assert "vehicle_pressure" in aggregate["missing_full_loop_contract_groups"]
    assert report["admission"]["full_loop_external_holdout_eligible"] is False
    serialized = output.read_text(encoding="utf-8")
    assert "preamble.csv" not in serialized
    assert "private station" not in serialized
    assert "car-1" not in serialized
    assert "0,20,25" not in serialized


def test_private_schema_recheck_rejects_repository_root():
    with pytest.raises(ValueError, match="outside the repository"):
        audit(ROOT, source_label="invalid")


def test_strict_contract_requires_station_and_vehicle_roles(tmp_path):
    source = tmp_path / "scoped.csv"
    source.write_text(
        "common_elapsed_s,vehicle_pressure,vehicle_temperature,dispenser_pressure,dispenser_temperature,mass_flow,cascade_bank,esd_status,vehicle_id\n"
        "0,5,24,70,20,1,M,READY,car-1\n",
        encoding="utf-8",
    )
    report = audit(tmp_path, source_label="strict-contract")
    aggregate = report["aggregate"]
    assert aggregate["files_with_full_loop_contract_groups"] == 1
    assert aggregate["missing_full_loop_contract_groups"] == []
