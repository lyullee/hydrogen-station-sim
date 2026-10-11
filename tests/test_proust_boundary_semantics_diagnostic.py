from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research" / "proust_release_boundary_semantics_diagnostic_2026_10_12.json"
PROTOCOL = ROOT / "research" / "proust_release_holdout_protocol.json"
DATA = ROOT / "data" / "public_validation" / "derived" / "proust_90mpa_release.csv"
RESULT = ROOT / "research" / "proust_release_holdout_result.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_proust_boundary_diagnostic_is_non_controlling_and_hash_locked():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["artifact_type"] == "proust_release_boundary_semantics_diagnostic"
    assert record["evidence_role"] == "post_outcome_diagnostic_only"
    assert record["claim_controlling"] is False
    assert record["parameter_fitting"] is False
    assert record["production_model_parameter_changed"] is False
    assert record["input_hashes"]["protocol_sha256"] == _sha256(PROTOCOL)
    assert record["input_hashes"]["data_sha256"] == _sha256(DATA)
    assert record["frozen_primary_result"]["sha256"] == _sha256(RESULT)
    assert record["frozen_primary_result"]["claim_supported"] is False


def test_proust_boundary_diagnostic_preserves_diameter_pattern():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    rows = record["series"]
    assert [row["nozzle_diameter_mm"] for row in rows] == [1.0, 2.0, 3.0]
    assert rows[0]["effective_cd_median"] > 1.0
    assert rows[1]["effective_cd_median"] < 0.8
    assert rows[2]["effective_cd_median"] < 0.8
    assert record["published_apparatus_semantics"]["unresolved_network_inputs"]
