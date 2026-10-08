from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_h2protocol_validation import equivalent_capsule_geometry, main  # noqa: E402


def test_equivalent_capsule_geometry_preserves_declared_volume() -> None:
    volume_m3 = 0.117
    aspect_ratio = 5.0

    diameter_m, cylindrical_length_m = equivalent_capsule_geometry(
        volume_m3,
        aspect_ratio,
    )

    reconstructed = (
        math.pi * diameter_m**2 * cylindrical_length_m / 4.0
        + math.pi * diameter_m**3 / 6.0
    )
    assert reconstructed == pytest.approx(volume_m3, rel=1.0e-12)
    assert cylindrical_length_m / diameter_m == pytest.approx(aspect_ratio)


@pytest.mark.parametrize("volume,aspect", [(0.0, 5.0), (0.1, 0.0), (-0.1, 5.0)])
def test_equivalent_capsule_geometry_rejects_nonphysical_inputs(
    volume: float,
    aspect: float,
) -> None:
    with pytest.raises(ValueError):
        equivalent_capsule_geometry(volume, aspect)


def test_mixed_convection_cli_requires_declared_geometry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_h2protocol_validation.py", "--vehicle-tank-thermal-model", "mixed_convection"],
    )
    with pytest.raises(SystemExit, match="requires --vehicle-equivalent"):
        main()


def test_constant_ua_cli_rejects_mixed_convection_geometry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_h2protocol_validation.py",
            "--vehicle-equivalent-capsule-aspect-ratio",
            "5",
        ],
    )
    with pytest.raises(SystemExit, match="require --vehicle-tank-thermal-model"):
        main()


def test_committed_mixed_convection_diagnostic_is_claim_bounded() -> None:
    record = json.loads(
        (ROOT / "research/closed_loop_mixed_convection_diagnostic_2026_10_08.json")
        .read_text(encoding="utf-8")
    )

    assert record["post_outcome"] is True
    assert record["parameter_fitting"] is False
    assert record["production_default_changed"] is False
    assert record["validation_gate_effect"] == "none"
    assert record["mixed_convection"]["screening_pass_count"] == 2
    assert record["baseline"]["screening_pass_count"] == 2
    result_path = ROOT / record["mixed_convection"]["artifact"]
    assert hashlib.sha256(result_path.read_bytes()).hexdigest() == record["result_sha256"]
    assert all(
        change < 0.0
        for change in record["absolute_change_mixed_minus_baseline"].values()
    )
    boundary = record["claim_boundary"].lower()
    assert "cannot revise" in boundary
    assert "cannot" in boundary
