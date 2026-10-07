"""Create private and public-safe custodian review artifacts from a mapping."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from h2station.restricted_attestation_review import write_restricted_attestation_review

from calibrate_confidential_station_data import _mapping


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an unconfirmed, privacy-safe channel attestation review."
    )
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--private-draft", type=Path, required=True)
    parser.add_argument("--private-markdown", type=Path, required=True)
    parser.add_argument("--public-status", type=Path, required=True)
    args = parser.parse_args()
    write_restricted_attestation_review(
        _mapping(args.mapping),
        mapping_path=args.mapping,
        profile_id=args.profile_id,
        private_draft_path=args.private_draft,
        private_markdown_path=args.private_markdown,
        public_status_path=args.public_status,
    )
    print(args.private_draft)
    print(args.private_markdown)
    print(args.public_status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
