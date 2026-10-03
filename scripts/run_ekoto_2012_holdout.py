"""Run the frozen Ekoto et al. (2012) release-flow holdout."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from h2station.ekoto_2012_validation import evaluate_ekoto_holdout, load_ekoto_flow_csv


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data", type=Path,
        default=Path("data/public_validation/raw/hyram-v6.1/tests/hyram/validation/data/ekoto-2012-fig3.csv"),
    )
    parser.add_argument(
        "--protocol", type=Path,
        default=Path("research/ekoto_2012_holdout_protocol.json"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("research/ekoto_2012_holdout_result.json"),
    )
    args = parser.parse_args()
    result = evaluate_ekoto_holdout(load_ekoto_flow_csv(args.data))
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": _sha256(args.protocol),
        "data_sha256": _sha256(args.data),
        "result": asdict(result),
        "claim_supported": result.joint_primary_screen_pass,
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
