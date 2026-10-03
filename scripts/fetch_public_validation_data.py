"""Download cited public validation data without adding it to Git.

The committed manifest records stable source URLs, attribution and checksums.
Third-party raw files remain under the gitignored ``data`` directory.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
from urllib.request import Request, urlopen


USER_AGENT = "hydrogen-station-sim-public-validation/1.0 (research reproducibility)"


def _hash(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=180) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)
    temporary.replace(destination)


def _fetch_static(source: dict, root: Path, *, force: bool) -> list[dict]:
    records = []
    for item in source["files"]:
        path = root / item["name"]
        if force or not path.exists():
            _download(item["url"], path)
        actual_size = path.stat().st_size
        actual_hash = _hash(path)
        if actual_size != int(item["bytes"]):
            raise RuntimeError(f"Size mismatch for {path}: {actual_size} != {item['bytes']}")
        if actual_hash.lower() != item["sha256"].lower():
            raise RuntimeError(f"SHA-256 mismatch for {path}")
        records.append({
            "name": item["name"], "bytes": actual_size,
            "sha256": actual_hash, "source_url": item["url"],
        })
    return records


def _fetch_figshare(source: dict, root: Path, *, force: bool) -> list[dict]:
    request = Request(source["api_url"], headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        article = json.load(response)
    records = []
    for item in article["files"]:
        path = root / item["name"]
        if force or not path.exists():
            _download(item["download_url"], path)
        actual_size = path.stat().st_size
        actual_md5 = _hash(path, "md5")
        if actual_size != int(item["size"]):
            raise RuntimeError(f"Size mismatch for {path}: {actual_size} != {item['size']}")
        if actual_md5.lower() != item["supplied_md5"].lower():
            raise RuntimeError(f"MD5 mismatch for {path}")
        records.append({
            "name": item["name"], "bytes": actual_size,
            "md5": actual_md5, "source_url": item["download_url"],
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "datasets", nargs="*",
        choices=(
            "h2protocol_j2601_tables", "h2protocol_mc_default", "hiad_2_2",
            "hydrogen_dispersion_channel",
        ),
        default=["h2protocol_j2601_tables", "hiad_2_2"],
    )
    parser.add_argument("--manifest", type=Path, default=Path("research/data_sources.json"))
    parser.add_argument("--output", type=Path, default=Path("data/public_validation/raw"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    acquisition_path = args.output / "acquisition.json"
    if acquisition_path.exists():
        acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
    else:
        acquisition = {"schema_version": 1, "files": {}}
    acquisition["source_manifest"] = str(args.manifest)
    acquisition["verified_at"] = datetime.now(timezone.utc).isoformat()
    for key in args.datasets:
        source = manifest["sources"][key]
        root = args.output / key
        if "api_url" in source:
            records = _fetch_figshare(source, root, force=args.force)
        else:
            records = _fetch_static(source, root, force=args.force)
        acquisition["files"][key] = records
        print(f"{key}: verified {len(records)} files", file=sys.stderr)

    args.output.mkdir(parents=True, exist_ok=True)
    acquisition_path.write_text(
        json.dumps(acquisition, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output / "acquisition.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
