from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / 'research/confidential_validation_split_manifest_2026_10_11.json'


def test_confidential_validation_split_manifest_is_privacy_bounded_and_claim_bounded():
    data = json.loads(ARTIFACT.read_text(encoding='utf-8'))
    assert data['artifact_type'] == 'confidential_validation_split_manifest'
    assert data['status'] == 'frozen_scope_manifest'
    assert all(value is False for value in data['privacy'].values())
    owner = data['owner_station_side_split']
    assert owner['deduplicated_rows'] == 56854143
    assert owner['fit_uses_holdout'] is False
    assert owner['default_model_parameters_changed_after_holdout'] is False
    cohorts = {item['id']: item for item in owner['cohorts']}
    assert cohorts['pressure_boundary']['holdout_points'] == 30
    assert cohorts['cascade_sequence']['holdout_pairs'] == 3664
    assert cohorts['recharge_pressure_forecast']['holdout_cases'] == 394
    public = data['public_component_split']
    assert public['holdout_cases'] == 12
    assert data['decision']['same_site_station_side_holdout_supported'] is True
    assert data['decision']['independent_external_full_loop_validation_supported'] is False
    assert data['station_to_vehicle_full_loop']['decision'].startswith('excluded')


def test_referenced_split_artifacts_match_frozen_hashes():
    data = json.loads(ARTIFACT.read_text(encoding='utf-8'))
    for relative, expected in data['integrity']['referenced_artifacts_sha256'].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
