from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_local_data_inventory_classifies_duplicate_numeric_trace() -> None:
    record = json.loads(
        (ROOT / "research/local_data_access_boundary_2026_10_14.json").read_text(
            encoding="utf-8"
        )
    )
    inventory = record["inventory"]
    assert inventory["file_count"] == 98
    assert inventory["numeric_trace_extensions_found"] == [".csv"]
    assert inventory["numeric_trace_files"] == [
        {
            "file_label": "USN_T00003/23_FFI_P101_T00003/23_FFI_P101_T00003.csv",
            "classification": "duplicate_of_retained_public_usn_archive",
            "duplicate_recheck": "research/ftpdata_usn_26117989_duplicate_recheck_2026_10_14.json",
            "new_independent_holdout": False,
        }
    ]
    assert inventory["by_extension"] == {
        ".csv": 1,
        ".hwpx": 1,
        ".jpeg": 4,
        ".jpg": 54,
        ".json": 3,
        ".md": 2,
        ".mp4": 29,
        ".pdf": 1,
        ".txt": 1,
        ".zip": 2,
    }
    assert "independent pressure-time validation" in record["evidence_boundary"][
        "does_not_support"
    ]
