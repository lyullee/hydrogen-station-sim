from __future__ import annotations

from io import BytesIO
import tarfile

from scripts.fetch_preslhy_ambient_packages import (
    BlockCachedRangeReader,
    iter_tar_members,
)


def test_tar_range_index_handles_regular_and_long_member_names():
    archive = BytesIO()
    with tarfile.open(fileobj=archive, mode="w", format=tarfile.PAX_FORMAT) as bundle:
        first = tarfile.TarInfo("root/PRE3P1A_KIT_D1_300K_DATA.zip")
        first.size = 4
        bundle.addfile(first, BytesIO(b"PK\x03\x04"))
        long_name = "root/" + ("nested/" * 20) + "PRE3P1A_KIT_D4_300K_DATA.zip"
        second = tarfile.TarInfo(long_name)
        second.size = 5
        bundle.addfile(second, BytesIO(b"hello"))
    payload = archive.getvalue()

    def fetch(offset: int, length: int) -> bytes:
        return payload[offset : offset + length]

    members = list(iter_tar_members(fetch, len(payload)))
    assert [member.name for member in members] == [
        "root/PRE3P1A_KIT_D1_300K_DATA.zip",
        long_name,
    ]
    assert fetch(members[0].offset, members[0].size) == b"PK\x03\x04"
    assert fetch(members[1].offset, members[1].size) == b"hello"
    next_offset = members[0].offset + ((members[0].size + 511) // 512) * 512
    resumed = list(iter_tar_members(fetch, len(payload), start_offset=next_offset))
    assert [member.name for member in resumed] == [long_name]


def test_block_cache_reuses_adjacent_ranges():
    payload = bytes(range(256)) * 16
    calls = []

    def raw(offset: int, length: int) -> bytes:
        calls.append((offset, length))
        return payload[offset : offset + length]

    cached = BlockCachedRangeReader(raw, len(payload), block_size=1024)
    assert cached(0, 512) == payload[:512]
    assert cached(512, 512) == payload[512:1024]
    assert calls == [(0, 1024)]
