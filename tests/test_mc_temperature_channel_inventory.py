from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_mc_temperature_channels import _stratification_summary  # noqa: E402


def test_stratification_summary_keeps_derived_metrics_aggregate_only() -> None:
    summary = _stratification_summary([
        {
            "individual_channel_spread_c": {
                "mean_c": 1.0, "median_c": 0.8, "p95_c": 2.0, "peak_c": 3.0,
            },
            "mean_to_reported_average_mae_c": 0.0,
        },
        {
            "individual_channel_spread_c": {
                "mean_c": 2.0, "median_c": 1.8, "p95_c": 4.0, "peak_c": 5.0,
            },
            "mean_to_reported_average_mae_c": None,
        },
    ])

    assert summary["cases_with_spread_metrics"] == 2
    assert summary["maximum_case_peak_spread_c"] == 5.0
    assert summary["reported_average_comparison_case_count"] == 1
    assert summary["reported_average_mae_mean_c"] == 0.0
