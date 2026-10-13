from __future__ import annotations

import pytest

from scripts.archive_preslhy_blowdown_result import archive_result


def test_archive_rejects_post_outcome_diagnostic() -> None:
    validation = {
        "packages": [
            {"name": "PRE3P1A_KIT_D05_300K_DATA.zip"},
            {"name": "PRE3P1A_KIT_D1_300K_DATA.zip"},
            {"name": "PRE3P1A_KIT_D2_300K_DATA.zip"},
            {"name": "PRE3P1A_KIT_D4_300K_DATA.zip"},
        ],
        "protocol_sha256": "protocol-hash",
        "evidence_role": "post_outcome_development_diagnostic_only",
        "freeze_integrity": {"matches_frozen_model": False},
    }
    protocol = {"source": {"outcomes_accessed_before_freeze": False}}

    with pytest.raises(RuntimeError, match="not from the prospectively frozen model"):
        archive_result(validation, protocol, "protocol-hash")
