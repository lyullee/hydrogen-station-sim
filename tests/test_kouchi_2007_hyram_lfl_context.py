import json
from pathlib import Path

import pytest

from scripts.build_kouchi_2007_hyram_lfl_context import build


ROOT = Path(__file__).resolve().parents[1]


def test_committed_kouchi_hyram_context_matches_rebuild():
    expected = json.loads(
        (ROOT / "research/kouchi_2007_hyram_lfl_context_2026_10_14.json")
        .read_text(encoding="utf-8")
    )
    actual = build(ROOT)
    assert actual == expected
    assert actual["status"] == (
        "POST_ACCESS_SINGLE_POINT_PLAUSIBILITY_CONTEXT_NOT_VALIDATION"
    )
    assert actual["source"]["test_gas"] == "hydrogen"
    assert actual["source"]["reported_time_averaged_concentration_volpct"] == 4.1
    # HyRAM's DOPRI5 integration is deterministic within the small numerical
    # variation introduced by the supported SciPy releases.  This is a
    # single-point plausibility context, so millimetre-level precision is not
    # a meaningful acceptance criterion.
    assert actual["result"]["modeled_4volpct_streamline_distance_m"] == pytest.approx(
        0.91, abs=0.001
    )
    assert actual["result"]["relative_distance_difference_percent"] < 1.2
    assert actual["model"]["parameter_fitting_executed"] is False
    assert actual["interpretation"]["independent_validation"] is False
    assert actual["interpretation"]["runtime_parameter_application"] is False
    assert actual["interpretation"]["consequence_validation_gate_changed"] is False
