"""Fetch only the ambient PRESLHY E3.1 numerical packages from its TAR.

The official RADAR archive is about 1.3 GB and also contains photographs and
cryogenic records.  Its HTTP endpoint supports byte ranges, so this utility
walks the TAR headers and downloads only the four ``300K_DATA`` ZIP members.
Third-party files and the acquisition record stay below the gitignored
``data`` directory.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import time
from typing import Callable, Iterator
from urllib.request import Request, urlopen


USER_AGENT = "hydrogen-station-sim-preslhy-validation/1.0"
DEFAULT_URL = (
    "https://www.radar-service.eu/radar-backend/archives/"
    "vuyYifgxlfOuFrSP/versions/1/content"
)
DEFAULT_ARCHIVE_BYTES = 1_313_122_304
TARGET_NAME = re.compile(r"^PRE3P1A_KIT_D(?:05|1|2|4)_300K_DATA\.zip$", re.I)


@dataclass(frozen=True)
class TarMember:
    name: str
    offset: int
    size: int
    typeflag: str


def _tar_text(field: bytes) -> str:
    return field.split(b"\0", 1)[0].decode("utf-8", errors="replace").strip()


def _tar_number(field: bytes) -> int:
    value = field.rstrip(b"\0 ")
    if not value:
        return 0
    if value[0] & 0x80:
        return int.from_bytes(value, "big", signed=True)
    return int(value, 8)


def _verify_header(header: bytes, offset: int) -> None:
    if len(header) != 512:
        raise RuntimeError(f"short TAR header at byte {offset}")
    expected = _tar_number(header[148:156])
    checksum_header = header[:148] + (b" " * 8) + header[156:]
    actual = sum(checksum_header)
    if expected != actual:
        raise RuntimeError(
            f"invalid TAR checksum at byte {offset}: {actual} != {expected}"
        )


def _parse_pax(payload: bytes) -> dict[str, str]:
    fields: dict[str, str] = {}
    cursor = 0
    while cursor < len(payload):
        separator = payload.find(b" ", cursor)
        if separator < 0:
            break
        length = int(payload[cursor:separator])
        record = payload[separator + 1 : cursor + length].rstrip(b"\n")
        key, marker, value = record.partition(b"=")
        if marker:
            fields[key.decode("utf-8")] = value.decode("utf-8")
        cursor += length
    return fields


def iter_tar_members(
    fetch_range: Callable[[int, int], bytes],
    archive_size: int,
    *,
    start_offset: int = 0,
) -> Iterator[TarMember]:
    """Yield regular TAR members using inclusive-independent byte ranges."""

    offset = start_offset
    pending_name: str | None = None
    pending_pax: dict[str, str] = {}
    while offset + 512 <= archive_size:
        header = fetch_range(offset, 512)
        if header == b"\0" * 512:
            return
        _verify_header(header, offset)
        name = _tar_text(header[0:100])
        prefix = _tar_text(header[345:500])
        if prefix:
            name = f"{prefix}/{name}"
        size = _tar_number(header[124:136])
        typeflag = chr(header[156]) if header[156] else "0"
        content_offset = offset + 512
        padded_size = ((size + 511) // 512) * 512

        if typeflag in {"L", "K", "x", "g"}:
            payload = fetch_range(content_offset, size) if size else b""
            if typeflag == "L":
                pending_name = _tar_text(payload)
            elif typeflag in {"x", "g"}:
                pending_pax.update(_parse_pax(payload))
        else:
            resolved_name = pending_pax.get("path", pending_name or name)
            yield TarMember(resolved_name, content_offset, size, typeflag)
            pending_name = None
            pending_pax = {}
        offset = content_offset + padded_size


class HttpRangeReader:
    def __init__(self, url: str, *, attempts: int = 5, timeout_s: int = 90):
        self.url = url
        self.attempts = attempts
        self.timeout_s = timeout_s

    def __call__(self, offset: int, length: int) -> bytes:
        if length == 0:
            return b""
        end = offset + length - 1
        last_error: Exception | None = None
        for attempt in range(self.attempts):
            try:
                request = Request(
                    self.url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Range": f"bytes={offset}-{end}",
                        "Accept-Encoding": "identity",
                    },
                )
                with urlopen(request, timeout=self.timeout_s) as response:
                    payload = response.read()
                    content_range = response.headers.get("Content-Range", "")
                    if response.status != 206:
                        raise RuntimeError(
                            f"range request returned HTTP {response.status}"
                        )
                    if not content_range.startswith(f"bytes {offset}-{end}/"):
                        raise RuntimeError(f"unexpected Content-Range: {content_range}")
                    if len(payload) != length:
                        raise RuntimeError(
                            f"short range {offset}-{end}: {len(payload)} bytes"
                        )
                    return payload
            except Exception as exc:  # network errors vary by platform
                last_error = exc
                if attempt + 1 < self.attempts:
                    time.sleep(2**attempt)
        raise RuntimeError(f"failed to fetch bytes {offset}-{end}") from last_error


class BlockCachedRangeReader:
    """Amortize adjacent TAR-header reads over one remote range request."""

    def __init__(
        self,
        reader: HttpRangeReader,
        archive_size: int,
        block_size: int = 256 * 1024,
    ) -> None:
        self.reader = reader
        self.archive_size = archive_size
        self.block_size = block_size
        self._offset = -1
        self._payload = b""

    def __call__(self, offset: int, length: int) -> bytes:
        if (
            self._offset <= offset
            and offset + length <= self._offset + len(self._payload)
        ):
            start = offset - self._offset
            return self._payload[start : start + length]
        if length > self.block_size:
            return self.reader(offset, length)
        fetch_length = min(self.block_size, self.archive_size - offset)
        self._offset = offset
        self._payload = self.reader(offset, fetch_length)
        return self._payload[:length]


def _download_member(
    reader: HttpRangeReader,
    member: TarMember,
    destination: Path,
    *, chunk_size: int = 8 * 1024 * 1024,
) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.sha256()
    written = temporary.stat().st_size if temporary.exists() else 0
    if written > member.size:
        raise RuntimeError(f"partial download exceeds member size: {temporary}")
    if written:
        with temporary.open("rb") as existing:
            for block in iter(lambda: existing.read(1024 * 1024), b""):
                digest.update(block)
        print(f"resuming {destination.name} at byte {written}", flush=True)
    with temporary.open("ab") as output:
        while written < member.size:
            length = min(chunk_size, member.size - written)
            payload = reader(member.offset + written, length)
            output.write(payload)
            output.flush()
            digest.update(payload)
            written += length
            print(
                f"{destination.name}: {written}/{member.size} bytes",
                flush=True,
            )
    if temporary.stat().st_size != member.size:
        raise RuntimeError(f"download size mismatch for {member.name}")
    with temporary.open("rb") as handle:
        if handle.read(4) != b"PK\x03\x04":
            raise RuntimeError(f"downloaded member is not a ZIP: {member.name}")
    temporary.replace(destination)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--archive-bytes", type=int, default=DEFAULT_ARCHIVE_BYTES)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/public_validation/raw/preslhy"),
    )
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--restart-index", action="store_true")
    args = parser.parse_args()

    expected = {
        "PRE3P1A_KIT_D05_300K_DATA.zip",
        "PRE3P1A_KIT_D1_300K_DATA.zip",
        "PRE3P1A_KIT_D2_300K_DATA.zip",
        "PRE3P1A_KIT_D4_300K_DATA.zip",
    }
    reader = HttpRangeReader(args.url)
    index_reader = BlockCachedRangeReader(reader, args.archive_bytes)
    args.output.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.output / "tar_index_checkpoint.json"
    if checkpoint_path.exists() and not args.restart_index:
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if (
            checkpoint.get("source_url") != args.url
            or checkpoint.get("archive_bytes") != args.archive_bytes
        ):
            raise RuntimeError("TAR checkpoint source does not match this request")
        start_offset = int(checkpoint["next_offset"])
        members = [TarMember(**item) for item in checkpoint.get("targets", [])]
        print(f"resuming TAR index at byte {start_offset}", flush=True)
    else:
        start_offset = 0
        members = []
    if not args.list_only:
        for member in members:
            name = PurePosixPath(member.name).name
            destination = args.output / name
            if not destination.exists():
                digest = _download_member(reader, member, destination)
                print(f"verified {name}: sha256 {digest}", flush=True)
    for member in iter_tar_members(
        index_reader, args.archive_bytes, start_offset=start_offset
    ):
        name = PurePosixPath(member.name).name
        newly_located = False
        if TARGET_NAME.fullmatch(name):
            if name not in {PurePosixPath(item.name).name for item in members}:
                members.append(member)
                newly_located = True
                print(f"located {name}", flush=True)
        next_offset = member.offset + ((member.size + 511) // 512) * 512
        checkpoint_path.write_text(
            json.dumps(
                {
                    "source_url": args.url,
                    "archive_bytes": args.archive_bytes,
                    "next_offset": next_offset,
                    "targets": [asdict(item) for item in members],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if newly_located and not args.list_only:
            destination = args.output / name
            if not destination.exists() or args.force:
                digest = _download_member(reader, member, destination)
                print(f"verified {name}: sha256 {digest}", flush=True)
        if {PurePosixPath(item.name).name for item in members} == expected:
            break
    found = {PurePosixPath(member.name).name for member in members}
    if found != expected:
        raise RuntimeError(f"ambient package set mismatch: found {sorted(found)}")
    for member in members:
        print(f"{member.name}\t{member.size}\t{member.offset}")
    if args.list_only:
        return 0

    records = []
    for member in members:
        name = PurePosixPath(member.name).name
        destination = args.output / name
        if destination.exists() and not args.force:
            if destination.stat().st_size != member.size:
                raise RuntimeError(f"existing file has wrong size: {destination}")
            digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        else:
            digest = _download_member(reader, member, destination)
        records.append({**asdict(member), "file": name, "sha256": digest})
        print(f"verified {name}: {member.size} bytes, sha256 {digest}")

    acquisition = {
        "schema_version": 1,
        "source_url": args.url,
        "source_archive_bytes": args.archive_bytes,
        "source_archive_md5_published": "b4d245866b7daed5705a06415a83b013",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "range_extraction": True,
        "members": records,
    }
    (args.output / "acquisition_preslhy.json").write_text(
        json.dumps(acquisition, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
