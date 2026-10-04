#!/usr/bin/env python3
"""Audit the public USN ignited-release thermal-effects archive.

The archive contains MATLAB v7.3 files rather than a station logger export.
This runner therefore performs a deterministic data-integrity and descriptive
consequence replay only.  It deliberately does not fit parameters or call the
production consequence model, because the public record does not provide a
case-to-case nozzle/pressure/geometry mapping sufficient for an untouched
predictive comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np


SOURCE = {
    "doi": "10.23642/usn.17695082.v1",
    "landing_page": "https://doi.org/10.23642/usn.17695082.v1",
    "api_record": "https://api.figshare.com/v2/articles/17695082",
    "license": "CC BY 4.0",
}

EXPECTED = [f"Exp_{index:05d}.mat" for index in range(1, 9)]
REQUIRED = {
    "MFM": {"mfr", "P", "T", "time"},
    "Tank": {"P", "T", "time"},
    "Vent": {"ACH", "vfr", "T", "time"},
    "HF": {"RHF1", "RHF2", "RHF3", "RHF4", "THF1", "THF2", "time"},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _array(group: h5py.Group, name: str) -> np.ndarray:
    return np.asarray(group[name][:], dtype=float).reshape(-1)


def _time_stats(values: np.ndarray) -> dict[str, object]:
    values = values[np.isfinite(values)]
    deltas = np.diff(values)
    return {
        "count": int(values.size),
        "start_s": float(values[0]) if values.size else None,
        "end_s": float(values[-1]) if values.size else None,
        "monotonic_strict": bool(values.size and np.all(deltas > 0)),
        "median_interval_s": float(np.median(deltas)) if deltas.size else None,
    }


def _numeric_summary(values: np.ndarray, *, nonnegative_peak: bool = False) -> dict[str, float | int | None]:
    values = values[np.isfinite(values)]
    if not values.size:
        return {"count": 0, "min": None, "max": None, "peak_nonnegative": None}
    return {
        "count": int(values.size),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "peak_nonnegative": float(np.max(np.maximum(values, 0.0))) if nonnegative_peak else None,
    }


def _longest_active_window(time: np.ndarray, flow: np.ndarray, threshold_g_s: float) -> dict[str, object]:
    valid = np.isfinite(time) & np.isfinite(flow)
    time, flow = time[valid], flow[valid]
    active = flow >= threshold_g_s
    best: tuple[int, int] | None = None
    start = None
    for index, flag in enumerate(active):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            candidate = (start, index - 1)
            if best is None or candidate[1] - candidate[0] > best[1] - best[0]:
                best = candidate
            start = None
    if start is not None:
        candidate = (start, len(active) - 1)
        if best is None or candidate[1] - candidate[0] > best[1] - best[0]:
            best = candidate
    if best is None:
        return {"threshold_g_s": threshold_g_s, "sample_count": 0, "start_s": None, "end_s": None}
    first, last = best
    positive_mass_kg = float(np.trapezoid(np.maximum(flow[first : last + 1], 0.0), time[first : last + 1]) / 1000.0)
    return {
        "threshold_g_s": threshold_g_s,
        "sample_count": int(last - first + 1),
        "start_s": float(time[first]),
        "end_s": float(time[last]),
        "integrated_positive_mass_kg": positive_mass_kg,
    }


def _groups(file: h5py.File) -> dict[str, list[str]]:
    return {
        name: sorted(str(key) for key in file[name].keys())
        for name in sorted(file.keys())
        if isinstance(file[name], h5py.Group) and name != "#refs#"
    }


def _case(path: Path) -> dict[str, object]:
    with h5py.File(path, "r") as handle:
        groups = _groups(handle)
        missing = {
            group: sorted(keys - set(groups.get(group, [])))
            for group, keys in REQUIRED.items()
            if not keys.issubset(set(groups.get(group, [])))
        }
        mfm_time = _array(handle["MFM"], "time")
        mfr = _array(handle["MFM"], "mfr")
        tank_pressure = _array(handle["Tank"], "P")
        tank_temperature = _array(handle["Tank"], "T")
        release_window = _longest_active_window(mfm_time, mfr, 0.5)
        thermal = {
            name: _numeric_summary(_array(handle["HF"], name), nonnegative_peak=True)
            for name in ("RHF1", "RHF2", "RHF3", "RHF4", "THF1", "THF2")
        }
        temperatures = {}
        if "TS" in handle:
            temperatures = {
                name: _numeric_summary(_array(handle["TS"], name), nonnegative_peak=False)
                for name in ("TT1", "TT2", "TT3", "TT4", "TT5", "TT6", "TT7", "TT8", "TT9")
                if name in handle["TS"]
            }
        return {
            "file": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "groups": groups,
            "required_channel_missing": missing,
            "timebase": {
                "MFM": _time_stats(mfm_time),
                "Tank": _time_stats(_array(handle["Tank"], "time")),
                "Vent": _time_stats(_array(handle["Vent"], "time")),
                "HF": _time_stats(_array(handle["HF"], "time")),
            },
            "release_window": release_window,
            "mass_flow_g_s": _numeric_summary(mfr, nonnegative_peak=True),
            "tank_pressure_bar": _numeric_summary(tank_pressure),
            "tank_temperature_c": _numeric_summary(tank_temperature),
            "heat_flux_kw_m2": thermal,
            "temperature_c": temperatures,
        }


def run(raw_dir: Path, output: Path) -> dict[str, object]:
    cases = [_case(raw_dir / name) for name in EXPECTED if (raw_dir / name).is_file()]
    missing_files = [name for name in EXPECTED if not (raw_dir / name).is_file()]
    result = {
        "schema_version": 1,
        "status": "postfreeze_descriptive_consequence_replay_complete" if not missing_files else "incomplete_missing_raw_files",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE,
        "raw_directory": str(raw_dir),
        "file_selection": "All eight public MAT experiment files, ordered by source filename; no outcome-based exclusion.",
        "case_count": len(cases),
        "expected_case_count": len(EXPECTED),
        "missing_files": missing_files,
        "cases": cases,
        "documented_units": {
            "MFM/mfr": "g/s",
            "MFM/P": "bar",
            "MFM/T": "degC",
            "Tank/P": "bar",
            "Tank/T": "degC",
            "HF/RHF*": "kW/m2",
            "HF/THF*": "kW/m2",
            "TS/TT*": "degC",
            "Vent/ACH": "1/h",
            "Vent/vfr": "m3/h",
        },
        "claim_boundary": (
            "Descriptive, post-freeze consequence-data replay only. The public record does not expose "
            "a frozen case-to-case nozzle/geometry mapping sufficient for an untouched predictive HyRAM "
            "comparison; this is not predictive validation. No parameter fitting, CFD calibration, station full-loop validation, controller "
            "validation, LLM effectiveness claim or legal separation-distance claim is made."
        ),
        "raw_redistribution": "Raw MAT files remain external to the repository; only hashes and derived summaries are committed.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.raw_dir, args.output)
    print(json.dumps({"status": result["status"], "case_count": result["case_count"], "missing_files": result["missing_files"]}))
    return 0 if result["status"] == "postfreeze_descriptive_consequence_replay_complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
