from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from h2station.prospective_spatial_rank import (
    FROZEN_PARAMETERS,
    prospective_spatial_rank_metadata,
    prospective_spatial_rank_score,
)
from h2station.spatial_detector import Point3D


ROOT = Path(__file__).resolve().parents[1]
DEVELOPMENT = ROOT / "research/pooled_spatial_rank_development_2026_10_13.json"
PROTOCOL = ROOT / "research/prospective_spatial_rank_protocol_2026_10_13.json"
MODULE = ROOT / "src/h2station/prospective_spatial_rank.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_frozen_rank_is_positive_and_orders_distance_and_elevation() -> None:
    source = Point3D(0.0, 0.0, 0.0)
    near = prospective_spatial_rank_score(source, Point3D(1.0, 0.0, 0.0))
    far = prospective_spatial_rank_score(source, Point3D(5.0, 0.0, 0.0))
    above = prospective_spatial_rank_score(source, Point3D(1.0, 1.0, 0.0))
    below = prospective_spatial_rank_score(source, Point3D(1.0, -1.0, 0.0))
    assert near > far > 0.0
    assert above > below > 0.0


@pytest.mark.parametrize(
    "source,detector",
    [
        (Point3D(math.nan, 0.0, 0.0), Point3D(0.0, 0.0, 0.0)),
        (Point3D(0.0, 0.0, 0.0), Point3D(math.inf, 0.0, 0.0)),
    ],
)
def test_frozen_rank_rejects_nonfinite_coordinates(source: Point3D, detector: Point3D) -> None:
    with pytest.raises(ValueError, match="coordinates must be finite"):
        prospective_spatial_rank_score(source, detector)


def test_metadata_forbids_runtime_and_quantitative_claims() -> None:
    metadata = prospective_spatial_rank_metadata()
    assert metadata["status"] == "POST_OUTCOME_DEVELOPMENT_ONLY_NOT_RUNTIME"
    assert metadata["vertical_axis"] == "y"
    assert "runtime detector routing" in metadata["prohibited_uses"]
    assert "hydrogen concentration prediction" in metadata["prohibited_uses"]
    assert FROZEN_PARAMETERS.horizontal_distance_power == 1.25


def test_pooled_development_retains_failed_transfer_screen() -> None:
    record = json.loads(DEVELOPMENT.read_text(encoding="utf-8"))
    selected = record["selection"]["selected"]
    assert record["status"] == "DEVELOPMENT_ONLY_NOT_VALIDATION"
    assert record["selection"]["candidate_count"] == 15120
    assert selected["parameters"] == [0.3, 0.1, 0.2, 1.0, 1.25]
    assert selected["hytunnel_actual_hydrogen"]["joint_pass"] is True
    assert selected["h2safe_helium"]["joint_pass"] is False
    assert selected["h2safe_helium"]["screens"][
        "nearest_in_response_quartile_fraction_at_least_0_7"
    ] is False
    assert selected["both_cohorts_joint_pass"] is False
    assert record["decision"]["runtime_application"] is False
    assert record["decision"]["readiness_gate_effect"] == "none"
    assert record["implementation"]["sha256"] == _sha256(MODULE)


def test_future_protocol_locks_implementation_and_all_or_nothing_decision() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    assert protocol["candidate"]["implementation_sha256"] == _sha256(MODULE)
    assert protocol["candidate"]["parameters"] == [0.3, 0.1, 0.2, 1.0, 1.25]
    assert protocol["future_holdout"]["outcomes_accessed"] is False
    assert protocol["future_holdout"]["required_test_gas"] == "hydrogen"
    assert protocol["decision_rule"]["all_screens_must_pass"] is True
    assert protocol["decision_rule"]["parameter_tuning_after_access_permitted"] is False
    assert protocol["runtime_policy"]["enabled"] is False


def test_runtime_modules_do_not_import_prospective_candidate() -> None:
    for relative in ("src/h2station/api.py", "src/h2station/hazop/runtime.py"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "prospective_spatial_rank" not in text
