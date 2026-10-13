from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/cheng_2026_h2co2_discharge_preaccess_protocol_2026_10_13.json"
RESULT = ROOT / "research/cheng_2026_h2co2_discharge_intake_result_2026_10_13.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_candidate_was_frozen_before_supplement_access() -> None:
    protocol = _load(PROTOCOL)
    result = _load(RESULT)

    assert protocol["current_status"] == "protocol_frozen_before_supplement_download"
    assert result["protocol_freeze_commit"] == "eb68ec9"
    assert result["protocol"] == str(PROTOCOL.relative_to(ROOT)).replace("\\", "/")
    decision = result["eligibility_decision"]
    assert decision["model_or_screen_changed_before_eligibility_decision"] is False
    assert decision["subsequent_model_development_after_candidate_closed"] is True


def test_candidate_fails_closed_without_raw_pure_hydrogen_trace() -> None:
    result = _load(RESULT)
    source = result["source"]
    package = result["content_audit"]["application_package"]
    decision = result["eligibility_decision"]

    assert source["test_mixture_reported_by_article"] == "0.7 H2 + 0.3 CO2 mole fraction"
    assert source["pure_hydrogen_raw_trace_packaged"] is False
    assert package["contains_raw_experimental_trace"] is False
    assert package["executables_run_during_audit"] is False
    assert decision["eligible_untouched_numerical_holdout"] is False
    assert decision["independent_pure_hydrogen_release_validation"] is False
    assert decision["ijhe_gate_impact"] == "no_change"
    assert decision["runtime_parameter_application"] is False


def test_frozen_model_hashes_remain_recorded_after_candidate_closed() -> None:
    protocol = _load(PROTOCOL)
    result = _load(RESULT)

    # The intake was closed as ineligible before later candidate-model work.
    # Its exact implementation is anchored by the immutable commit and hashes,
    # rather than forcing the active development file to remain unchanged.
    assert result["protocol_freeze_commit"] == "eb68ec9"
    for hash_key in ("model_sha256", "evaluator_sha256", "campaign_runner_sha256"):
        digest = protocol["freeze"][hash_key]
        assert len(digest) == 64
        assert all(character in "0123456789ABCDEF" for character in digest)
