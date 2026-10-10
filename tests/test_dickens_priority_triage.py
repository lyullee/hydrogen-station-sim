import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dickens_priority_triage_is_actionable_but_not_promoted() -> None:
    record = json.loads(
        (ROOT / "research/dickens_typeiii_priority_mechanism_triage_2026_10_11.json")
        .read_text(encoding="utf-8")
    )
    assert record["gate_id"] == "dickens_typeiii_prospective_validation"
    assert record["mechanism_screen"]["all_grid_cases_joint_screen_pass"] is True
    assert record["decision"]["promotion_allowed"] is False
    assert record["decision"]["runtime_model_changed"] is False
    assert set(record["source_semantics"]["missing_required_metadata"]) == {
        "experiment inlet nozzle internal diameter",
        "time-resolved inlet gas temperature",
    }
