from __future__ import annotations

import json
from pathlib import Path

from scripts.evaluate_confidential_component_bundle import evaluate_bundle
from scripts.export_confidential_component_bundle import export_component_bundle
from tests.test_confidential_component_bundle import _write_fixture


ROOT = Path(__file__).resolve().parents[1]


def test_component_bundle_replay_is_bounded_and_runs_runtime(tmp_path: Path) -> None:
    inputs, mapping, attestation = _write_fixture(tmp_path)
    bundle = tmp_path / "bundle"
    export_component_bundle(
        inputs, mapping, attestation, bundle,
        ROOT / "research/external_hrs_component_intake_protocol.json",
    )
    result = evaluate_bundle(bundle, tmp_path / "replay.json")
    assert result["artifact_type"] == "controlled_component_bundle_replay_diagnostic"
    assert result["decision"] == "COMPONENT_REPLAY_DIAGNOSTIC_PASS"
    assert result["event_count"] == 3
    assert result["envelope_pass"] is True
    assert result["runtime_replay_pass"] is True
    assert result["predictive_validation"] is False
    assert result["full_loop_holdout_eligible"] is False
    assert result["source_identifiers_published"] is False


def test_component_bundle_replay_rejects_repo_output(tmp_path: Path) -> None:
    inputs, mapping, attestation = _write_fixture(tmp_path)
    bundle = tmp_path / "bundle"
    export_component_bundle(
        inputs, mapping, attestation, bundle,
        ROOT / "research/external_hrs_component_intake_protocol.json",
    )
    try:
        evaluate_bundle(bundle, ROOT / "replay.json")
    except ValueError as exc:
        assert "outside the repository" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("repository output must be rejected")
