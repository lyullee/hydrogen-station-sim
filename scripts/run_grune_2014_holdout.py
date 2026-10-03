"""Run the frozen Grune et al. (2014) pressure-decay holdout."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from h2station.grune_2014_validation import (
    evaluate_grune_2014_holdout,
    load_grune_2014_pressure_csv,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data", type=Path,
        default=Path("data/public_validation/derived/grune_2014_figure2.csv"),
    )
    parser.add_argument(
        "--protocol", type=Path,
        default=Path("research/grune_2014_holdout_protocol.json"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("research/grune_2014_holdout_result.json"),
    )
    args = parser.parse_args()
    result = evaluate_grune_2014_holdout(load_grune_2014_pressure_csv(args.data))
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": _sha256(args.protocol),
        "data_sha256": _sha256(args.data),
        "result": asdict(result),
        "claim_supported": result.joint_primary_screen_pass,
        "claim_boundary": (
            "One 20 MPa, 0.37 L, 4 mm pressure-decay trace; no flame, ignition, "
            "dispersion, radiation, station control or safety-distance claim."
        ),
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
