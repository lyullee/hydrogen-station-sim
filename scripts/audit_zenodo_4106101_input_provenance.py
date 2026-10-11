#!/usr/bin/env python3
"""Audit source provenance for the Zenodo 4106101 pressure-peaking runner.

This audit deliberately does not change the frozen result. It checks which
boundary values are present in the CC-BY metadata document and which values
are supplied by the runner outside that document.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
from zipfile import ZipFile


EXPECTED_MD5 = {
    "HTE242USN000METADATA.DOCX": "19ed05ec6b768b91a3accd61952f06ac",
    "HTE242USN00011MFR.zip": "e210005525700347a43d9cf352e9a39b",
    "HTE242USN00011PRESS.zip": "85f590964f3dcefba1f4b2a59916a1a3",
}

EXPECTED_VENT_AREA_M2 = {
    2: 0.0012, 3: 0.0020, 4: 0.0020, 5: 0.0014, 6: 0.0014,
    7: 0.0006, 8: 0.0006, 9: 0.0006, 10: 0.0006, 11: 0.0006,
}


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def docx_text(path: Path) -> str:
    """Extract enough text to inspect the public metadata without a DOCX dependency."""
    with ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    return html.unescape(re.sub(r"<[^>]+>", "", xml))


def _case_rows(text: str) -> dict[int, dict[str, float]]:
    """Read the compact experiment table embedded in the metadata document."""
    rows: dict[int, dict[str, float]] = {}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if line != "2":
            continue
        cursor = index
        while cursor < len(lines):
            try:
                case = int(lines[cursor])
            except ValueError:
                break
            if case not in EXPECTED_VENT_AREA_M2:
                break
            # Nine cells follow the experiment number: nozzle, volume, vent
            # area, vent size, MFR, reservoir pressure, peak overpressure,
            # peak time and duration.
            values = lines[cursor + 1 : cursor + 10]
            try:
                vent_area = float(re.match(r"[-+]?\d*\.?(?:\d+)", values[2]).group(0))
                rows[case] = {
                    "nozzle_diameter_m": float(values[0]),
                    "volume_m3": float(values[1]),
                    "vent_area_m2": vent_area,
                }
            except (AttributeError, IndexError, ValueError):
                break
            cursor += 10
        break
    return rows


def audit(raw_directory: Path) -> dict[str, object]:
    metadata = raw_directory / "HTE242USN000METADATA.DOCX"
    mfr = raw_directory / "HTE242USN00011MFR.zip"
    pressure = raw_directory / "HTE242USN00011PRESS.zip"
    files = {path.name: md5(path) for path in (metadata, mfr, pressure)}
    text = docx_text(metadata)
    rows = _case_rows(text)
    geometry_pass = (
        len(rows) == len(EXPECTED_VENT_AREA_M2)
        and all(
            abs(rows[case]["volume_m3"] - 14.9) <= 1e-12
            and abs(rows[case]["vent_area_m2"] - area) <= 1e-12
            for case, area in EXPECTED_VENT_AREA_M2.items()
        )
    )
    # The metadata describes pressure, concentration, MFR and vent geometry;
    # it does not contain a per-case temperature channel or initial-T table.
    temperature_boundary_present = bool(
        re.search(r"(?:initial|ambient|gas|enclosure)\s+temperature", text, re.I)
    )
    return {
        "schema_version": 1,
        "artifact_type": "zenodo_4106101_input_provenance_audit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "doi": "10.5281/zenodo.4106101",
            "metadata_file": metadata.as_posix(),
            "archive_md5": files,
            "expected_md5_match": files == EXPECTED_MD5,
        },
        "documented_boundaries": {
            "geometry_and_vent_area": {
                "metadata_case_count": len(rows),
                "expected_case_count": len(EXPECTED_VENT_AREA_M2),
                "matches_runner_constants": geometry_pass,
                "volume_m3": 14.9,
                "vent_area_m2_by_case": EXPECTED_VENT_AREA_M2,
            },
            "temperature": {
                "per_case_temperature_boundary_in_metadata": temperature_boundary_present,
                "interpretation": "No temperature channel or initial-temperature table is present in the Zenodo metadata snapshot.",
            },
        },
        "runner_boundary_status": {
            "temperature_constants_in_runner": True,
            "temperature_constants_source": "undocumented in the Zenodo metadata snapshot; requires separate paper/supplement provenance",
            "runtime_parameter_changed": False,
            "result_reclassification": "exploratory_only_until_temperature_provenance_or_channel_is independently archived",
        },
        "claim_boundary": "This audit corrects provenance wording only. It does not retune the pressure-peaking model or promote a validation claim.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-directory", type=Path, default=Path("data/public_validation/raw/zenodo_4106101"))
    parser.add_argument("--output", type=Path, default=Path("research/zenodo_4106101_input_provenance_audit_2026_10_11.json"))
    args = parser.parse_args()
    result = audit(args.raw_directory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["documented_boundaries"], ensure_ascii=False))


if __name__ == "__main__":
    main()
