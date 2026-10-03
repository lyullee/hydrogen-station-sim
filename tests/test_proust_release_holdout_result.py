from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research" / "proust_release_holdout_result.json"
PROTOCOL = ROOT / "research" / "proust_release_holdout_protocol.json"
DATA = ROOT / "data" / "public_validation" / "derived" / "proust_90mpa_release.csv"
EXTRACTION = ROOT / "data" / "public_validation" / "derived" / "proust_90mpa_extraction.json"
SENSITIVITY = ROOT / "research" / "proust_release_pressure_basis_sensitivity.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_proust_result_retains_all_series_and_negative_decision():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    aggregate = result["aggregate"]
    assert aggregate["series"] == 3
    assert aggregate["diameter_groups"] == [1.0, 2.0, 3.0]
    assert aggregate["joint_primary_passes"] == 0
    assert aggregate["minimum_requirements_met"] is True
    assert aggregate["claim_supported"] is False
    assert [item["points"] for item in result["series"]] == [13, 10, 12]


def test_proust_result_hashes_frozen_protocol_and_digitization_data():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    extraction = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    assert result["protocol_sha256"] == _sha256(PROTOCOL)
    assert result["data_sha256"] == _sha256(DATA)
    assert extraction["protocol_commit"] == "3fb8b91"
    assert extraction["source_pdf_committed"] is False
    assert extraction["protocol_committed_before_numerical_access"] is True


def test_pressure_basis_sensitivity_is_diagnostic_and_does_not_reverse_failures():
    sensitivity = json.loads(SENSITIVITY.read_text(encoding="utf-8"))
    assert sensitivity["claim_controlling"] is False
    assert all(
        not item["gauge_to_absolute_sensitivity"]["joint_primary_screen_pass"]
        for item in sensitivity["series"]
    )
