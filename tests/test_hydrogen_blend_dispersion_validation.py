from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from h2station.hydrogen_blend_dispersion_validation import (
    BLEND_CASES,
    RELEASE_CASES,
    evaluate_archive,
)


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/hydrogen_blend_dispersion_holdout_protocol_2026_10_08.json"


def _write(path: Path, scale: float, labelled: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["distance_m", "hydrogen_concentration"] if labelled else ["x", "value"])
        for index in range(1, 8):
            writer.writerow([index, scale * index])


def test_synthetic_monotonic_archive_passes_both_frozen_screens(tmp_path: Path):
    for index, name in enumerate(BLEND_CASES, start=1):
        _write(tmp_path / name, float(index))
    for index, name in enumerate(RELEASE_CASES, start=1):
        _write(tmp_path / name, float(index), labelled=False)
    result = evaluate_archive(tmp_path)
    assert result["joint_primary_screen_pass"] is True
    assert result["screens"]["blend_fraction"]["spearman"] == pytest.approx(1.0)
    assert result["screens"]["release_volume"]["strictly_increasing"] is True


def test_non_monotonic_response_is_retained_as_failure(tmp_path: Path):
    for scale, name in zip((1.0, 3.0, 2.0), BLEND_CASES):
        _write(tmp_path / name, scale)
    for index, name in enumerate(RELEASE_CASES, start=1):
        _write(tmp_path / name, float(index))
    result = evaluate_archive(tmp_path)
    assert result["joint_primary_screen_pass"] is False
    assert result["screens"]["blend_fraction"]["pass_screen"] is False


def test_headerless_utf16_tab_rows_use_frozen_coordinate_fallback(tmp_path: Path):
    path = tmp_path / "hydrogenAll10%.csv"
    path.write_text("0\t1\t2\n1\t2\t4\n2\t3\t6\n", encoding="utf-16")
    from h2station.hydrogen_blend_dispersion_validation import extract_case_response

    case = extract_case_response(path, 10.0)
    assert case.finite_response_count == 6
    assert case.extraction_mode == "fallback_exclude_first_numeric_coordinate_column"


def test_protocol_declares_pre_access_state_and_bounded_claim():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["status"] == "FROZEN_BEFORE_NUMERIC_ARCHIVE_DOWNLOAD"
    assert protocol["prior_access"]["numeric_archive_downloaded"] is False
    assert protocol["aggregate_decision"]["retain_failures"] is True
    assert "does not validate absolute" in protocol["claim_boundary"]


def test_archived_result_retains_negative_outcome_and_format_disclosure():
    result_path = ROOT / "research/hydrogen_blend_dispersion_holdout_result_2026_10_08.json"
    if not result_path.is_file():
        pytest.skip("holdout result not archived yet")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    integrity = result["execution_integrity"]
    assert result["claim_supported"] is False
    assert result["evaluation"]["joint_primary_screen_pass"] is False
    assert integrity["classification"] == (
        "PROSPECTIVE_ENDPOINTS_POST_ACCESS_FORMAT_REPAIR"
    )
    assert integrity["locked_module_byte_identical"] is False
    assert integrity["endpoint_or_threshold_changed"] is False
    assert integrity["case_selection_changed"] is False
