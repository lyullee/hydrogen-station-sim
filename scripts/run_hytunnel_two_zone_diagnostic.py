"""Run the post-outcome HyTunnel two-zone transport diagnostic.

This intentionally produces a separate artifact and never overwrites the
frozen holdout result or readiness gate.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from h2station.hytunnel_carpark_validation import DISPERSION_CASES
from h2station.hytunnel_two_zone_diagnostic import evaluate_directory


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
        default=Path("research/hytunnel_carpark_holdout_protocol_2026_10_08.json"),
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("research/hytunnel_carpark_holdout_result_2026_10_08.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/hytunnel_two_zone_diagnostic_2026_10_11.json"),
    )
    args = parser.parse_args()
    source_files = sorted(args.data_directory.glob("Exp*.mat"))
    evaluation = evaluate_directory(args.data_directory, experiments=DISPERSION_CASES)
    payload = {
        "schema_version": 1,
        "artifact_type": "hytunnel_carpark_post_outcome_two_zone_diagnostic",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "post_outcome_diagnostic": True,
        "source": {
            "dataset_doi": "10.23642/USN.14405903",
            "article_doi": "10.3390/en14113008",
            "license": "CC BY 4.0",
            "raw_files_committed": False,
            "file_count": len(source_files),
            "files": [
                {"name": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)}
                for path in source_files
            ],
        },
        "protocol_reference": str(args.protocol).replace("\\", "/"),
        "protocol_sha256": _sha256(args.protocol),
        "baseline_reference": str(args.baseline).replace("\\", "/"),
        "model_boundary": {
            "name": "geometry_declared_two_zone_source_to_vent_transport",
            "source_zone": "published 5 m source-to-vent-wall distance divided by 40 ft enclosure length",
            "exchange": "ventilation volumetric flow transports source-zone gas to bulk zone and bulk gas to exhaust",
            "initial_condition": "measured array mean at first retained post-release sample in both zones",
            "case_specific_fitting": False,
            "time_shift": False,
            "sensor_subset_selection": False,
            "runtime_parameter_application": False,
            "frozen_gate_effect": "none",
        },
        "evaluation": evaluation,
        "claim_boundary": (
            "Post-outcome development diagnostic only. The public archive lacks an authoritative "
            "sensor-coordinate crosswalk, so this does not validate local plume geometry, detector "
            "placement, outdoor HRS dispersion, consequence distance, station controls or a complete "
            "station-to-vehicle loop. It must not replace the frozen holdout result."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
