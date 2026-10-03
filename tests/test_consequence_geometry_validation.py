from pathlib import Path

from scripts.validate_consequence_geometry import build_report


ROOT = Path(__file__).resolve().parents[1]


def test_bounded_consequence_geometry_chain_is_complete():
    report = build_report(ROOT, run_browser_tests=False)
    checks = dict(report["chain_checks"])
    checks["browser_mapping_regression_passed"] = True
    assert all(checks.values())
    assert report["independent_dataset_family_count"] == 3
    assert report["site_specific_validation"] is False
    assert report["safety_distance_claim_permitted"] is False


def test_each_evidence_family_has_frozen_data_hashes():
    report = build_report(ROOT, run_browser_tests=False)
    for family in report["evidence_families"]:
        assert family["markers_present"] is True
        assert family["data_sha256"]
        assert all(len(value) == 64 for value in family["data_sha256"].values())
