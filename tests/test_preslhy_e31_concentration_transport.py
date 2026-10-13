from pathlib import Path

from h2station.preslhy_e31_concentration_transport import (
    CONCENTRATION_CHANNELS,
    DOCUMENTED_TRANSPORT_DELAY_S,
    run_archive_diagnostic,
)


ROOT = Path(__file__).resolve().parents[1]


def test_e31_concentration_delay_diagnostic_is_bounded_and_complete():
    result = run_archive_diagnostic(ROOT / "data/public_validation/raw/preslhy")

    assert result["diagnostic_type"] == "POST_ACCESS_CONCENTRATION_TRANSPORT_DELAY_DIAGNOSTIC"
    assert result["runtime_promotion"] is False
    assert result["independent_validation_gate_impact"] == "none"
    assert result["archive_count"] == 6
    assert result["trace_count"] == 33
    assert result["error_count"] == 0
    assert result["source_description"]["concentration_channels"] == list(CONCENTRATION_CHANNELS)
    assert result["source_description"]["documented_transport_delay_s"] == DOCUMENTED_TRANSPORT_DELAY_S
    assert result["raw_onset_lag"]["count"] == 33 * len(CONCENTRATION_CHANNELS)
    assert result["corrected_onset_lag"]["count"] == result["raw_onset_lag"]["count"]

    for trace in result["traces"]:
        assert len(trace["sensors"]) == len(CONCENTRATION_CHANNELS)
        assert trace["samples"] >= 20
        for sensor in trace["sensors"]:
            assert sensor["corrected_onset_lag_s"] == (
                sensor["raw_onset_lag_s"] - DOCUMENTED_TRANSPORT_DELAY_S
            )


def test_e31_delay_diagnostic_reports_observed_timestamp_shift():
    result = run_archive_diagnostic(ROOT / "data/public_validation/raw/preslhy")

    raw = result["raw_onset_lag"]["median_s"]
    corrected = result["corrected_onset_lag"]["median_s"]
    assert raw is not None and corrected is not None
    assert abs((raw - corrected) - DOCUMENTED_TRANSPORT_DELAY_S) < 1e-9
