"""Run the frozen HyTunnel actual-hydrogen spatial-rank holdout."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from h2station.hytunnel_spatial_validation import evaluate_spatial_directory


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-directory", type=Path, required=True)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("research/hytunnel_spatial_holdout_protocol_2026_10_08.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/hytunnel_spatial_holdout_result_2026_10_08.json"),
    )
    args = parser.parse_args()
    evaluation = evaluate_spatial_directory(args.data_directory)
    aggregate = evaluation.get("aggregate") or {}
    source_files = sorted(args.data_directory.glob("Exp*.mat"))
    payload = {
        "schema_version": 1,
        "artifact_type": "hytunnel_actual_hydrogen_spatial_rank_holdout",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "dataset_doi": "10.23642/USN.14405903",
            "article_doi": "10.3390/en14113008",
            "test_gas": "hydrogen",
            "license": "CC BY 4.0",
            "version": "1.1",
            "raw_files_committed": False,
            "files": [
                {
                    "name": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
                for path in source_files
            ],
        },
        "protocol_sha256": _sha256(args.protocol),
        "evaluation": evaluation,
        "decision": {
            "independent_spatial_validation_pass": (
                aggregate.get("joint_screen_pass") is True
            ),
            "runtime_candidate_enabled": False,
            "runtime_policy": (
                "Keep runtime routing disabled until the audit verifies the exact frozen "
                "candidate, complete case accounting and every joint screen."
            ),
        },
        "claim_boundary": (
            "This holdout tests only spatial rank transfer of the already frozen "
            "orientation-class candidate in one mechanically ventilated enclosure with "
            "a vertically downward source. It does not validate concentration amplitude, "
            "alarm thresholds, outdoor station placement, CFD, ESD, consequence distance "
            "or a complete station-to-vehicle loop."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
