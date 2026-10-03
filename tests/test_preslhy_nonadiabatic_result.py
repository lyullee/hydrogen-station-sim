from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research" / "preslhy_nonadiabatic_development_result.json"


def test_nonadiabatic_result_is_explicitly_development_only():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["evidence_role"] == "consumed_development_data_not_external_validation"
    assert result["claim_prohibited"] is True
    assert result["aggregate"]["cases"] == 22
    assert result["aggregate"]["joint_primary_passes"] == 20
    assert not result["errors"]


def test_nonadiabatic_result_hashes_match_archived_implementation():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    implementation = result["implementation"]
    assert hashlib.sha256(
        (ROOT / implementation["module"]).read_bytes()
    ).hexdigest() == implementation["sha256"]
    assert hashlib.sha256(
        (ROOT / implementation["runner"]).read_bytes()
    ).hexdigest() == implementation["runner_sha256"]
