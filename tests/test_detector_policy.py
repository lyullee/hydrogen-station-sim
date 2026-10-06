from pathlib import Path

from h2station.detector_policy import load_public_detector_policy
from h2station.risk.runtime_backend import UnavailableHyRAMBackend
from h2station.scenario import ReferenceScenario, build_reference_scenario


ROOT = Path(__file__).resolve().parents[1]


def test_public_detector_replay_rule_is_loaded_without_case_fitting():
    policy = load_public_detector_policy(ROOT)
    assert policy.evidence_status == "PUBLIC_REPLAY_RULE_APPLIED"
    assert policy.source_artifact == "research/dispersion_detector_logic_validation.json"
    assert policy.source_doi == "10.23642/usn.26117989.v2"
    assert policy.alarm_threshold_volpct_h2 == 1.0
    assert policy.trip_threshold_volpct_h2 == 2.0
    assert policy.persistence_s == 0.5
    assert "does not validate outdoor station dispersion" in policy.claim_limit


def test_reference_safety_plc_uses_public_policy_and_keeps_default_model():
    built = build_reference_scenario(ReferenceScenario(duration_s=0.1), UnavailableHyRAMBackend())
    limits = built.simulator.safety_plc.limits
    assert limits.detector_policy_status == "PUBLIC_REPLAY_RULE_APPLIED"
    assert limits.detector_alarm_volume_fraction == 0.01
    assert limits.detector_trip_volume_fraction == 0.02
    assert limits.trip_persistence_s == 0.5
