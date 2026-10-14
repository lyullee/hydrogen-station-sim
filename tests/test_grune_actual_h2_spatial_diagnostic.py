from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from analyze_grune_ps_actual_h2_spatial import _profile_summary  # noqa: E402
from h2station.public_validation import (  # noqa: E402
    GruneVentilationPoint,
    GruneVentilationProfile,
)


def test_spatial_diagnostic_keeps_threshold_extents_descriptive() -> None:
    profile = GruneVentilationProfile(
        source_workbook="example.xlsx",
        sheet_name="1 mm 1g H2 W = 0",
        release_diameter_mm=1.0,
        nominal_release_g_s=1.0,
        wind_speed_m_s=0.0,
        wind_mode="no-wind",
        points=(
            GruneVentilationPoint(0.0, 0.0, 0.1, 0.1, 0.1, 1.0, 20.0, 1.0, 1.0),
            GruneVentilationPoint(0.1, 0.2, 4.5, 4.5, 4.5, 1.0, 20.0, 1.0, 1.0),
        ),
    )

    summary = _profile_summary(profile)
    threshold = summary["thresholds"]["4.0"]
    assert threshold["point_count_at_or_above_threshold"] == 1
    assert threshold["x_min_mm"] == 0.1
    assert threshold["y_max_mm"] == 0.2
    assert threshold["coordinate_extent_is_descriptive"] is True
