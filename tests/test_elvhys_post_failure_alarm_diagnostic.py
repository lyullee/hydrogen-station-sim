from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "research/elvhys_post_failure_alarm_diagnostic_2026_10_11.json"


def test_elvhys_post_failure_diagnostic_is_explicitly_bounded():
    record = json.loads(RESULT.read_text(encoding="utf-8"))
    assert record["status"] == "POST_OUTCOME_DIAGNOSTIC_ONLY"
    assert record["outcome_informed"] is True
    assert record["prospective_gate_changed"] is False
    assert record["runtime_parameter_application"] is False
    assert record["protocol"]["failed_case_id_retained"] == 44
    assert record["aggregate"]["replayed_case_count"] == 14
    assert record["aggregate"]["measured_signal_route_diagnostic_pass"] is True
    rendered = json.dumps(record, ensure_ascii=False)
    assert "C:\\" not in rendered
