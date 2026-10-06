"""Audit owner-controlled photos and screen recordings without persisting media.

The owner sometimes supplies logger data as a video of an Excel/SCADA screen.
That is useful provenance and channel-inventory evidence, but it is not a
machine-readable trace.  This audit deliberately records only aggregate media
counts, stream metadata and the next custodian-side intake requirements.  It
never writes source paths, filenames, calendar values, frames or OCR output.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
import re
import subprocess
from typing import Any


SIZE_BUCKETS = ("<1MiB", "1-100MiB", "100-500MiB", ">=500MiB")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".m4v"}


def _size_bucket(size: int) -> str:
    mib = 1024 * 1024
    if size < mib:
        return "<1MiB"
    if size < 100 * mib:
        return "1-100MiB"
    if size < 500 * mib:
        return "100-500MiB"
    return ">=500MiB"


def _probe_video(path: Path, ffmpeg: str | None) -> dict[str, Any]:
    """Return privacy-safe stream metadata; fail closed when no probe exists."""

    if not ffmpeg:
        return {"probe_status": "not_run"}
    try:
        completed = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except (OSError, ValueError):
        return {"probe_status": "probe_error"}
    text = completed.stderr.decode("utf-8", errors="replace")
    duration_match = re.search(
        r"Duration:\s+(\d+):(\d+):(\d+\.\d+)", text
    )
    duration_s = None
    if duration_match:
        hours, minutes, seconds = duration_match.groups()
        duration_s = round(
            int(hours) * 3600 + int(minutes) * 60 + float(seconds), 3
        )
    resolutions = sorted(
        {
            f"{width}x{height}"
            for width, height in re.findall(r"\b(\d{3,5})x(\d{3,5})\b", text)
        }
    )
    return {
        "probe_status": "decoded" if duration_s is not None else "undecodable",
        "duration_s": duration_s,
        "has_video_stream": "Video:" in text,
        "has_audio_stream": "Audio:" in text,
        "resolution_families": resolutions,
    }


def audit(root: Path, *, ffmpeg: str | None = None) -> dict[str, Any]:
    """Build an aggregate intake decision without exposing source identifiers."""

    files = [path for path in root.rglob("*") if path.is_file()]
    extension_counts: dict[str, int] = {}
    size_buckets = {bucket: 0 for bucket in SIZE_BUCKETS}
    image_count = 0
    video_count = 0
    video_decoded = 0
    video_undecodable = 0
    video_duration_s = 0.0
    audio_stream_count = 0
    resolutions: set[str] = set()
    non_media_count = 0

    for path in files:
        suffix = path.suffix.lower() or "<none>"
        extension_counts[suffix] = extension_counts.get(suffix, 0) + 1
        size_buckets[_size_bucket(path.stat().st_size)] += 1
        if suffix in IMAGE_EXTENSIONS:
            image_count += 1
            continue
        if suffix not in VIDEO_EXTENSIONS:
            non_media_count += 1
            continue
        video_count += 1
        probe = _probe_video(path, ffmpeg)
        if probe.get("probe_status") == "decoded":
            video_decoded += 1
            video_duration_s += float(probe.get("duration_s") or 0.0)
        elif probe.get("probe_status") == "undecodable":
            video_undecodable += 1
        if probe.get("has_audio_stream"):
            audio_stream_count += 1
        resolutions.update(probe.get("resolution_families") or [])

    return {
        "schema_version": 1,
        "artifact_type": "confidential_private_media_intake_assessment",
        "recorded_at": datetime.now().strftime("%Y-%m"),
        "source_identifiers_published": False,
        "raw_media_persisted": False,
        "exact_source_dates_published": False,
        "file_count": len(files),
        "extension_counts": dict(sorted(extension_counts.items())),
        "size_buckets": size_buckets,
        "media_inventory": {
            "image_count": image_count,
            "video_count": video_count,
            "non_media_count": non_media_count,
            "video_probe_used": bool(ffmpeg),
            "video_decoded_count": video_decoded,
            "video_undecodable_count": video_undecodable,
            "video_duration_s_total": round(video_duration_s, 3),
            "video_audio_stream_count": audio_stream_count,
            "video_resolution_families": sorted(resolutions),
        },
        "content_assessment": {
            "screen_recorded_logger_candidate": video_decoded > 0,
            "displayed_channel_values_machine_readable": False,
            "machine_readable_trace_present": False,
            "equipment_photo_inventory_candidate": image_count > 0,
            "ocr_or_frame_values_used_for_calibration": False,
            "assessment": (
                "Screen recordings and photos can support channel/equipment inventory. "
                "They are not used as calibration rows because timestamps, tag units, "
                "calibration status and event semantics cannot be verified from media alone."
            ),
        },
        "eligibility": {
            "channel_inventory_candidate": video_decoded > 0,
            "equipment_geometry_review_candidate": image_count > 0,
            "pressure_or_temperature_parameter_fit": False,
            "station_vehicle_full_loop_validation": False,
            "full_loop_holdout_eligible": False,
        },
        "required_custodian_intake": [
            "Export the original logger/SCADA table as CSV or XLSX, not a screen recording.",
            "Provide a tag dictionary with engineering units, scale, direction and quality semantics.",
            "Provide calibration/uncertainty information and a timezone policy; exact calendar dates can be replaced by relative seconds after intake.",
            "Mark fill, idle, vent, alarm, ESD and vehicle/receptacle events so a temporal holdout can be frozen.",
            "Confirm written reuse terms and keep the raw archive outside the public repository.",
        ],
        "claim_boundary": (
            "Private-media provenance and intake readiness only. This artifact is not "
            "numerical calibration, physical validation, safety certification or a "
            "station-to-vehicle holdout."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=str, default=None)
    args = parser.parse_args()
    result = audit(args.input, ffmpeg=args.ffmpeg)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
