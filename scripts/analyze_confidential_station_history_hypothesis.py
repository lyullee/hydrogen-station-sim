"""Create a privacy-safe aggregate from long confidential station histories."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from h2station.confidential_history_profile import analyze_confidential_history  # noqa: E402


def _outside_repository(path: Path, *, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return resolved
    raise ValueError(f"{label} must be outside the repository worktree")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-stride", type=int, default=600)
    parser.add_argument("--calibration-fraction", type=float, default=0.70)
    arguments = parser.parse_args()
    source = _outside_repository(arguments.input, label="input")
    mapping_path = _outside_repository(arguments.mapping, label="mapping")
    output = _outside_repository(arguments.output, label="output")
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    report = analyze_confidential_history(
        source,
        mapping,
        sample_stride=arguments.sample_stride,
        calibration_fraction=arguments.calibration_fraction,
    )
    report["mapping"] = {
        "mapping_sha256": _sha256(mapping_path),
        "contains_source_labels": False,
        "role_and_unit_attestation_is_explicit": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
