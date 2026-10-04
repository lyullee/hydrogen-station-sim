"""Summarize the public USN ignited-release MAT archive without tuning a model.

The Figshare/DataverseNO files are MATLAB v7.3 (HDF5) containers.  This parser
keeps the raw archive outside the repository and writes only provenance and
deterministic descriptive measurements.  It is intentionally not a validation
score: the experiment-to-nozzle-angle mapping and the confined CFD boundary are
not encoded in the public MAT metadata, so no case-specific model fitting is
performed here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


EXPECTED_FILES = tuple(f"Exp_{index:05d}.mat" for index in range(1, 9))
MFR_ACTIVE_THRESHOLD_G_S = 0.5


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _array(dataset: Any) -> np.ndarray:
    return np.asarray(dataset[()]).reshape(-1).astype(float, copy=False)


def _longest_active_window(
    time_s: np.ndarray,
    mass_flow_g_s: np.ndarray,
) -> tuple[dict[str, float | int | None], tuple[int, int] | None]:
    finite = np.isfinite(time_s) & np.isfinite(mass_flow_g_s)
    mask = finite & (mass_flow_g_s >= MFR_ACTIVE_THRESHOLD_G_S)
    transitions = np.diff(np.r_[False, mask, False].astype(np.int8))
    starts = np.flatnonzero(transitions == 1)
    ends = np.flatnonzero(transitions == -1) - 1
    if not len(starts):
        return ({
            "threshold_g_s": MFR_ACTIVE_THRESHOLD_G_S,
            "start_s": None,
            "end_s": None,
            "sample_count": 0,
        }, None)
    index = max(range(len(starts)), key=lambda i: int(ends[i] - starts[i] + 1))
    start, end = int(starts[index]), int(ends[index])
    return ({
        "threshold_g_s": MFR_ACTIVE_THRESHOLD_G_S,
        "start_s": float(time_s[start]),
        "end_s": float(time_s[end]),
        "sample_count": end - start + 1,
    }, (start, end))


def _finite_peak(group: Any, name: str) -> float | None:
    if name not in group:
        return None
    values = _array(group[name])
    values = values[np.isfinite(values)]
    return float(np.max(values)) if values.size else None


def summarize_file(path: Path) -> dict[str, Any]:
    try:
        import h5py
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("Install the research extra (h5py) to parse MATLAB v7.3 files") from exc

    with h5py.File(path, "r") as root:
        required_groups = {"MFM", "HF", "Tank", "Vent"}
        missing_groups = sorted(required_groups.difference(root.keys()))
        if missing_groups:
            raise ValueError(f"{path.name}: missing groups {missing_groups}")
        mfm = root["MFM"]
        mfm_time = _array(mfm["time"])
        mfr = _array(mfm["mfr"])
        window, active_span = _longest_active_window(mfm_time, mfr)
        if active_span is not None:
            start, end = active_span
            mass_kg = float(np.trapezoid(np.maximum(mfr[start:end + 1], 0.0), mfm_time[start:end + 1]) / 1000.0)
            initial_pressure = float(np.nanmedian(_array(root["Tank"]["P"])[start:min(end + 1, start + 10)]))
            initial_temperature = float(np.nanmedian(_array(root["Tank"]["T"])[start:min(end + 1, start + 10)]))
        else:
            mass_kg = None
            initial_pressure = None
            initial_temperature = None
        heat_flux_peaks = {
            name: _finite_peak(root["HF"], name)
            for name in ("RHF1", "RHF2", "RHF3", "RHF4", "THF1", "THF2")
        }
        temperature_peaks = {
            name: _finite_peak(root["TS"], name)
            for name in ("TT1", "TT2", "TT3", "TT4", "TT5", "TT6", "TT7", "TT8", "TT9")
        } if "TS" in root else {}
        groups = {name: sorted(root[name].keys()) for name in ("MFM", "HF", "Tank", "Vent")}
        if "TS" in root:
            groups["TS"] = sorted(root["TS"].keys())
    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "groups": groups,
        "mfm_time_end_s": float(np.nanmax(mfm_time)),
        "mass_flow_max_g_s": float(np.nanmax(mfr)),
        "active_release_window": window,
        "integrated_positive_mass_kg": mass_kg,
        "initial_tank_pressure_bar": initial_pressure,
        "initial_tank_temperature_c": initial_temperature,
        "heat_flux_peaks": heat_flux_peaks,
        "temperature_peaks_c": temperature_peaks,
    }


def analyze(raw_dir: Path) -> dict[str, Any]:
    files = [raw_dir / name for name in EXPECTED_FILES]
    missing = [path.name for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing public MAT files: {', '.join(missing)}")
    cases = [summarize_file(path) for path in files]
    return {
        "schema_version": 1,
        "status": "descriptive_public_archive_replay_complete",
        "source_doi": "10.23642/usn.17695082.v1",
        "source_landing_page": "https://doi.org/10.23642/usn.17695082.v1",
        "license": "CC BY 4.0",
        "raw_directory": str(raw_dir),
        "file_selection": "All eight public MAT experiments in the source record, ordered by filename.",
        "release_window_rule": (
            "Use the longest contiguous MFM interval with mass flow >= 0.5 g/s; "
            "the threshold is a deterministic instrument-noise boundary, not a fitted event cutoff."
        ),
        "cases": cases,
        "case_count": len(cases),
        "claim_boundary": (
            "Descriptive consequence-data replay only. No case-specific fitting, "
            "CFD calibration, station full-loop validation, controller validation, "
            "LLM effectiveness claim or legal separation-distance claim is made."
        ),
        "raw_redistribution": "Raw MAT files remain external to the repository; only hashes and derived summaries are committed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.raw_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "case_count": result["case_count"], "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
