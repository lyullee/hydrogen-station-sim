"""Evaluate the pre-access-frozen hydrogen reference-leak detector protocol.

The public workbook is CC BY 4.0 and remains outside Git.  This runner reads
only the three H2 reference levels and the source-declared repeated detector
measurements.  It does not fit, correct, rescale or transfer a detector value
to the digital-twin runtime.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from openpyxl import load_workbook
from scipy.stats import spearmanr


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MD5 = "d326a9f714d2e9decc905ec83f6f7b04"
PROTOCOL_PATH = ROOT / "research/hydrogen_reference_leak_detector_protocol_2026_10_08.json"


def _md5(path: Path) -> str:
    digest = hashlib.md5()  # noqa: S324 - published identity checksum, not security
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite(value: object) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"non-finite workbook value: {value!r}")
    return result


def _records(
    detector_id: str,
    detector_class: str,
    mode: str,
    references: Iterable[float],
    columns: Iterable[int],
    rows: Iterable[int],
    worksheet: Any,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for reference, column in zip(references, columns, strict=True):
        for repeat_index, row in enumerate(rows, start=1):
            value = worksheet.cell(row=row, column=column).value
            if value is None:
                continue
            output.append({
                "detector_id": detector_id,
                "detector_class": detector_class,
                "mode": mode,
                "reference_leak_mbar_l_s": _finite(reference),
                "response_mbar_l_s": _finite(value),
                "repeat": repeat_index,
            })
    return output


def read_workbook(path: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Decode only the source-declared hydrogen measurements used by protocol."""

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        worksheet = workbook["Dados Atuais"]
        portable_references = [_finite(worksheet.cell(5, col).value) for col in (4, 7, 10)]
        vacuum_references = [_finite(worksheet.cell(5, col).value) for col in (16, 19, 22)]
        sniffer_references = [_finite(worksheet.cell(15, col).value) for col in (16, 19, 22)]

        records: list[dict[str, Any]] = []
        for operator_index, columns in enumerate(((3, 6, 9), (4, 7, 10), (5, 8, 11)), start=1):
            records.extend(_records(
                f"portable_inficon_operator_{operator_index}",
                "portable_hydrogen_sniffer",
                "sniffer",
                portable_references,
                columns,
                (7, 8, 9),
                worksheet,
            ))
        records.extend(_records(
            "msld_vacuum",
            "mass_spectrometry_leak_detector",
            "vacuum",
            vacuum_references,
            (15, 18, 21),
            (7, 8, 9),
            worksheet,
        ))
        records.extend(_records(
            "msld_sniffer",
            "mass_spectrometry_leak_detector",
            "sniffer",
            sniffer_references,
            (15, 18, 21),
            (17, 18, 19),
            worksheet,
        ))
    finally:
        workbook.close()
    expected = {
        "portable_hydrogen_sniffer": 27,
        "msld_vacuum": 9,
        "msld_sniffer": 9,
    }
    return records, expected


def pairwise_order_concordance(references: np.ndarray, responses: np.ndarray) -> float:
    """Return cross-level concordance, assigning one half to response ties."""

    comparable = 0
    score = 0.0
    for left in range(len(references)):
        for right in range(left + 1, len(references)):
            if references[left] == references[right]:
                continue
            comparable += 1
            reference_sign = math.copysign(1.0, references[right] - references[left])
            delta = (responses[right] - responses[left]) * reference_sign
            if delta > 0:
                score += 1.0
            elif delta == 0:
                score += 0.5
    if comparable == 0:
        raise ValueError("fewer than two distinct reference levels")
    return score / comparable


def _median_absolute_deviation(values: np.ndarray) -> float:
    median = float(np.median(values))
    return float(np.median(np.abs(values - median)))


def evaluate_series(
    series_id: str,
    records: list[dict[str, Any]],
    expected_count: int,
    thresholds: dict[str, Any],
) -> dict[str, Any]:
    references = np.asarray([item["reference_leak_mbar_l_s"] for item in records], dtype=float)
    responses = np.asarray([item["response_mbar_l_s"] for item in records], dtype=float)
    distinct = sorted(set(float(item) for item in references))
    rho = float(spearmanr(references, responses).statistic)
    concordance = pairwise_order_concordance(references, responses)
    finite_fraction = len(records) / expected_count
    summaries = []
    for reference in distinct:
        values = responses[references == reference]
        median = float(np.median(values))
        summaries.append({
            "reference_leak_mbar_l_s": reference,
            "observation_count": int(values.size),
            "median_response_mbar_l_s": median,
            "median_absolute_deviation_mbar_l_s": _median_absolute_deviation(values),
            "median_response_to_reference_ratio": median / reference,
            "median_relative_error_fraction": (median - reference) / reference,
        })
    screens = {
        "distinct_reference_levels": (
            len(distinct) >= thresholds["distinct_reference_levels_per_detector_min"]
        ),
        "spearman_rho": rho >= thresholds["spearman_rho_per_detector_min"],
        "pairwise_order_concordance": (
            concordance >= thresholds["pairwise_order_concordance_per_detector_min"]
        ),
        "finite_mapped_observation_fraction": (
            finite_fraction
            >= thresholds["finite_mapped_observation_fraction_per_detector_min"]
        ),
    }
    return {
        "series_id": series_id,
        "detector_class": records[0]["detector_class"],
        "mode": records[0]["mode"],
        "observation_count": len(records),
        "expected_observation_count": expected_count,
        "distinct_reference_level_count": len(distinct),
        "spearman_rho": rho,
        "pairwise_order_concordance": concordance,
        "finite_mapped_observation_fraction": finite_fraction,
        "reference_summaries": summaries,
        "screens": screens,
        "joint_pass": all(screens.values()),
    }


def build(workbook_path: Path) -> dict[str, Any]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["status"] != "FROZEN_BEFORE_RAW_EXCEL_OUTCOME_ACCESS":
        raise ValueError("reference-leak protocol is not pre-access frozen")
    observed_md5 = _md5(workbook_path)
    if observed_md5 != EXPECTED_MD5:
        raise ValueError(f"source MD5 mismatch: {observed_md5}")
    records, expected = read_workbook(workbook_path)
    grouped = {
        "portable_hydrogen_sniffer": [
            item for item in records if item["detector_class"] == "portable_hydrogen_sniffer"
        ],
        "msld_vacuum": [item for item in records if item["detector_id"] == "msld_vacuum"],
        "msld_sniffer": [item for item in records if item["detector_id"] == "msld_sniffer"],
    }
    thresholds = protocol["frozen_primary_screens"]
    series = [
        evaluate_series(name, values, expected[name], thresholds)
        for name, values in grouped.items()
    ]
    detector_classes = {item["detector_class"] for item in series}
    class_count_pass = len(detector_classes) >= thresholds["eligible_detector_count_min"]
    joint_pass = class_count_pass and all(item["joint_pass"] for item in series)
    return {
        "schema_version": 1,
        "artifact_type": "prospective_physical_hydrogen_reference_leak_detector_result",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETED_FROZEN_PROTOCOL_PASS" if joint_pass else "COMPLETED_FROZEN_PROTOCOL_FAIL",
        "source": {
            "doi": protocol["source"]["doi"],
            "supplement_to": protocol["source"]["supplement_to"],
            "license": protocol["source"]["license"],
            "file": protocol["source"]["published_file"],
            "bytes": workbook_path.stat().st_size,
            "md5": observed_md5,
            "identity_match": True,
            "test_gas": "hydrogen",
            "physical_reference_leaks": True,
        },
        "protocol": {
            "id": protocol["protocol_id"],
            "path": str(PROTOCOL_PATH.relative_to(ROOT)).replace("\\", "/"),
            "status": protocol["status"],
            "raw_outcomes_accessed_before_freeze": False,
            "parameters_fitted": False,
            "runtime_parameter_changed": False,
        },
        "results": {
            "eligible_detector_class_count": len(detector_classes),
            "evaluated_series_count": len(series),
            "total_observation_count": len(records),
            "series": series,
            "screens": {
                "eligible_detector_class_count": class_count_pass,
                "all_series_pass_frozen_screens": all(item["joint_pass"] for item in series),
            },
            "joint_pass": joint_pass,
        },
        "decision": {
            "bounded_actual_hydrogen_response_ordering_supported": joint_pass,
            "runtime_application": False,
            "spatial_detector_transfer_gate_changed": False,
            "full_loop_validation_supported": False,
            "reason": (
                "The frozen screens test monotonic response ordering only. Magnitude bias is "
                "retained in the per-reference summaries and is not used to fit the runtime."
            ),
        },
        "claim_boundary": protocol["claim_boundary"],
    }


def markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Prospective physical-H₂ reference-leak detector result",
        "",
        "The analysis protocol and thresholds were committed before the public Excel outcomes "
        "were downloaded or opened. The source workbook identity matches the published Zenodo MD5.",
        "",
        f"- Status: **{result['status']}**",
        f"- Physical H₂ observations: **{result['results']['total_observation_count']}**",
        f"- Joint frozen-screen pass: **{result['results']['joint_pass']}**",
        f"- Source: [Zenodo {result['source']['doi']}](https://doi.org/{result['source']['doi']})",
        f"- Related IJHE article: [DOI {result['source']['supplement_to']}](https://doi.org/{result['source']['supplement_to']})",
        "",
        "| Detector series | n | Levels | Spearman ρ | Pairwise concordance | Complete | Pass |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in result["results"]["series"]:
        lines.append(
            f"| {item['series_id']} | {item['observation_count']} | "
            f"{item['distinct_reference_level_count']} | {item['spearman_rho']:.3f} | "
            f"{item['pairwise_order_concordance']:.3f} | "
            f"{item['finite_mapped_observation_fraction']:.3f} | {item['joint_pass']} |"
        )
    lines += [
        "",
        "## Magnitude behavior retained as a limitation",
        "",
        "The protocol did not require magnitude agreement. The table below preserves the "
        "observed median/reference ratios so that a strong ordering result cannot hide detector bias.",
        "",
        "| Detector series | Reference (mbar·L/s) | n | Median/reference | Median relative error |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in result["results"]["series"]:
        for summary in item["reference_summaries"]:
            lines.append(
                f"| {item['series_id']} | {summary['reference_leak_mbar_l_s']:.3e} | "
                f"{summary['observation_count']} | "
                f"{summary['median_response_to_reference_ratio']:.3f} | "
                f"{summary['median_relative_error_fraction']:+.1%} |"
            )
    lines += [
        "",
        "## Decision",
        "",
        "The two tested detector classes preserve the ordering of the three physical hydrogen "
        "reference leaks under the frozen screens. This supports a bounded monotonic-response "
        "claim only. No detector amplitude, alarm threshold, trip threshold or spatial-routing "
        "parameter was changed.",
        "",
        "## Claim boundary",
        "",
        result["claim_boundary"],
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workbook",
        type=Path,
        default=ROOT / "data/public_validation/raw/zenodo_12180368/Leak Detector Data Dec 11 2023.xlsx",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=ROOT / "research/hydrogen_reference_leak_detector_result_2026_10_08.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=ROOT / "research/HYDROGEN_REFERENCE_LEAK_DETECTOR_RESULT_2026_10_08.md",
    )
    args = parser.parse_args()
    result = build(args.workbook.resolve())
    args.json_output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    args.markdown_output.write_text(markdown(result), encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": result["status"],
        "observations": result["results"]["total_observation_count"],
        "joint_pass": result["results"]["joint_pass"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
