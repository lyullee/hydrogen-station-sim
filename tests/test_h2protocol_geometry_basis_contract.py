from __future__ import annotations

import pytest

from scripts.run_h2protocol_validation import (
    _effective_volume_multiplier_for_geometry_basis,
)


def test_capacity_eos_does_not_apply_legacy_volume_fit_twice() -> None:
    fit = {"effective_volume_multiplier": 1.052729261198358}

    assert _effective_volume_multiplier_for_geometry_basis(
        fit, "capacity_scaled"
    ) == pytest.approx(1.052729261198358)
    assert _effective_volume_multiplier_for_geometry_basis(
        fit, "capacity_eos"
    ) == pytest.approx(1.0)


def test_geometry_basis_contract_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="geometry_basis"):
        _effective_volume_multiplier_for_geometry_basis(
            {"effective_volume_multiplier": 1.0}, "unknown"
        )
