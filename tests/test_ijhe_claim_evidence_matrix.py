from __future__ import annotations

import json
from pathlib import Path

from scripts.build_ijhe_claim_evidence_matrix import ROWS, _sha256, build


ROOT = Path(__file__).resolve().parents[1]


def test_claim_matrix_is_a_bounded_projection_of_the_current_audit() -> None:
    audit_path = ROOT / "manuscript/ijhe_readiness_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    matrix = json.loads(
        (ROOT / "research/ijhe_claim_evidence_matrix_2026_10_11.json").read_text(
            encoding="utf-8"
        )
    )
    expected = build(audit, audit_sha256=_sha256(audit_path))
    # The evidence projection is deterministic; the generation timestamp is
    # intentionally refreshed each time the audit is rebuilt.
    assert {key: value for key, value in matrix.items() if key != "generated_at"} == {
        key: value for key, value in expected.items() if key != "generated_at"
    }
    assert len(matrix["rows"]) == len(ROWS) == 8
    status_by_id = {row["id"]: row["status"] for row in matrix["rows"]}
    assert status_by_id["tank_external_validation"] == "PASS"
    assert status_by_id["ignited_pressure_peaking_external_validation"] == "PASS"
    assert status_by_id["full_loop_external_validation"] == "OUT OF SCOPE"
    assert status_by_id["proust_independent_release_validation"] == "FAIL"
    assert matrix["paper_scope"].startswith("objective engineering")
