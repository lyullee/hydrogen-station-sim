"""Run the prospectively frozen Proust 90 MPa release validation."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from h2station.proust_release_validation import evaluate_series, load_digitized_points


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data", type=Path,
        default=Path("data/public_validation/derived/proust_90mpa_release.csv"),
    )
    parser.add_argument(
        "--protocol", type=Path,
        default=Path("research/proust_release_holdout_protocol.json"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/public_validation/results/proust_release_holdout.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    for item in protocol["locked_implementation"].values():
        if _sha256(root / item["path"]) != item["sha256"]:
            raise RuntimeError(f"locked implementation changed: {item['path']}")

    groups = defaultdict(list)
    for point in load_digitized_points(args.data):
        groups[(point.case_id, point.nozzle_diameter_mm)].append(point)
    results, retained_failures = [], []
    for key, points in sorted(groups.items()):
        try:
            results.append(asdict(evaluate_series(points)))
        except Exception as exc:
            retained_failures.append({
                "case_id": key[0],
                "nozzle_diameter_mm": key[1],
                "points": len(points),
                "evaluation_error": f"{type(exc).__name__}: {exc}",
                "joint_primary_screen_pass": False,
            })
    all_results = results + retained_failures
    diameters = sorted({item["nozzle_diameter_mm"] for item in all_results})
    passes = sum(bool(item["joint_primary_screen_pass"]) for item in all_results)
    minimum_met = len(all_results) >= 3 and len(diameters) >= 3
    pass_fraction = passes / len(all_results) if all_results else None
    claim_supported = bool(
        minimum_met and pass_fraction is not None and pass_fraction >= 2 / 3
    )
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": _sha256(args.protocol),
        "data_sha256": _sha256(args.data),
        "aggregate": {
            "series": len(all_results),
            "diameter_groups": diameters,
            "joint_primary_passes": passes,
            "joint_primary_pass_fraction": pass_fraction,
            "minimum_requirements_met": minimum_met,
            "claim_supported": claim_supported,
        },
        "series": results,
        "retained_failures": retained_failures,
        "claim_boundary": protocol["claim_boundary"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

