"""Prospective trend validation for a public hydrogen-blend release dataset.

The source archive reports spatial concentration fields for three hydrogen
blend fractions and three release-volume conditions.  The public metadata do
not expose enough apparatus detail for an absolute concentration comparison,
so this module evaluates only a pre-declared qualitative transfer claim:
larger hydrogen fraction and larger release volume must produce a larger
upper-tail hydrogen response.

The extraction rules deliberately avoid outcome-specific column selection.
Concentration-labelled columns are preferred; otherwise the first numeric
column is treated as a coordinate/index and the remaining numeric cells are
used.  This fallback is recorded in every result.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import csv
import math
from pathlib import Path
import re
from statistics import median
from typing import Iterable


BLEND_CASES = {
    "hydrogenAll10%.csv": 10.0,
    "hydrogenAll20%.csv": 20.0,
    "hydrogenAll30%.csv": 30.0,
}
RELEASE_CASES = {
    "H-232.csv": 232.0,
    "H-325.csv": 325.0,
    "H-476.csv": 476.0,
}


@dataclass(frozen=True)
class CaseResponse:
    file_name: str
    driver_value: float
    response_q90: float
    finite_response_count: int
    extraction_mode: str


@dataclass(frozen=True)
class TrendScreen:
    case_count: int
    spearman: float | None
    endpoint_ratio: float | None
    strictly_increasing: bool
    pass_screen: bool


def _number(value: str) -> float | None:
    text = str(value or "").strip().replace("%", "")
    if not text:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def _normalise_header(value: str) -> str:
    return re.sub(r"[^a-z0-9%]+", "", str(value or "").lower())


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _decode(path: Path) -> str:
    payload = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "cp1252"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Unable to decode CSV: {path.name}")


def extract_case_response(path: Path, driver_value: float) -> CaseResponse:
    text = _decode(path)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(text.splitlines(), dialect))
    if len(rows) < 2:
        raise ValueError(f"CSV has fewer than two rows: {path.name}")

    headers = [_normalise_header(value) for value in rows[0]]
    labelled = [
        index
        for index, header in enumerate(headers)
        if any(token in header for token in ("hydrogen", "h2", "concentration", "vol%"))
    ]
    if labelled:
        selected = labelled
        mode = "concentration_labelled_columns"
    else:
        width = max(len(row) for row in rows[1:])
        if width < 2:
            raise ValueError(f"CSV lacks a response column: {path.name}")
        selected = list(range(1, width))
        mode = "fallback_exclude_first_numeric_coordinate_column"

    values: list[float] = []
    for row in rows[1:]:
        for index in selected:
            if index >= len(row):
                continue
            value = _number(row[index])
            if value is not None and value >= 0.0:
                values.append(value)
    if len(values) < 3:
        raise ValueError(f"CSV has fewer than three finite response values: {path.name}")
    return CaseResponse(
        file_name=path.name,
        driver_value=float(driver_value),
        response_q90=_percentile(values, 0.90),
        finite_response_count=len(values),
        extraction_mode=mode,
    )


def _ranks(values: Iterable[float]) -> list[float]:
    sequence = list(values)
    result = [0.0] * len(sequence)
    for value in sorted(set(sequence)):
        indices = [index for index, item in enumerate(sequence) if item == value]
        rank = 1.0 + sum(1 for item in sequence if item < value)
        average = rank + (len(indices) - 1) / 2.0
        for index in indices:
            result[index] = average
    return result


def _pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y) or len(x) < 2:
        return None
    x_mid = median(x)
    y_mid = median(y)
    numerator = sum((a - x_mid) * (b - y_mid) for a, b in zip(x, y))
    x_scale = math.sqrt(sum((a - x_mid) ** 2 for a in x))
    y_scale = math.sqrt(sum((b - y_mid) ** 2 for b in y))
    if x_scale <= 0.0 or y_scale <= 0.0:
        return None
    return numerator / (x_scale * y_scale)


def evaluate_trend(cases: list[CaseResponse]) -> TrendScreen:
    ordered = sorted(cases, key=lambda case: case.driver_value)
    responses = [case.response_q90 for case in ordered]
    spearman = _pearson(
        _ranks(case.driver_value for case in ordered),
        _ranks(responses),
    )
    endpoint_ratio = None
    if responses and responses[0] > 0.0:
        endpoint_ratio = responses[-1] / responses[0]
    increasing = all(b > a for a, b in zip(responses, responses[1:]))
    passed = bool(
        len(ordered) == 3
        and spearman is not None
        and spearman >= 0.8
        and endpoint_ratio is not None
        and endpoint_ratio > 1.0
        and increasing
    )
    return TrendScreen(
        case_count=len(ordered),
        spearman=spearman,
        endpoint_ratio=endpoint_ratio,
        strictly_increasing=increasing,
        pass_screen=passed,
    )


def evaluate_archive(directory: Path) -> dict[str, object]:
    def key(name: str) -> str:
        return re.sub(r"\s+", "", name).lower()

    files = {key(path.name): path for path in directory.rglob("*.csv")}

    def load(group: dict[str, float]) -> list[CaseResponse]:
        missing = [name for name in group if key(name) not in files]
        if missing:
            raise FileNotFoundError("Missing frozen cases: " + ", ".join(missing))
        return [
            extract_case_response(files[key(name)], driver)
            for name, driver in group.items()
        ]

    blend = load(BLEND_CASES)
    release = load(RELEASE_CASES)
    blend_screen = evaluate_trend(blend)
    release_screen = evaluate_trend(release)
    return {
        "cases": {
            "blend_fraction": [asdict(case) for case in blend],
            "release_volume": [asdict(case) for case in release],
        },
        "screens": {
            "blend_fraction": asdict(blend_screen),
            "release_volume": asdict(release_screen),
        },
        "joint_primary_screen_pass": (
            blend_screen.pass_screen and release_screen.pass_screen
        ),
    }


__all__ = [
    "BLEND_CASES",
    "RELEASE_CASES",
    "CaseResponse",
    "TrendScreen",
    "evaluate_archive",
    "evaluate_trend",
    "extract_case_response",
]
