"""Fetch the KIT LH2 archive through RADAR's range-capable BagIt endpoint.

The script only transfers bytes and verifies the publisher digest. It does not
extract, parse, or inspect any archive member. The stage-1 protocol must still
be applied before opening outcome files.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import shutil
import urllib.request
from pathlib import Path


BASE = "https://www.radar-service.eu"
DATASET = "umUTdrjbbQCUDIXE"
EXPECTED_BYTES = 4_971_447_808
EXPECTED_MD5 = "0e4ac934ecb973c6f07212e8a80707c9"


def _session() -> tuple[urllib.request.OpenerDirector, dict[str, str]]:
    import http.cookiejar

    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    page = opener.open(
        f"{BASE}/radar/en/dataset/{DATASET}", timeout=60
    ).read()
    match = re.search(rb'<meta name="_csrf" content="([^"]+)"', page)
    if not match:
        raise RuntimeError("RADAR CSRF token not found")
    token = match.group(1).decode()
    headers = {"X-CSRF-TOKEN": token}
    with opener.open(
        urllib.request.Request(
            f"{BASE}/radar/ajax/acceptDownloadTc",
            data=b"",
            method="POST",
            headers=headers,
        ),
        timeout=60,
    ) as response:
        if response.status != 200:
            raise RuntimeError(f"download terms endpoint returned {response.status}")
    with opener.open(
        urllib.request.Request(
            f"{BASE}/radar/dataset/bagit/download/{DATASET}", headers=headers
        ),
        timeout=60,
    ) as response:
        download_url = json.loads(response.read())["downloadUrl"]
    cookie_header = "; ".join(f"{cookie.name}={cookie.value}" for cookie in jar)
    return opener, {
        **headers,
        "Accept-Encoding": "identity",
        "Download-URL": download_url,
        "Cookie": cookie_header,
    }


def _probe(opener: urllib.request.OpenerDirector, headers: dict[str, str]) -> int:
    url = headers["Download-URL"]
    request = urllib.request.Request(
        url, headers={key: value for key, value in headers.items() if key != "Download-URL"}
        | {"Range": "bytes=0-0"},
    )
    with opener.open(request, timeout=120) as response:
        if response.status != 206:
            raise RuntimeError(f"range probe returned {response.status}")
        content_range = response.headers.get("Content-Range", "")
        match = re.fullmatch(r"bytes 0-0/(\d+)", content_range)
        if not match:
            raise RuntimeError(f"unexpected Content-Range: {content_range!r}")
        response.read(1)
        return int(match.group(1))


def _download_range(
    url: str,
    headers: dict[str, str],
    start: int,
    end: int,
    destination: Path,
    retries: int,
) -> tuple[int, int]:
    request_headers = {
        key: value for key, value in headers.items() if key != "Download-URL"
    }
    request_headers["Range"] = f"bytes={start}-{end}"
    expected = end - start + 1
    last_error: Exception | None = None
    for _attempt in range(retries + 1):
        try:
            destination.unlink(missing_ok=True)
            request = urllib.request.Request(url, headers=request_headers)
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.status != 206:
                    raise RuntimeError(f"range {start}-{end} returned {response.status}")
                content_range = response.headers.get("Content-Range", "")
                if not content_range.startswith(f"bytes {start}-{end}/"):
                    raise RuntimeError(f"range mismatch for {start}-{end}: {content_range!r}")
                with destination.open("wb") as output:
                    copied = 0
                    while copied < expected:
                        block = response.read(min(8 * 1024 * 1024, expected - copied))
                        if not block:
                            break
                        output.write(block)
                        copied += len(block)
                if copied != expected:
                    raise RuntimeError(f"short range {start}-{end}: {copied}/{expected}")
                return start, copied
        except Exception as exc:  # pragma: no cover - network-dependent recovery
            last_error = exc
    raise RuntimeError(f"range {start}-{end} failed after retries: {last_error}")


def _md5_file(path: Path, block_bytes: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.md5()
    with path.open("rb") as source:
        while block := source.read(block_bytes):
            digest.update(block)
    return digest.hexdigest()


def _seed_existing_prefix(
    existing: Path,
    chunk_dir: Path,
    chunk_bytes: int,
    expected_md5: str | None,
) -> int:
    """Copy a verified, chunk-aligned prefix into the range cache.

    The archive is opaque at this stage: this function only hashes and copies
    bytes.  Refusing a non-aligned prefix prevents a partial final chunk from
    being mistaken for a complete HTTP range.
    """

    size = existing.stat().st_size
    if size == 0:
        return 0
    if size % chunk_bytes:
        raise RuntimeError(
            f"existing prefix is not chunk aligned: {size} bytes for {chunk_bytes}-byte chunks"
        )
    if expected_md5 and _md5_file(existing) != expected_md5.lower():
        raise RuntimeError(f"existing prefix MD5 mismatch: {existing}")

    with existing.open("rb") as source:
        start = 0
        while start < size:
            part = chunk_dir / f"{start:012d}.part"
            expected = min(chunk_bytes, size - start)
            if not part.exists() or part.stat().st_size != expected:
                source.seek(start)
                with part.open("wb") as target:
                    remaining = expected
                    while remaining:
                        block = source.read(min(8 * 1024 * 1024, remaining))
                        if not block:
                            raise RuntimeError(f"existing prefix ended at {start}")
                        target.write(block)
                        remaining -= len(block)
            start += expected
    return size


def fetch(
    output: Path,
    chunk_bytes: int,
    workers: int,
    retries: int,
    resume_existing_prefix: bool = False,
    existing_prefix_md5: str | None = None,
) -> dict[str, object]:
    opener, headers = _session()
    total = _probe(opener, headers)
    if total != EXPECTED_BYTES:
        raise RuntimeError(f"publisher size changed: {total} != {EXPECTED_BYTES}")

    output.parent.mkdir(parents=True, exist_ok=True)
    chunk_dir = output.with_name(output.name + ".ranges")
    chunk_dir.mkdir(parents=True, exist_ok=True)
    seeded_bytes = 0
    if resume_existing_prefix and output.exists():
        seeded_bytes = _seed_existing_prefix(
            output, chunk_dir, chunk_bytes, existing_prefix_md5
        )
    all_ranges = [
        (start, min(start + chunk_bytes, total) - 1)
        for start in range(0, total, chunk_bytes)
    ]
    download_ranges = [
        item for item in all_ranges if item[0] >= seeded_bytes
    ]
    url = headers["Download-URL"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _download_range,
                url,
                headers,
                start,
                end,
                chunk_dir / f"{start:012d}.part",
                retries,
            ): (start, end)
            for start, end in download_ranges
        }
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            start, copied = future.result()
            completed += copied
            print(json.dumps({"completed_bytes": completed, "total_bytes": total, "range_start": start}), flush=True)

    digest = hashlib.md5()
    with output.with_suffix(output.suffix + ".partial").open("wb") as target:
        for start, _end in all_ranges:
            part = chunk_dir / f"{start:012d}.part"
            with part.open("rb") as source:
                shutil.copyfileobj(source, target, length=8 * 1024 * 1024)
                source.seek(0)
                while block := source.read(8 * 1024 * 1024):
                    digest.update(block)
    actual_md5 = digest.hexdigest()
    staged = output.with_suffix(output.suffix + ".partial")
    if actual_md5 != EXPECTED_MD5 or staged.stat().st_size != total:
        return {
            "status": "FAIL",
            "bytes": staged.stat().st_size,
            "md5": actual_md5,
            "expected_bytes": total,
            "expected_md5": EXPECTED_MD5,
            "output": str(staged),
        }
    staged.replace(output)
    shutil.rmtree(chunk_dir)
    return {
        "status": "PASS",
        "bytes": total,
        "md5": actual_md5,
        "output": str(output),
        "range_count": len(all_ranges),
        "download_range_count": len(download_ranges),
        "seeded_prefix_bytes": seeded_bytes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/public_validation/raw/kit_lh2_consequence_1483/archive.tar"))
    parser.add_argument("--chunk-bytes", type=int, default=64 * 1024 * 1024)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument(
        "--resume-existing-prefix",
        action="store_true",
        help="Reuse an existing chunk-aligned opaque prefix at --output.",
    )
    parser.add_argument(
        "--existing-prefix-md5",
        default=None,
        help="Optional MD5 for the existing prefix; fail closed on mismatch.",
    )
    args = parser.parse_args()
    result = fetch(
        args.output.resolve(),
        args.chunk_bytes,
        args.workers,
        args.retries,
        args.resume_existing_prefix,
        args.existing_prefix_md5,
    )
    print(json.dumps(result), flush=True)
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
