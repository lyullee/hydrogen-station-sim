from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hyddown_candidate_artifacts_are_fail_closed_for_external_validation() -> None:
    record = json.loads(
        (ROOT / "research/hyddown_public_artifact_boundary_2026_10_12.json").read_text(
            encoding="utf-8"
        )
    )
    assert record["source"]["source_commit"] == (
        "1040d758b819533451086baa5cf2a47b4292a22f"
    )
    assert record["decision"]["new_independent_public_holdout_found"] is False
    assert record["decision"]["runtime_parameter_changed"] is False
    assert record["decision"]["readiness_gate_promoted"] is False
    artifacts = {item["path"]: item for item in record["artifacts"]}
    assert artifacts["validation/rupture_history.csv"]["classification"] == (
        "simulation_output_non_hydrogen"
    )
    assert artifacts["validation/rupture_history_jet.csv"][
        "eligible_for_independent_hydrogen_validation"
    ] is False
    unisim = artifacts["validation/Unisim_Type_IV.csv"]
    assert unisim["classification"] == "commercial_simulator_cross_solver_output"
    assert unisim["eligible_for_cross_solver_diagnostic"] is True
    assert unisim["eligible_for_independent_hydrogen_validation"] is False
