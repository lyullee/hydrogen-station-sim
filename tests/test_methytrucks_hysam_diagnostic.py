from __future__ import annotations

import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def test_active_session_grouping_preserves_pulses_and_long_gaps():
    from scripts.analyze_methytrucks_hysam import active_sessions

    time_s = np.arange(12, dtype=float) * 10.0
    flow = np.asarray([0, 2, 2, 0, 0, 3, 3, 0, 0, 0, 4, 4], dtype=float)
    assert active_sessions(time_s, flow, join_gap_s=35.0) == [(1, 6), (10, 11)]


def test_methytrucks_result_keeps_post_access_claim_boundary_explicit():
    record = json.loads(
        (ROOT / "research/methytrucks_hysam_postaccess_diagnostic_2026_10_08.json")
        .read_text(encoding="utf-8")
    )
    assert record["status"] == "completed_post_access_external_diagnostic"
    assert record["source"]["dataset_doi"] == "10.5281/zenodo.20590842"
    assert record["source"]["dataset_license"] == "CC BY 4.0"
    assert record["access_integrity"]["all_expected_sha256_match"] is True
    assert record["access_integrity"]["raw_rows_committed"] is False
    assert record["access_integrity"]["parameter_fitting_performed"] is False
    assert len(record["workbooks"]) == 3
    assert all(item["sampling_interval_s"] == 0.5 for item in record["workbooks"])
    replay = record["candidate_tank_replay"]
    assert 0.9 < replay["mass_boundary"]["flow_to_scale_mass_ratio"] < 1.2
    assert replay["fit"]["case_specific_fitting"] is False
    assert record["eligibility"]["component_diagnostic_eligible"] is True
    assert record["eligibility"]["prospective_holdout_eligible"] is False
    assert record["eligibility"]["quantitative_full_loop_validation_eligible"] is False
    assert "not an untouched holdout" in record["claim_boundary"]
