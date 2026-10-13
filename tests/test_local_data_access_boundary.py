from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_local_data_inventory_is_explicitly_non_numeric() -> None:
    record = json.loads(
        (ROOT / "research/local_data_access_boundary_2026_10_14.json").read_text(
            encoding="utf-8"
        )
    )
    inventory = record["inventory"]
    assert inventory["file_count"] == 85
    assert inventory["numeric_trace_extensions_found"] == []
    assert inventory["by_extension"] == {
        ".jpg": 54,
        ".mp4": 29,
        ".pdf": 1,
        ".hwpx": 1,
    }
    assert "independent pressure-time validation" in record["evidence_boundary"][
        "does_not_support"
    ]
