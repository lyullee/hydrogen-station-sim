"""Run the prospectively frozen hydrogen-blend dispersion trend holdout."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

from h2station.hydrogen_blend_dispersion_validation import evaluate_archive


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("research/hydrogen_blend_dispersion_holdout_protocol_2026_10_08.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/hydrogen_blend_dispersion_holdout_result_2026_10_08.json"),
    )
    parser.add_argument(
        "--extract-directory",
        type=Path,
        default=Path("tmp/hydrogen_blend_dispersion_holdout"),
    )
    args = parser.parse_args()
    args.extract_directory.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.archive) as bundle:
        bundle.extractall(args.extract_directory)

    evaluation = evaluate_archive(args.extract_directory)
    payload = {
        "schema_version": 1,
        "artifact_type": "prospective_hydrogen_blend_dispersion_trend_holdout",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "doi": "10.17632/x8zkds4fyn.2",
            "license": "CC BY 4.0",
            "archive_sha256": _sha256(args.archive),
            "raw_archive_committed": False,
        },
        "protocol_sha256": _sha256(args.protocol),
        "evaluation": evaluation,
        "claim_supported": evaluation["joint_primary_screen_pass"],
        "claim_boundary": (
            "This holdout tests only whether public hydrogen-blend measurements "
            "preserve the pre-declared direction and rank of upper-tail response "
            "versus blend fraction and release volume. It does not validate absolute "
            "hydrogen concentration, outdoor HRS dispersion, detector placement, "
            "alarm setpoints, ESD, consequence distance or the complete station loop."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
