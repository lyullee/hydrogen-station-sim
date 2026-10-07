from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_public_tank_runtime_calibration import build_record  # noqa: E402


def test_public_tank_runtime_audit_keeps_the_component_scope_and_runtime_link():
    record = build_record(ROOT)

    assert record["artifact_type"] == "public_type_iv_tank_runtime_calibration_audit"
    assert record["raw_experimental_rows_persisted"] is False
    assert record["source_workbook_names_persisted"] is False
    assert record["runtime_match"] is True
    assert record["runtime"]["api_default_mode"] == "public_type_iv"
    assert record["runtime"]["validation_case_count"] == 12
    assert record["recheck"]["matches_frozen_expected_result"] is True
    assert "does not validate a station-to-vehicle controller" in record["claim_boundary"]
    assert len(record["source_hashes"]) == 6
