from __future__ import annotations

import io
import tarfile

from scripts.audit_kit_lh2_consequence_access import _scan_members


def test_stage1_member_scan_does_not_open_payload_values(tmp_path):
    archive = tmp_path / "archive.tar"
    with tarfile.open(archive, "w") as stream:
        info = tarfile.TarInfo("README.txt")
        payload = b"metadata only"
        info.size = len(payload)
        stream.addfile(info, io.BytesIO(payload))

    result = _scan_members(archive)

    assert result["complete"] is True
    assert result["values_opened"] is False
    assert result["video_outcomes_opened"] is False
    assert result["members"][0]["name"] == "README.txt"


def test_stage1_member_scan_records_truncated_archive_without_promoting_it(tmp_path):
    archive = tmp_path / "archive.tar"
    with tarfile.open(archive, "w") as stream:
        info = tarfile.TarInfo("outcome.mp4")
        payload = b"video bytes" * 100
        info.size = len(payload)
        stream.addfile(info, io.BytesIO(payload))
    # Keep the tar header but truncate the member payload, which forces the
    # header-only scan to record an incomplete archive instead of accepting
    # harmless zero padding at the end of an otherwise complete tar stream.
    archive.write_bytes(archive.read_bytes()[:512 + 100])

    result = _scan_members(archive)

    assert result["complete"] is False
    assert result["error"]
    assert result["video_outcomes_opened"] is False
