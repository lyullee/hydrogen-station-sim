from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_h2safe_oedi_recheck_is_same_archive_and_not_a_new_holdout() -> None:
    record = json.loads(
        (ROOT / "research/h2safe_oedi_recheck_2026_10_12.json").read_text(
            encoding="utf-8-sig"
        )
    )
    download = record["download_recheck"]
    assert download["bytes"] == download["prior_bytes"]
    assert download["sha256"] == download["prior_sha256"]
    assert download["content_changed_since_prior_intake"] is False
    eligibility = record["eligibility_recheck"]
    assert eligibility["new_independent_holdout"] is False
    assert eligibility["station_to_vehicle_full_loop"] is False
    assert eligibility["runtime_parameter_application"] is False
    assert "timing crosswalk" in eligibility["reason"]
