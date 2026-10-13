"""Run the post-access Liang et al. (2026) Table 2 release benchmark."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from h2station.liang_2026_release_benchmark import evaluate


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/public_validation/derived/liang_2026_table2.csv"),
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("research/liang_2026_release_benchmark_protocol.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/liang_2026_release_benchmark_2026_10_13.json"),
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    for item in protocol["locked_inputs"]:
        path = root / item["path"]
        if _sha256(path) != item["sha256"]:
            raise RuntimeError(f"locked input changed: {item['path']}")

    result = evaluate(args.data)
    result.update(
        {
            "schema_version": 1,
            "artifact_type": "liang_2026_release_postaccess_benchmark",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "protocol_sha256": _sha256(args.protocol),
            "data_sha256": _sha256(args.data),
            "locked_input_hashes_verified": True,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
