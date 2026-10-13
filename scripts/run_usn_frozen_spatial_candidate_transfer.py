"""Evaluate the frozen spatial-rank candidate on a third actual-H2 cohort.

The USN open-channel outcomes were inspected before the candidate was frozen,
so this is deliberately a post-access transfer diagnostic rather than an
independent or prospective validation.  The candidate coefficients are not
tuned here and the result has no runtime or readiness-gate effect.
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

from h2station.prospective_spatial_rank import (
    prospective_spatial_rank_metadata,
    prospective_spatial_rank_score,
)
from h2station.spatial_detector import Point3D
from run_usn_actual_h2_spatial_response_diagnostic import (
    _aggregate,
    _evaluate_member,
    _load_coordinates,
)


COORDINATE_ARTIFACT = (
    ROOT / "research/usn_open_channel_sensor_coordinates_2026_10_10.json"
)
PROTOCOL = ROOT / "research/prospective_spatial_rank_protocol_2026_10_13.json"
DEVELOPMENT = ROOT / "research/pooled_spatial_rank_development_2026_10_13.json"
IMPLEMENTATION = ROOT / "src/h2station/prospective_spatial_rank.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _candidate_score(
    source_xyz: tuple[float, float, float],
    detector_xyz: tuple[float, float, float],
) -> float:
    """Map USN ``z`` elevation to the candidate's declared ``y`` elevation."""

    source = Point3D(x=source_xyz[0], y=source_xyz[2], z=source_xyz[1])
    detector = Point3D(x=detector_xyz[0], y=detector_xyz[2], z=detector_xyz[1])
    return prospective_spatial_rank_score(source, detector)


def run(raw_dir: Path, coordinates_path: Path) -> dict[str, Any]:
    coordinates = _load_coordinates(coordinates_path)
    source = (0.45, 0.5, 0.8)
    archives = sorted(raw_dir.glob("*.zip"))
    cases = [
        _evaluate_member(
            archive,
            coordinates,
            source,
            model="pooled_spatial_rank_v1",
            score_function=_candidate_score,
        )
        for archive in archives
    ]
    aggregate = _aggregate(cases)
    development = json.loads(DEVELOPMENT.read_text(encoding="utf-8"))
    development_sources = development.get("sources") or {}
    dataset_doi = "10.23642/USN.26117989"
    included_in_parameter_search = any(
        str(item.get("dataset_doi") or "").lower() == dataset_doi.lower()
        for item in development_sources.values()
        if isinstance(item, dict)
    )
    return {
        "schema_version": 1,
        "artifact_type": "post_access_usn_frozen_spatial_candidate_transfer",
        "recorded_at": "2026-10-13",
        "source": {
            "dataset_doi": dataset_doi,
            "article_doi": "10.1016/j.jlp.2025.105669",
            "test_gas": "actual hydrogen",
            "archive_count": len(archives),
            "coordinates_artifact": str(coordinates_path.relative_to(ROOT)).replace(
                "\\", "/"
            ),
        },
        "candidate": {
            **prospective_spatial_rank_metadata(),
            "implementation_sha256": _sha256(IMPLEMENTATION),
            "protocol_sha256": _sha256(PROTOCOL),
            "development_artifact_sha256": _sha256(DEVELOPMENT),
            "parameter_tuning_in_this_evaluation": False,
            "dataset_included_in_parameter_search": included_in_parameter_search,
        },
        "coordinate_transform": {
            "dataset_frame": "x width, y streamwise distance from closed end, z height",
            "candidate_frame": "x horizontal, y elevation, z horizontal",
            "mapping": "candidate(x,y,z) = dataset(x,z,y)",
            "unit": "m",
            "source_origin_dataset_xyz_m": source,
        },
        "response": "per-sensor q99 minus q10 over the complete trace",
        "result": {"cases": cases, "aggregate": aggregate},
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
            "The fixed candidate is evaluated without coefficient tuning on a third "
            "actual-hydrogen cohort that was not included in the numerical parameter "
            "search. Because its outcomes had already been inspected before the freeze, "
            "this is a post-access transfer diagnostic, not independent or prospective "
            "validation. It does not validate concentration, alarm time, detector "
            "placement, CFD, ESD, safety distance, or station runtime behavior."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--coordinates", type=Path, default=COORDINATE_ARTIFACT)
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            ROOT
            / "research/usn_frozen_spatial_candidate_transfer_2026_10_13.json"
        ),
    )
    args = parser.parse_args()
    result = run(args.raw_dir.resolve(), args.coordinates.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "aggregate": result["result"]["aggregate"],
                "evidence_classification": result["evidence_classification"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
