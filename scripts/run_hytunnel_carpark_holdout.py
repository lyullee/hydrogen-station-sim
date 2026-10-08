"""Run the frozen HyTunnel-CS car-park time-series holdout."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from h2station.hytunnel_carpark_validation import evaluate_directory


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
        "--output",
        type=Path,
        default=Path("research/hytunnel_carpark_holdout_result_2026_10_08.json"),
    )
    args = parser.parse_args()
    evaluation = evaluate_directory(args.data_directory)
    source_files = sorted(args.data_directory.glob("Exp*.mat"))
    payload = {
        "schema_version": 1,
        "artifact_type": "hytunnel_carpark_raw_timeseries_holdout",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "dataset_doi": "10.23642/USN.14405903",
            "article_doi": "10.3390/en14113008",
            "license": "CC BY 4.0",
            "version": "1.1",
            "raw_files_committed": False,
            "files": [
                {"name": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)}
                for path in source_files
            ],
        },
        "protocol_sha256": _sha256(args.protocol),
        "evaluation": evaluation,
        "claims": {
            "well_mixed_sensor_mean_transfer_supported": evaluation["dispersion"]["joint_screen_pass"],
            "local_real_gas_mass_flow_transfer_supported": evaluation["mass_flow"]["joint_screen_pass"],
        },
        "claim_boundary": (
            "The two claims are limited to sensor-array-mean concentration in a mechanically "
            "ventilated 60.8 m3 enclosure and local 0.5 mm blowdown mass flow from measured "
            "upstream pressure/temperature. They do not validate plume geometry, detector "
            "placement, the 3.86 m line transient, outdoor HRS dispersion, consequence "
            "distance, station controls or a complete station-to-vehicle loop."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
