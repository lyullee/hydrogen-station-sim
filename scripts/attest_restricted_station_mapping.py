"""Check a private station-map attestation without reading any measurement rows.

Both inputs remain in the controlled environment.  The output deliberately
contains only generic role families and booleans, so it can be reviewed before
being used beside a de-identified calibration aggregate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from h2station.restricted_attestation import load_restricted_channel_attestation

from calibrate_confidential_station_data import _mapping


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a restricted station channel-role attestation."
    )
    parser.add_argument("--mapping", type=Path, required=True, help="restricted raw-column map")
    parser.add_argument(
        "--attestation", type=Path, required=True,
        help="restricted generic-role/unit attestation JSON",
    )
    parser.add_argument("--output", type=Path, required=True, help="sanitized output JSON")
    args = parser.parse_args()

    checked = load_restricted_channel_attestation(args.attestation, _mapping(args.mapping))
    output = {
        "schema_version": 1,
        "artifact_type": "confidential_station_channel_attestation",
        **checked.to_public_dict(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
