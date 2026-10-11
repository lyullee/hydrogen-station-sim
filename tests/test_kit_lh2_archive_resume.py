from __future__ import annotations

import hashlib

import pytest

from scripts.fetch_kit_lh2_archive import _seed_existing_prefix


def test_seed_existing_prefix_reuses_aligned_opaque_chunks(tmp_path):
    source = tmp_path / "archive.tar"
    payload = bytes(range(256)) * 32
    source.write_bytes(payload)
    chunk_dir = tmp_path / "archive.tar.ranges"
    chunk_dir.mkdir()

    seeded = _seed_existing_prefix(
        source,
        chunk_dir,
        512,
        hashlib.md5(payload).hexdigest(),
    )

    assert seeded == len(payload)
    assert (chunk_dir / "000000000000.part").read_bytes() == payload[:512]
    assert (chunk_dir / "000000000512.part").read_bytes() == payload[512:1024]


def test_seed_existing_prefix_rejects_unaligned_prefix(tmp_path):
    source = tmp_path / "archive.tar"
    source.write_bytes(b"x" * 513)
    with pytest.raises(RuntimeError, match="not chunk aligned"):
        _seed_existing_prefix(source, tmp_path / "ranges", 512, None)


def test_seed_existing_prefix_rejects_bad_hash(tmp_path):
    source = tmp_path / "archive.tar"
    source.write_bytes(b"x" * 512)
    with pytest.raises(RuntimeError, match="MD5 mismatch"):
        _seed_existing_prefix(source, tmp_path / "ranges", 512, "0" * 32)
