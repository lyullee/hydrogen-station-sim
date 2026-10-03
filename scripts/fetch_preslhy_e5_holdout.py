"""Resumably fetch the CC-BY-SA PRESLHY E5.1 holdout archive."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

import httpx


DATASET_ID = "uzDLoVtvVFILFwGQ"
LANDING_URL = f"https://radar.kit.edu/radar/en/dataset/{DATASET_ID}"
ARCHIVE_URL = (
    f"https://radar.kit.edu/radar-backend/archives/{DATASET_ID}/versions/1/content"
)
EXPECTED_BYTES = 484_896_768
EXPECTED_MD5 = "e7f7816a6d710101cb9c73694cafe899"


def _accept_download_terms(client: httpx.Client) -> None:
    response = client.get(LANDING_URL)
    response.raise_for_status()
    token_match = re.search(r'<meta name="_csrf" content="([^"]+)"', response.text)
    header_match = re.search(
        r'<meta name="_csrf_header" content="([^"]+)"', response.text
    )
    if not token_match or not header_match:
        raise RuntimeError("RADAR CSRF metadata was not found")
    accepted = client.post(
        "https://radar.kit.edu/radar/ajax/acceptDownloadTc",
        headers={
            header_match.group(1): token_match.group(1),
            "X-Requested-With": "XMLHttpRequest",
            "Referer": LANDING_URL,
        },
    )
    accepted.raise_for_status()


def _md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/public_validation/raw/preslhy_e5_1"),
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    final = args.output / "PRESLHY_E5_1_ignited_discharge.tar"
    partial = final.with_suffix(".tar.part")
    if final.exists() and final.stat().st_size == EXPECTED_BYTES:
        actual_md5 = _md5(final)
        if actual_md5 == EXPECTED_MD5:
            print(f"verified existing {final}")
            return 0
        raise RuntimeError(f"existing archive MD5 mismatch: {actual_md5}")
    start = partial.stat().st_size if partial.exists() else 0
    if start > EXPECTED_BYTES:
        raise RuntimeError("partial archive is larger than the published archive")

    timeout = httpx.Timeout(connect=30.0, read=120.0, write=30.0, pool=30.0)
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        _accept_download_terms(client)
        headers = {"Referer": LANDING_URL}
        if start:
            headers["Range"] = f"bytes={start}-"
        with client.stream("GET", ARCHIVE_URL, headers=headers) as response:
            response.raise_for_status()
            if start and response.status_code != 206:
                raise RuntimeError("RADAR did not honour the resume range")
            content_range = response.headers.get("content-range", "")
            if start and not content_range.startswith(f"bytes {start}-"):
                raise RuntimeError(f"unexpected Content-Range: {content_range}")
            mode = "ab" if start else "wb"
            written = start
            next_report = ((written // (32 * 1024 * 1024)) + 1) * 32 * 1024 * 1024
            with partial.open(mode) as handle:
                for block in response.iter_bytes(1024 * 1024):
                    handle.write(block)
                    written += len(block)
                    if written >= next_report:
                        print(
                            f"downloaded {written / 1024 / 1024:.1f} / "
                            f"{EXPECTED_BYTES / 1024 / 1024:.1f} MiB",
                            flush=True,
                        )
                        next_report += 32 * 1024 * 1024
    if partial.stat().st_size != EXPECTED_BYTES:
        raise RuntimeError(
            f"archive size mismatch: {partial.stat().st_size} != {EXPECTED_BYTES}"
        )
    actual_md5 = _md5(partial)
    if actual_md5 != EXPECTED_MD5:
        raise RuntimeError(f"archive MD5 mismatch: {actual_md5} != {EXPECTED_MD5}")
    partial.replace(final)
    acquisition = {
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "source_url": ARCHIVE_URL,
        "landing_url": LANDING_URL,
        "doi": "10.35097/1258",
        "license": "CC-BY-SA-4.0",
        "bytes": final.stat().st_size,
        "md5": actual_md5,
        "published_md5": EXPECTED_MD5,
        "integrity_verified": True,
        "local_path": str(final),
    }
    (args.output / "acquisition_preslhy_e5_1.json").write_text(
        json.dumps(acquisition, indent=2) + "\n", encoding="utf-8"
    )
    print(final)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise
