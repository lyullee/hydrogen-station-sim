"""Privacy-bounded discovery scan for local hydrogen-station candidates.

This scanner is intentionally a discovery aid, not a validation importer.  It
keeps only aggregate counts and coarse candidate classes.  Paths, filenames,
headers, timestamps, identifiers and measurement values are never written to
the output.  A candidate becomes eligible for validation only after a separate
custodian attestation establishes units, time alignment, boundary roles and
reuse rights.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Iterable

try:  # Optional: spreadsheet inspection is opt-in and must not block CSV scans.
    import openpyxl
except ImportError:  # pragma: no cover - exercised only in minimal environments.
    openpyxl = None

try:  # Optional: scientific-container inspection is explicitly opt-in.
    from scipy.io import whosmat
except ImportError:  # pragma: no cover - exercised only in minimal environments.
    whosmat = None

try:  # Optional: HDF5 inspection is explicitly opt-in.
    import h5py
except ImportError:  # pragma: no cover - exercised only in minimal environments.
    h5py = None


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
}

MACHINE_EXTENSIONS = {
    ".csv",
    ".tsv",
    ".xlsx",
    ".xls",
    ".json",
    ".mat",
    ".h5",
    ".hdf5",
    ".txt",
    ".md",
}

PATH_KEYWORDS = re.compile(
    r"vehicle|car|tank|disp|nozzle|fuel|station|hrs|충전|차량|탱크|디스펜|노즐|수소",
    re.IGNORECASE,
)
HEADER_FAMILIES = {
    "vehicle_or_dispenser": re.compile(
        r"veh|vehicle|car|tank|disp|nozzle|fuel|soc|충전|차량|탱크|디스펜|노즐",
        re.IGNORECASE,
    ),
    "pressure": re.compile(
        r"press|pressure|pt[_-]?\d+|pi[_-]?\d+|압력", re.IGNORECASE
    ),
    "temperature": re.compile(
        r"temp|temperature|tt[_-]?\d+|ti[_-]?\d+|온도", re.IGNORECASE
    ),
    "flow_or_mass": re.compile(
        r"flow|mass|rate|totalizer|accum|유량|질량|적산", re.IGNORECASE
    ),
    "protocol_or_control": re.compile(
        r"protocol|command|controller|state|valve|esd|pcv|제어|밸브|차단",
        re.IGNORECASE,
    ),
}
RELEASE_RIG_PATTERN = re.compile(
    r"release|rig|jet|aperture|누출|분출", re.IGNORECASE
)
STATIC_TEMPLATE_PATTERN = re.compile(
    r"(?:^|[_\- .])(?:template|schema|example)(?:$|[_\- .])",
    re.IGNORECASE,
)
TIME_PATTERN = re.compile(
    r"^time(?:\s*\([^)]*\)|\s*\[[^]]+\]|_s)?$|"
    r"timestamp|datetime|zeit|시간|시각",
    re.IGNORECASE,
)
SPLIT_ROLE_TOKENS = re.compile(
    r"(?:^|[_\- .])(?:station|hrs|vehicle|car|tank|receiving|receptacle|"
    r"disp(?:enser)?|nozzle|source|station-side|vehicle-side|충전소|차량|"
    r"탱크|수용부|디스펜서|노즐)(?=$|[_\- .])",
    re.IGNORECASE,
)
RECEIVING_BOUNDARY = re.compile(
    r"vehicle|car|receptacle|vehicle[_ -]?tank|fuel[_ -]?cell|차량|수용부|차량탱크",
    re.IGNORECASE,
)
STATION_BOUNDARY = re.compile(
    r"station|hrs|disp(?:enser)?|cascade|precool(?:er)?|supply|compressor|"
    r"충전소|디스펜서|뱅크|압축기|공급|프리쿨",
    re.IGNORECASE,
)
SOURCE_PRESSURE_CHANNEL = re.compile(
    r"source[_ -]?pressure|supply[_ -]?pressure|psupply|p[_ -]?supply|"
    r"station[_ -]?pressure|dispenser[_ -]?pressure|bank[_ -]?pressure|"
    r"공급압력|소스압력|뱅크압력",
    re.IGNORECASE,
)


def _iter_files(roots: Iterable[Path]) -> Iterable[Path]:
    """Yield files without retaining their paths in the result."""

    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in MACHINE_EXTENSIONS:
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            yield path


def _read_header(
    path: Path,
    *,
    inspect_spreadsheets: bool = False,
    inspect_scientific: bool = False,
) -> list[str]:
    suffix = path.suffix.lower()
    if suffix in {".mat", ".h5", ".hdf5"}:
        if not inspect_scientific:
            return []
        try:
            if suffix == ".mat":
                if whosmat is None:
                    return []
                # ``whosmat`` reads only the MATLAB directory and metadata;
                # numerical arrays are not loaded or persisted.
                return [str(name) for name, _shape, _kind in whosmat(path)]
            if h5py is None:
                return []
            names: list[str] = []
            with h5py.File(path, "r") as handle:
                def collect(name: str) -> None:
                    if len(names) < 4096:
                        names.append(str(name))
                handle.visit(collect)
            return names
        # Scientific archives in document workspaces are often mixed-version
        # MATLAB/HDF5 exports.  A malformed member is a bounded parse miss,
        # not a reason to abort the whole aggregate scan.
        except Exception:  # noqa: BLE001 - discovery must fail closed per file.
            return []
    if suffix not in {".csv", ".tsv", ".xlsx"}:
        return []
    if suffix == ".xlsx":
        if not inspect_spreadsheets or openpyxl is None:
            return []
        # Read only a small header window.  Values are used in memory for
        # classification and are never returned or persisted.
        try:
            workbook = openpyxl.load_workbook(
                path, read_only=True, data_only=True, keep_links=False
            )
            headers: list[str] = []
            for worksheet in workbook.worksheets[:8]:
                candidates: list[list[str]] = []
                for row in worksheet.iter_rows(max_row=32, max_col=256, values_only=True):
                    values = [str(value).strip() for value in row if value is not None and str(value).strip()]
                    if len(values) >= 2:
                        candidates.append(values)
                if candidates:
                    # Prefer the row that exposes the most channel families;
                    # this handles a short title row before the real header.
                    headers.extend(max(candidates, key=lambda values: sum(
                        bool(pattern.search(" ".join(values)))
                        for pattern in HEADER_FAMILIES.values()
                    )))
            workbook.close()
            return headers
        except (OSError, ValueError, KeyError, RuntimeError):
            return []
    for encoding in ("utf-8-sig", "cp949", "utf-16"):
        try:
            with path.open("r", encoding=encoding, newline="") as stream:
                delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
                return next(csv.reader(stream, delimiter=delimiter), [])
        except (OSError, UnicodeError, csv.Error):
            continue
    return []


def _classify_candidate(path: Path, header: list[str]) -> str:
    text = " ".join([path.stem, *header])
    # A schema/template is useful for intake documentation but cannot be
    # treated as an observed trace merely because it contains all channel
    # names.  Keep it in the aggregate file count and out of data candidates.
    if STATIC_TEMPLATE_PATTERN.search(path.stem):
        return "unclassified_machine_readable"
    # ELVHYS-style release-rig traces often contain ``nozzle`` and pressure
    # labels.  Keep them separate from vehicle/dispenser candidates so a
    # keyword hit cannot be mistaken for a full-loop fueling record.
    if RELEASE_RIG_PATTERN.search(text) and HEADER_FAMILIES["pressure"].search(text):
        return "release_rig_experiment_candidate"
    has_time = any(TIME_PATTERN.search(str(column)) for column in header)
    has_pressure = bool(HEADER_FAMILIES["pressure"].search(text))
    has_temperature = bool(HEADER_FAMILIES["temperature"].search(text))
    has_flow = bool(HEADER_FAMILIES["flow_or_mass"].search(text))
    has_protocol = bool(HEADER_FAMILIES["protocol_or_control"].search(text))
    # A single synchronized export can contain both sides of the boundary;
    # classify it before the broader vehicle/dispenser bucket so it becomes a
    # useful P0 lead without persisting any headers or values.
    if (
        has_time
        and has_pressure
        and has_temperature
        and has_flow
        and has_protocol
        and RECEIVING_BOUNDARY.search(text)
        and STATION_BOUNDARY.search(text)
    ):
        return "full_loop_timeseries_candidate"
    # Public bench exports can contain source-side pressure plus receiving
    # vessel pressure/temperature and flow, but no controller phase channel.
    # Keep this separate from a full-loop candidate: it is useful for model
    # development, yet cannot open the protocol-provenance gate.
    if (
        has_time
        and has_pressure
        and has_temperature
        and has_flow
        and SOURCE_PRESSURE_CHANNEL.search(text)
        and not has_protocol
    ):
        return "boundary_bundle_missing_protocol_candidate"
    if HEADER_FAMILIES["vehicle_or_dispenser"].search(text):
        # A synchronized vehicle candidate needs a time axis and a flow/mass
        # field in addition to pressure and temperature.  Static QRA result
        # tables often mention dispenser, pressure and temperature but do not
        # contain a measured time series.
        if has_time and has_pressure and has_temperature and has_flow:
            return "vehicle_pressure_temperature_candidate"
        return "vehicle_or_dispenser_candidate"
    if HEADER_FAMILIES["protocol_or_control"].search(text):
        return "control_or_protocol_candidate"
    if HEADER_FAMILIES["flow_or_mass"].search(text):
        return "flow_or_mass_candidate"
    if HEADER_FAMILIES["pressure"].search(text):
        return "pressure_candidate"
    if HEADER_FAMILIES["temperature"].search(text):
        return "temperature_candidate"
    return "unclassified_machine_readable"


def _split_pair_signature(path: Path, header: list[str]) -> tuple[str, bool, bool] | None:
    """Return a private grouping key and station/receiving role flags.

    A split pair is only an *attestable lead*.  The key is retained in memory
    for the duration of the scan and is never returned.  Requiring a shared
    parent directory and a non-empty stem after removing explicit role words
    avoids pairing unrelated files that merely contain ``pressure`` and
    ``temperature`` in their headers.
    """

    if (
        path.suffix.lower() not in {".csv", ".tsv"}
        or STATIC_TEMPLATE_PATTERN.search(path.stem)
    ):
        return None
    text = " ".join(str(column) for column in header)
    has_time = any(TIME_PATTERN.search(str(column)) for column in header)
    has_pressure = bool(HEADER_FAMILIES["pressure"].search(text))
    has_temperature = bool(HEADER_FAMILIES["temperature"].search(text))
    has_flow = bool(HEADER_FAMILIES["flow_or_mass"].search(text))
    if not (has_time and has_pressure and has_temperature):
        return None
    stem = re.sub(r"\d{4}[-_]?\d{2}[-_]?\d{2}", "", path.stem.casefold())
    stem = SPLIT_ROLE_TOKENS.sub(" ", stem)
    stem = re.sub(r"(?:^|[_\- .])(?:trace|data|log|export|measurement)(?=$|[_\- .])", " ", stem)
    stem = re.sub(r"[^a-z0-9가-힣]+", " ", stem).strip()
    if not stem:
        return None
    # The parent path is an in-memory namespace only.  It prevents two
    # unrelated folders with the same event stem from being paired.
    key = f"{path.parent}\x1f{stem}"
    explicit_vehicle = bool(
        HEADER_FAMILIES["vehicle_or_dispenser"].search(path.stem)
        or HEADER_FAMILIES["vehicle_or_dispenser"].search(text)
    )
    return key, bool(has_flow and not explicit_vehicle), explicit_vehicle


def scan_workspace(
    roots: Iterable[Path],
    *,
    inspect_spreadsheets: bool = False,
    inspect_scientific: bool = False,
) -> dict:
    files = 0
    path_keyword_candidates = 0
    header_screened = 0
    header_family_counts: Counter[str] = Counter()
    coarse_classes: Counter[str] = Counter()
    parse_errors = 0
    spreadsheet_headers_screened = 0
    spreadsheet_parse_errors = 0
    scientific_headers_screened = 0
    scientific_parse_errors = 0
    split_groups: dict[str, tuple[bool, bool, int]] = {}
    full_loop_candidates = 0
    partial_loop_candidates = 0

    for path in _iter_files(roots):
        files += 1
        if PATH_KEYWORDS.search(path.stem):
            path_keyword_candidates += 1
        header = _read_header(
            path,
            inspect_spreadsheets=inspect_spreadsheets,
            inspect_scientific=inspect_scientific,
        )
        if path.suffix.lower() in {".csv", ".tsv"}:
            header_screened += 1
            if not header:
                parse_errors += 1
            for family, pattern in HEADER_FAMILIES.items():
                if any(pattern.search(str(column)) for column in header):
                    header_family_counts[family] += 1
        elif path.suffix.lower() == ".xlsx" and inspect_spreadsheets:
            spreadsheet_headers_screened += 1
            if not header:
                spreadsheet_parse_errors += 1
            for family, pattern in HEADER_FAMILIES.items():
                if any(pattern.search(str(column)) for column in header):
                    header_family_counts[family] += 1
        elif path.suffix.lower() in {".mat", ".h5", ".hdf5"} and inspect_scientific:
            scientific_headers_screened += 1
            if not header:
                scientific_parse_errors += 1
            for family, pattern in HEADER_FAMILIES.items():
                if any(pattern.search(str(column)) for column in header):
                    header_family_counts[family] += 1
        candidate_class = _classify_candidate(path, header)
        coarse_classes[candidate_class] += 1
        if candidate_class == "full_loop_timeseries_candidate":
            full_loop_candidates += 1
        elif candidate_class == "boundary_bundle_missing_protocol_candidate":
            partial_loop_candidates += 1
        split = _split_pair_signature(path, header)
        if split is not None:
            key, station_like, receiving_like = split
            old_station, old_receiving, old_count = split_groups.get(
                key, (False, False, 0)
            )
            split_groups[key] = (
                old_station or station_like,
                old_receiving or receiving_like,
                old_count + 1,
            )

    split_pair_candidates = sum(
        1
        for station_like, receiving_like, file_count in split_groups.values()
        if station_like and receiving_like and file_count >= 2
    )

    return {
        "schema_version": 1,
        "artifact_type": "privacy_bounded_local_workspace_candidate_scan",
        "status": "discovery_only",
        "generated_at": date.today().isoformat(),
        "privacy": {
            "source_paths_published": False,
            "source_filenames_published": False,
            "source_headers_published": False,
            "source_identifiers_published": False,
            "raw_rows_persisted": False,
            "candidate_values_persisted": False,
        },
        "scan": {
            "machine_readable_files": files,
            "path_keyword_candidates": path_keyword_candidates,
            "csv_tsv_headers_screened": header_screened,
            "header_parse_errors": parse_errors,
            "spreadsheet_headers_screened": spreadsheet_headers_screened,
            "spreadsheet_header_parse_errors": spreadsheet_parse_errors,
            "spreadsheet_inspection_enabled": inspect_spreadsheets,
            "scientific_headers_screened": scientific_headers_screened,
            "scientific_header_parse_errors": scientific_parse_errors,
            "scientific_inspection_enabled": inspect_scientific,
            "header_family_candidate_counts": dict(sorted(header_family_counts.items())),
            "coarse_candidate_classes": dict(sorted(coarse_classes.items())),
            "split_pair_candidate_count": split_pair_candidates,
        },
        "eligibility": {
            "full_loop_candidate_count": full_loop_candidates,
            "partial_loop_candidate_count": partial_loop_candidates,
            "split_pair_candidates_require_attestation": split_pair_candidates,
            "decision": "DISCOVERY_ONLY_UNTIL_ATTESTED",
            "required_attestation": [
                "common time base and units",
                "station/dispenser/vehicle boundary roles",
                "initial conditions and protocol state",
                "reuse rights and custodian confirmation",
            ],
        },
        "claim_boundary": (
            "Aggregate discovery counts only. Keyword or header matches do not prove "
            "measured status, synchronized station-to-vehicle coverage, or validation eligibility."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--inspect-spreadsheets",
        action="store_true",
        help="Inspect only XLSX header windows; never persist workbook values",
    )
    parser.add_argument(
        "--inspect-scientific",
        action="store_true",
        help="Inspect MATLAB/HDF5 variable names only; never persist numeric arrays",
    )
    args = parser.parse_args()
    result = scan_workspace(
        args.root,
        inspect_spreadsheets=args.inspect_spreadsheets,
        inspect_scientific=args.inspect_scientific,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
