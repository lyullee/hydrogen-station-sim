import json
from pathlib import Path

import pytest

from h2station.dispersion_proxy import concentration_volpct, load_public_dispersion_proxy


ROOT = Path(__file__).resolve().parents[1]


def test_public_dispersion_proxy_artifact_is_loaded_with_provenance():
    policy = load_public_dispersion_proxy(ROOT)
    assert policy.status == "PUBLIC_DISPERSION_PROXY_APPLIED"
    assert policy.source_doi == "10.23642/usn.26117989.v2"
    assert policy.source_license == "CC BY 4.0"
    assert policy.case_count == 22
    assert policy.coefficient_volpct_per_g_s == pytest.approx(28.449493830243835)


def test_public_dispersion_proxy_scales_small_release_without_instant_saturation():
    value = concentration_volpct(0.1)
    assert value == pytest.approx(2.8449493830243835)
    assert value < 100.0
    assert concentration_volpct(10.0) == 100.0
    assert concentration_volpct(0.0) == 0.0


def test_proxy_artifact_records_claim_boundary_and_case_statistics():
    record = json.loads(
        (ROOT / "research/dispersion_concentration_proxy_calibration_2026_10_06.json")
        .read_text(encoding="utf-8")
    )
    assert record["status"] == "derived_bounded_dispersion_concentration_proxy"
    assert record["source"]["case_count"] == 22
    assert len(record["cases"]) == 22
    assert "does not validate outdoor station dispersion" in record["claim_boundary"]
