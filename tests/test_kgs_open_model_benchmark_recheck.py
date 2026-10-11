from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_kgs_benchmark_is_aggregate_context_only() -> None:
    record = json.loads(
        (ROOT / "research/kgs_open_model_benchmark_recheck_2026_10_12.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["reported_scope"]["real_world_scenarios"] == 6
    assert record["code_route"]["access_result"] == "HTTP_401_SIGN_IN_REQUIRED"
    assert record["code_route"]["raw_code_downloaded"] is False
    assert record["code_route"]["raw_rows_public"] is False
    assert record["eligibility"]["independent_raw_holdout"] is False
    assert record["eligibility"]["runtime_parameter_application"] is False
    assert record["eligibility"]["validation_gate_promoted"] is False
    assert record["decision"] == "PUBLISHED_AGGREGATE_CODE_ROUTE_NOT_HOLDOUT"
