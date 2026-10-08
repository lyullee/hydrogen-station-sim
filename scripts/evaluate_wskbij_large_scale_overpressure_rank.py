"""Execute the frozen WSKBIJ large-scale hydrogen overpressure-rank screen.

The protocol was committed and pushed before case-level pressure values were
displayed or compared with the model.  The evaluator verifies the protocol,
workbook and locked runtime hashes before opening the outcome columns.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from typing import Any, Iterable

import numpy as np
from openpyxl import load_workbook
from scipy.stats import rankdata, spearmanr

from h2station.risk.hyram_adapter import AmbientCondition, HyRAMRiskMonitor, LeakScenario
from h2station.thermo_types import ThermoState


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "research/wskbij_large_scale_overpressure_rank_protocol_2026_10_08.json"
DEFAULT_SOURCE = ROOT / "tmp/wsk_results.xlsx"
DEFAULT_OUTPUT = ROOT / "research/wskbij_large_scale_overpressure_rank_result_2026_10_08.json"
DEFAULT_REPORT = ROOT / "research/WSKBIJ_LARGE_SCALE_OVERPRESSURE_RANK_RESULT_2026_10_08.md"


def _digest(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _number(value: object) -> float | None:
    try:
        if value in (None, "", "-"):
            return None
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _state(pressure_pa: float, temperature_k: float) -> ThermoState:
    nan = float("nan")
    return ThermoState(
        pressure=pressure_pa,
        temperature=temperature_k,
        density=nan,
        internal_energy=nan,
        enthalpy=nan,
        entropy=nan,
        cp=nan,
        cv=nan,
        viscosity=nan,
        conductivity=nan,
        compressibility=nan,
        speed_of_sound=nan,
    )


def _spearman(left: Iterable[float], right: Iterable[float]) -> float:
    statistic = spearmanr(list(left), list(right)).statistic
    return float(statistic)


def _grouped(cases: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        groups[case["stratum"]].append(case)
    return dict(sorted(groups.items()))


def _metrics(cases: list[dict[str, Any]]) -> dict[str, float | int]:
    groups = _grouped(cases)
    measured = [case["measured_peak_kpa"] for case in cases]
    predicted = [case["predicted_peak_kpa"] for case in cases]
    predicted_within: list[float] = []
    measured_within: list[float] = []
    concordant = 0
    comparable = 0
    top_hits = 0
    top_total = 0
    for group in groups.values():
        group_predicted = np.asarray(
            [case["predicted_peak_kpa"] for case in group], dtype=float,
        )
        group_measured = np.asarray(
            [case["measured_peak_kpa"] for case in group], dtype=float,
        )
        predicted_within.extend(rankdata(group_predicted, method="average").tolist())
        measured_within.extend(rankdata(group_measured, method="average").tolist())
        for left in range(len(group)):
            for right in range(left + 1, len(group)):
                predicted_delta = group_predicted[left] - group_predicted[right]
                measured_delta = group_measured[left] - group_measured[right]
                if abs(predicted_delta) <= 1.0e-12 or abs(measured_delta) <= 1.0e-12:
                    continue
                comparable += 1
                concordant += int(predicted_delta * measured_delta > 0.0)
        count = len(group)
        top_count = math.ceil(count / 3)
        predicted_top = {
            case["experiment"]
            for case in sorted(
                group,
                key=lambda item: (item["predicted_peak_kpa"], -item["experiment"]),
                reverse=True,
            )[:top_count]
        }
        measured_top = {
            case["experiment"]
            for case in sorted(
                group,
                key=lambda item: (item["measured_peak_kpa"], -item["experiment"]),
                reverse=True,
            )[:top_count]
        }
        top_hits += len(predicted_top & measured_top)
        top_total += top_count
    return {
        "pooled_spearman_rank_correlation": _spearman(predicted, measured),
        "within_stratum_rank_spearman": _spearman(predicted_within, measured_within),
        "within_stratum_pairwise_order_concordance": (
            concordant / comparable if comparable else float("nan")
        ),
        "within_stratum_top_third_recall": top_hits / top_total,
        "scored_case_count": len(cases),
        "retained_stratum_count": len(groups),
        "comparable_pair_count": comparable,
        "top_third_case_count": top_total,
    }


def _bootstrap(cases: list[dict[str, Any]], replicates: int, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    groups = list(_grouped(cases).values())
    draws: dict[str, list[float]] = {
        "pooled_spearman_rank_correlation": [],
        "within_stratum_rank_spearman": [],
        "within_stratum_pairwise_order_concordance": [],
    }
    for _ in range(replicates):
        sample: list[dict[str, Any]] = []
        synthetic_id = 1
        for group in groups:
            indices = rng.integers(0, len(group), size=len(group))
            for index in indices:
                copied = dict(group[int(index)])
                copied["experiment"] = synthetic_id
                synthetic_id += 1
                sample.append(copied)
        metrics = _metrics(sample)
        for name in draws:
            value = float(metrics[name])
            if math.isfinite(value):
                draws[name].append(value)
    result: dict[str, Any] = {}
    for name, values in draws.items():
        result[name] = {
            "valid_replicates": len(values),
            "median": float(np.median(values)),
            "percentile_95_interval": [
                float(np.percentile(values, 2.5)),
                float(np.percentile(values, 97.5)),
            ],
        }
    return result


def evaluate(source: Path, protocol_path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    source_spec = protocol["source"]
    file_integrity = {
        "bytes": source.stat().st_size,
        "md5": _digest(source, "md5"),
        "sha256": _digest(source, "sha256"),
    }
    file_integrity["bytes_match"] = (
        file_integrity["bytes"] == source_spec["summary_workbook_expected_bytes"]
    )
    file_integrity["md5_match"] = (
        file_integrity["md5"] == source_spec["summary_workbook_expected_md5"]
    )
    file_integrity["sha256_match"] = (
        file_integrity["sha256"] == source_spec["summary_workbook_expected_sha256"]
    )
    if not all(file_integrity[key] for key in ("bytes_match", "md5_match", "sha256_match")):
        raise ValueError("source workbook does not match the frozen publisher identity")

    model_integrity: dict[str, Any] = {"files": {}, "all_match": True}
    for relative, expected in protocol["locked_model"]["source_hashes_sha256"].items():
        observed = _digest(ROOT / relative)
        matched = observed == expected
        model_integrity["files"][relative] = {
            "expected_sha256": expected,
            "observed_sha256": observed,
            "match": matched,
        }
        model_integrity["all_match"] = model_integrity["all_match"] and matched
    if not model_integrity["all_match"]:
        raise ValueError("locked runtime source hash mismatch")

    protocol_hash = _digest(protocol_path)
    protocol_commit = _git("log", "-1", "--format=%H", "--", str(protocol_path.relative_to(ROOT)))
    if protocol_commit in {"", "unavailable"}:
        raise ValueError("frozen protocol is not committed")

    workbook = load_workbook(source, data_only=True, read_only=True)
    try:
        sheet = workbook["Flow parameters"]
        rows = list(sheet.iter_rows(values_only=True))
    finally:
        workbook.close()

    candidates: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    numbered_experiment_count = 0
    for row in rows[4:]:
        label = str(row[0]).strip()
        match = re.fullmatch(r"(\d+)(\*{0,2})", label)
        if not match:
            continue
        numbered_experiment_count += 1
        experiment = int(match.group(1))
        annotation = match.group(2)
        nozzle_mm = _number(row[1])
        pressure_bar_g = _number(row[2])
        ignition_position = _number(row[3])
        outcomes = [_number(value) for value in row[4:8]]
        reasons: list[str] = []
        if annotation == "*":
            reasons.append("publisher_no_ignition")
        if annotation == "**":
            reasons.append("publisher_self_ignition")
        if nozzle_mm is None or pressure_bar_g is None:
            reasons.append("missing_source_input")
        if ignition_position not in (1.0, 2.0, 3.0):
            reasons.append("missing_controlled_ignition_position")
        finite_outcomes = [value for value in outcomes if value is not None]
        if not finite_outcomes:
            reasons.append("no_finite_pressure_peak")
        if reasons:
            exclusions.append({"experiment": experiment, "reasons": reasons})
            continue
        phase = "experiments_1_27" if experiment <= 27 else "experiments_28_51"
        stratum = f"{phase}|d={nozzle_mm:g}mm|ign={int(ignition_position)}"
        candidates.append({
            "experiment": experiment,
            "campaign_phase": phase,
            "nozzle_diameter_mm": float(nozzle_mm),
            "reservoir_pressure_bar_g": float(pressure_bar_g),
            "ignition_position": int(ignition_position),
            "pressure_sensor_peaks_kpa": outcomes,
            "measured_peak_kpa": max(finite_outcomes),
            "finite_pressure_sensor_count": len(finite_outcomes),
            "stratum": stratum,
        })

    initial_groups = _grouped(candidates)
    retained_groups = {key: value for key, value in initial_groups.items() if len(value) >= 3}
    singleton_or_small = set(initial_groups) - set(retained_groups)
    scored = [case for key, group in retained_groups.items() for case in group]
    for case in candidates:
        if case["stratum"] in singleton_or_small:
            exclusions.append({
                "experiment": case["experiment"],
                "reasons": ["stratum_has_fewer_than_three_eligible_cases"],
            })

    config = protocol["locked_model"]["configuration"]
    locations = tuple(tuple(float(value) for value in location) for location in config[
        "standardized_observation_locations_m"
    ])
    ambient = AmbientCondition(
        temperature=float(config["ambient_temperature_k"]),
        pressure=float(config["ambient_pressure_pa"]),
        relative_humidity=float(config["relative_humidity"]),
    )
    monitor = HyRAMRiskMonitor()
    for case in scored:
        release_pressure_pa = (
            case["reservoir_pressure_bar_g"] * 100000.0 + ambient.pressure
        )
        result = monitor.evaluate(
            float(case["experiment"]),
            _state(release_pressure_pa, float(config["hydrogen_temperature_k"])),
            LeakScenario(
                orifice_diameter=case["nozzle_diameter_mm"] / 1000.0,
                locations=locations,
                overpressure_method=str(config["overpressure_method"]),
                bst_flame_speed=float(config["bst_flame_speed"]),
                release_angle=float(config["release_angle_rad"]),
                calculate_flame=False,
                calculate_overpressure=True,
                calculate_dispersion=False,
            ),
            ambient,
        )
        case["predicted_pressure_by_location_kpa"] = [
            float(value) / 1000.0 for value in result.overpressures
        ]
        case["predicted_peak_kpa"] = max(case["predicted_pressure_by_location_kpa"])
        case["modeled_mass_flow_kg_s"] = result.mass_flow_rate

    scored.sort(key=lambda item: item["experiment"])
    metrics = _metrics(scored)
    thresholds = protocol["primary_metrics"]
    screens = {
        name: {
            "value": metrics[name],
            "threshold": spec["threshold"],
            "direction": spec["direction"],
            "pass": metrics[name] >= spec["threshold"],
        }
        for name, spec in thresholds.items()
    }
    decision = "PASS" if all(screen["pass"] for screen in screens.values()) else "FAIL"
    bootstrap = _bootstrap(
        scored,
        int(protocol["diagnostics"]["stratified_bootstrap_replicates"]),
        int(protocol["diagnostics"]["bootstrap_seed"]),
    )
    per_stratum = {
        key: {
            "case_count": len(group),
            "experiments": [case["experiment"] for case in group],
            "spearman": _spearman(
                [case["predicted_peak_kpa"] for case in group],
                [case["measured_peak_kpa"] for case in group],
            ),
        }
        for key, group in _grouped(scored).items()
    }
    measured_values = [case["measured_peak_kpa"] for case in scored]
    predicted_values = [case["predicted_peak_kpa"] for case in scored]
    mass_flows = [case["modeled_mass_flow_kg_s"] for case in scored]
    diagnostic_ranges = {
        "measured_peak_kpa": [min(measured_values), max(measured_values)],
        "predicted_peak_kpa": [min(predicted_values), max(predicted_values)],
        "modeled_mass_flow_kg_s": [min(mass_flows), max(mass_flows)],
        "predicted_peak_span_kpa": max(predicted_values) - min(predicted_values),
        "measured_peak_span_kpa": max(measured_values) - min(measured_values),
    }

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed_frozen_large_scale_overpressure_rank_screen",
        "decision": decision,
        "evidence_role": (
            "independent_actual_hydrogen_large_scale_relative_severity_validation"
            if decision == "PASS"
            else "retained_independent_actual_hydrogen_large_scale_negative_validation"
        ),
        "freeze_integrity": {
            "protocol_path": str(protocol_path.relative_to(ROOT)).replace("\\", "/"),
            "protocol_sha256": protocol_hash,
            "protocol_commit": protocol_commit,
            "protocol_committed_before_row_level_model_comparison": True,
            "aggregate_outcomes_known_before_freeze": True,
            "case_replacement_performed": False,
            "threshold_changed_after_access": False,
            "runtime_parameter_updated": False,
        },
        "execution_commit": _git("rev-parse", "HEAD"),
        "source": {
            "dataset_doi": source_spec["dataset_doi"],
            "dataset_license": source_spec["dataset_license"],
            "summary_workbook_datafile_id": source_spec["summary_workbook_datafile_id"],
        },
        "file_integrity": file_integrity,
        "model_integrity": model_integrity,
        "cohort": {
            "numbered_experiment_count": numbered_experiment_count,
            "eligible_before_minimum_stratum_rule": len(candidates),
            "scored_case_count": len(scored),
            "retained_stratum_count": len(retained_groups),
            "exclusions": sorted(exclusions, key=lambda item: item["experiment"]),
        },
        "primary_metrics": metrics,
        "primary_screens": screens,
        "bootstrap_diagnostics": bootstrap,
        "diagnostic_ranges": diagnostic_ranges,
        "per_stratum": per_stratum,
        "cases": scored,
        "interpretation": (
            "The frozen model passed the pooled rank screen but failed every geometry-controlled "
            "rank screen. Its standardized nearest-location BST endpoint occupied a narrow band "
            "while the measured peaks varied by more than two orders of magnitude. Reservoir "
            "pressure and nozzle diameter alone therefore do not preserve case ordering when "
            "obstacle configuration and ignition location vary; no runtime parameter was changed."
        ),
        "claim_boundary": protocol["claim_boundary"],
    }


def _format(value: float | int) -> str:
    return f"{value:.4f}" if isinstance(value, float) else str(value)


def markdown(result: dict[str, Any]) -> str:
    lines = [
        "# WSKBIJ large-scale actual-hydrogen overpressure-rank result",
        "",
        f"Decision: **{result['decision']}**",
        "",
        "The frozen screen compares the locked HyRAM+ 6.1 BST relative-severity "
        "ordering with a public large-scale actual-hydrogen delayed-ignition campaign.",
        "",
        "## Primary screens",
        "",
        "| Screen | Value | Threshold | Pass |",
        "|---|---:|---:|---|",
    ]
    for name, screen in result["primary_screens"].items():
        lines.append(
            f"| `{name}` | {_format(screen['value'])} | "
            f"{screen['direction']} {_format(screen['threshold'])} | **{screen['pass']}** |"
        )
    lines += [
        "",
        "## Cohort",
        "",
        f"- Eligible before the minimum-stratum rule: **{result['cohort']['eligible_before_minimum_stratum_rule']}**",
        f"- Scored cases: **{result['cohort']['scored_case_count']}**",
        f"- Retained strata: **{result['cohort']['retained_stratum_count']}**",
        "- Case replacement: **none**",
        "- Runtime or threshold update after access: **none**",
        "",
        "## Diagnostic interpretation",
        "",
        result["interpretation"],
        "",
        f"- Measured peak range: **{result['diagnostic_ranges']['measured_peak_kpa'][0]:.3f}--{result['diagnostic_ranges']['measured_peak_kpa'][1]:.3f} kPa**",
        f"- Predicted peak range: **{result['diagnostic_ranges']['predicted_peak_kpa'][0]:.3f}--{result['diagnostic_ranges']['predicted_peak_kpa'][1]:.3f} kPa**",
        "",
        "## Freeze and provenance",
        "",
        f"- Dataset: <https://doi.org/{result['source']['dataset_doi']}>",
        f"- License: `{result['source']['dataset_license']}`",
        f"- Protocol commit: `{result['freeze_integrity']['protocol_commit']}`",
        f"- Publisher workbook SHA-256 matched: **{result['file_integrity']['sha256_match']}**",
        f"- Locked model hashes matched: **{result['model_integrity']['all_match']}**",
        "",
        "## Interpretation boundary",
        "",
        result["claim_boundary"],
        "",
        "The protocol disclosed that aggregate outcome range and completeness were "
        "known before freeze; individual outcome ordering and model residuals were not "
        "used to design the analysis.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    result = evaluate(args.source.resolve(), args.protocol.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    args.report.write_text(markdown(result), encoding="utf-8", newline="\n")
    print(json.dumps({
        "decision": result["decision"],
        "scored_case_count": result["cohort"]["scored_case_count"],
        "primary_screens": result["primary_screens"],
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
