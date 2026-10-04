import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from intake_external_hrs_bundle import build_manifest  # noqa: E402


def test_intake_manifest_hashes_bytes_without_parsing_measurements(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "fill.csv").write_text(
        "time,vehicle_pressure,flow\n0,5.0,0.0\n", encoding="utf-8"
    )
    protocol = tmp_path / "protocol.json"
    protocol.write_text(
        json.dumps(
            {
                "status": "prospective_intake_contract",
                "outcomes_accessed_before_freeze": False,
                "claim_boundary": "manifest only",
            }
        ),
        encoding="utf-8",
    )
    manifest = build_manifest(bundle, protocol)
    assert manifest["file_count"] == 1
    assert manifest["numerical_values_inspected"] is False
    assert manifest["archive_members_parsed"] is False
    assert manifest["files"][0]["relative_path"] == "fill.csv"
    assert len(manifest["files"][0]["sha256"]) == 64


def test_intake_rejects_nonprospective_protocol(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("time,value\n0,1\n", encoding="utf-8")
    protocol = tmp_path / "protocol.json"
    protocol.write_text(
        json.dumps(
            {
                "status": "post_outcome_development_diagnostic",
                "outcomes_accessed_before_freeze": True,
                "claim_boundary": "diagnostic",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="prospective_intake_contract"):
        build_manifest(source, protocol)
