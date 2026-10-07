"""Record a privacy-safe recheck of the frozen public Type-IV tank result.

The script compares aggregate fit and held-out validation metrics only.  It
never copies source workbooks, time-series rows, or paths into the committed
record.  A match demonstrates reproducibility of the bounded tank component;
it is not a new station-to-vehicle validation result.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


FIT_KEYS = ("effective_volume_multiplier", "gas_liner_ua_multiplier")
METRIC_KEYS = (
    "pressure_rmse_mpa",
    "temperature_rmse_c",
    "soc_rmse_percentage_points",
)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a JSON object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aggregate(record: dict[str, Any]) -> dict[str, Any]:
    fit = record.get("fit") or {}
    validation = record.get("validation") or {}
    return {
        "fit": {key: float(fit[key]) for key in FIT_KEYS},
        "validation_case_count": int(validation["case_count"]),
        "validation_mean_metrics": {
            key: float(validation[key]["mean"])
            for key in METRIC_KEYS
        },
    }


def compare(expected: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    """Compare only deterministic derived values in two validation records."""

    expected_aggregate = _aggregate(expected)
    fresh_aggregate = _aggregate(fresh)
    differences: dict[str, dict[str, float | int]] = {}
    for section in ("fit", "validation_mean_metrics"):
        for key, expected_value in expected_aggregate[section].items():
            observed_value = fresh_aggregate[section][key]
            if abs(float(expected_value) - float(observed_value)) > 1.0e-10:
                differences[f"{section}.{key}"] = {
                    "expected": expected_value,
                    "fresh": observed_value,
                }
    if expected_aggregate["validation_case_count"] != fresh_aggregate["validation_case_count"]:
        differences["validation_case_count"] = {
            "expected": expected_aggregate["validation_case_count"],
            "fresh": fresh_aggregate["validation_case_count"],
        }
    return {
        "matches": not differences,
        "expected": expected_aggregate,
        "fresh": fresh_aggregate,
        "differences": differences,
    }


def build_record(
    expected_path: Path, fresh_path: Path, comparison: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "artifact_type": "public_type_iv_tank_validation_recheck",
        "rechecked_at": datetime.now(timezone.utc).isoformat(),
        "expected_artifact": expected_path.name,
        "expected_sha256": _sha256(expected_path),
        "fresh_result_sha256": _sha256(fresh_path),
        "raw_experimental_rows_persisted": False,
        "source_workbook_names_persisted": False,
        "comparison": comparison,
        "claim_boundary": (
            "A matching recheck supports reproducibility of the public Type-IV "
            "tank-only fit with measured mass-flow and inlet-temperature "
            "boundaries. It is not full station-to-vehicle validation, SAE "
            "protocol certification, field safety validation, or a vehicle "
            "certification result."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--expected", type=Path,
        default=Path("research/tank_model_validation_v2.json"),
    )
    parser.add_argument("--fresh", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path,
        default=Path("research/public_type_iv_tank_validation_recheck_2026_10_07.json"),
    )
    args = parser.parse_args()
    comparison = compare(_read(args.expected), _read(args.fresh))
    record = build_record(args.expected, args.fresh, comparison)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0 if comparison["matches"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
