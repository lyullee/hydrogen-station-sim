from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / 'research/ethics_and_expert_review_scope_decision_2026_10_11.json'


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
