"""Reproduce the fixed spatial candidate on public Figshare H2 channel data.

The archive was opened by earlier repository diagnostics before this protocol
was written. This command is therefore a post-access transfer diagnostic, not
an independent holdout; it cannot change runtime routing or a readiness gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.prospective_spatial_rank import (  # noqa: E402
    prospective_spatial_rank_metadata,
    prospective_spatial_rank_score,
)
from h2station.spatial_detector import Point3D  # noqa: E402
from run_usn_actual_h2_spatial_response_diagnostic import (  # noqa: E402
    _aggregate,
    _evaluate_member,
    _load_coordinates,
)

PROTOCOL = ROOT / "research/figshare_h2_channel_spatial_holdout_protocol_2026_10_14.json"
COORDINATES = ROOT / "research/usn_open_channel_sensor_coordinates_2026_10_10.json"
IMPLEMENTATION = ROOT / "src/h2station/prospective_spatial_rank.py"
DATASET_DOI = "10.23642/usn.26117989.v2"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _candidate_score(source_xyz: tuple[float, float, float], detector_xyz: tuple[float, float, float]) -> float:
    source = Point3D(x=source_xyz[0], y=source_xyz[2], z=source_xyz[1])
    detector = Point3D(x=detector_xyz[0], y=detector_xyz[2], z=detector_xyz[1])
    return prospective_spatial_rank_score(source, detector)


def run(raw_dir: Path, coordinates_path: Path) -> dict[str, Any]:
    coordinates = _load_coordinates(coordinates_path)
    source = (0.45, 0.5, 0.8)
    archives = sorted(raw_dir.glob("23_FFI_P101_T*.zip"))
    cases = [
        _evaluate_member(
            archive, coordinates, source, model="pooled_spatial_rank_v1", score_function=_candidate_score
        )
        for archive in archives
    ]
    return {
        "schema_version": 1,
        "artifact_type": "figshare_h2_channel_spatial_post_access_transfer",
        "recorded_at": "2026-10-14",
        "source": {
            "dataset_doi": DATASET_DOI,
            "article_doi": "10.1016/j.jlp.2025.105669",
            "test_gas": "actual hydrogen",
            "archive_count": len(archives),
            "coordinates_artifact": str(coordinates_path.relative_to(ROOT)).replace("\\", "/"),
        },
        "candidate": {
            **prospective_spatial_rank_metadata(),
            "implementation_sha256": _sha256(IMPLEMENTATION),
            "protocol_sha256": _sha256(PROTOCOL),
            "parameter_tuning_in_this_evaluation": False,
            "outcomes_accessed_before_protocol_freeze": True,
        },
        "coordinate_transform": {
            "dataset_frame": "x width, y streamwise distance from closed end, z height",
            "candidate_frame": "x horizontal, y elevation, z horizontal",
            "mapping": "candidate(x,y,z) = dataset(x,z,y)",
            "unit": "m",
            "source_origin_dataset_xyz_m": source,
        },
        "response": "per-sensor q99 minus q10 over the complete trace",
        "result": {"cases": cases, "aggregate": _aggregate(cases)},
        "evidence_classification": {
            "outcomes_accessed_before_candidate_freeze": True,
            "human_outcome_independence": False,
            "independent_holdout": False,
            "prospective_validation": False,
            "transfer_diagnostic_only": True,
            "readiness_gate_effect": False,
            "runtime_parameter_application": False,
        },
        "claim_boundary": (
            "This is a reproducible post-access transfer diagnostic on an actual-hydrogen "
            "open-ended channel. It does not validate the station detector map, alarm or "
            "ESD setpoints, consequence distance, evacuation radius, or SAGA effectiveness, "
            "and cannot close the independent spatial-validation blocker."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--coordinates", type=Path, default=COORDINATES)
    parser.add_argument("--output", type=Path, default=ROOT / "research/figshare_h2_channel_spatial_holdout_result_2026_10_14.json")
    args = parser.parse_args()
    result = run(args.raw_dir.resolve(), args.coordinates.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(args.output), "aggregate": result["result"]["aggregate"], "evidence_classification": result["evidence_classification"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
