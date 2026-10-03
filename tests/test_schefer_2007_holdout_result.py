from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research" / "schefer_2007_holdout_result.json"
PROTOCOL = ROOT / "research" / "schefer_2007_holdout_protocol.json"
DATA = ROOT / "data" / "public_validation" / "derived" / "schefer_2007_figure4.csv"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_schefer_2007_result_retains_negative_decision_and_hashes():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    observed = result["result"]
    assert result["protocol_sha256"] == _sha256(PROTOCOL)
    assert result["data_sha256"] == _sha256(DATA)
    assert observed["points"] == 222
    assert observed["nrmse_screen_pass"] is False
    assert observed["median_ape_screen_pass"] is False
    assert observed["half_pressure_time_screen_pass"] is True
    assert observed["joint_primary_screen_pass"] is False
    assert result["claim_supported"] is False
