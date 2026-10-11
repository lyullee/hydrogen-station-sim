from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / 'research/ethics_and_expert_review_scope_decision_2026_10_11.json'
APPLICABILITY = ROOT / 'research/ethics_applicability_decision_2026_10_11.json'


def test_ethics_and_expert_scope_keeps_human_effectiveness_claim_closed():
    data = json.loads(ARTIFACT.read_text(encoding='utf-8'))
    assert data['institutional_ethics_determination'] == 'PENDING'
    assert data['independent_expert_review_complete'] == 'PENDING'
    assert data['human_effectiveness_claim_permitted'] is False
    assert data['llm_as_judge_permitted'] is False
    protocol = data['frozen_expert_protocol']
    assert protocol['holdout_event_count'] == 24
    assert protocol['reviewer_count'] == 3
    assert protocol['reviewer_independence'] is True
    assert data['decision']['institutional_determination_required_before_human_rating'] is True
    assert data['decision']['expert_review_required_for_operator_effectiveness_claim'] is True


def test_ethics_applicability_record_does_not_fabricate_approval_or_human_effect():
    data = json.loads(APPLICABILITY.read_text(encoding='utf-8'))
    current = data['current_physics_study']
    assert current['human_participants'] is False
    assert current['claim_of_saga_human_safety_effect'] is False
    assert current['institutional_approval_claimed'] is False
    gate = data['ethics_gate']
    assert gate['required_for_current_physics_paper'] is False
    assert gate['required_before_human_effectiveness_claim'] is True
    assert gate['determination_id'] is None
    expert = data['independent_expert_review']
    assert expert['required_for_current_physics_paper'] is False
    assert expert['required_for_saga_human_safety_effect_claim'] is True
    assert expert['llm_as_judge'] is False
