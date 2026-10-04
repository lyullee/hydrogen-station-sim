"""Replay a small, hash-identified subset of the public USN ignited archive.

This is a channel/time-base integrity replay, not a fitted consequence-model
validation.  The three selected files are pressure-peaking experiments from
the CC BY 4.0 DataverseNO record.  Their synchronized SIGMA and GEN3i arrays
are summarized without copying the raw files into the repository.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import loadmat


FILES: tuple[dict[str, Any], ...] = (
    {
        "datafile_id": 266075,
        "name": "HTE341USN0029READ191111.mat",
        "bytes": 42508034,
        "md5": "d93dab6ece1ea477825d35de4ff56344",
    },
    {
        "datafile_id": 266076,
        "name": "HTE341USN0030READ191111.mat",
        "bytes": 43239997,
        "md5": "6012e3a7e92c43dced63312288f46425",
    },
    {
        "datafile_id": 266077,
        "name": "HTE341USN0031READ191111.mat",
        "bytes": 43807775,
        "md5": "62d0637fe5ed0710589bb5b0482f82bd",
    },
)


def _hashes(path: Path) -> dict[str, Any]:
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            md5.update(block)
            sha256.update(block)
    return {"bytes": path.stat().st_size, "md5": md5.hexdigest(), "sha256": sha256.hexdigest()}


def _finite_range(values: np.ndarray) -> list[float]:
    finite = np.asarray(values, dtype=float)[np.isfinite(values)]
    return [float(np.min(finite)), float(np.max(finite))]


def _replay(path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    observed = _hashes(path) if path.is_file() else None
    item: dict[str, Any] = {
        **expected,
        "present": path.is_file(),
        "observed_file": observed,
        "identity_match": bool(
            observed
            and observed["bytes"] == expected["bytes"]
            and observed["md5"] == expected["md5"]
        ),
        "channel_replay": None,
    }
    if not path.is_file():
        return item
    data = loadmat(path, squeeze_me=True, struct_as_record=False)
    sigma = np.asarray(data["SIGMA"], dtype=float)
    gen3i = np.asarray(data["GEN3i"], dtype=float)
    sigma_time = sigma[:, 0]
    gen_time = gen3i[:, 0]
    item["channel_replay"] = {
        "sigma_shape": list(sigma.shape),
        "gen3i_shape": list(gen3i.shape),
        "sigma_columns": ["time_s", "mass_flow_g_s", "coriolis_pressure_bar", "T1_C", "T2_C", "T3_C", "T4_C"],
        "gen3i_columns": ["time_s", "unused_channel", "overpressure_kpa"],
        "sigma_time_range_s": [float(sigma_time[0]), float(sigma_time[-1])],
        "gen3i_time_range_s": [float(gen_time[0]), float(gen_time[-1])],
        "sigma_time_monotonic": bool(np.all(np.diff(sigma_time) > 0)),
        "gen3i_time_monotonic": bool(np.all(np.diff(gen_time) > 0)),
        "sigma_finite": bool(np.isfinite(sigma).all()),
        "gen3i_finite": bool(np.isfinite(gen3i).all()),
        "mass_flow_g_s_range": _finite_range(sigma[:, 1]),
        "coriolis_pressure_bar_range": _finite_range(sigma[:, 2]),
        "temperature_c_range": _finite_range(sigma[:, 3:7]),
        "overpressure_kpa_range": _finite_range(gen3i[:, 2]),
        "peak_mass_flow_g_s": float(np.max(sigma[:, 1])),
        "peak_mass_flow_time_s": float(sigma[np.argmax(sigma[:, 1]), 0]),
        "peak_overpressure_kpa": float(np.max(gen3i[:, 2])),
        "peak_overpressure_time_s": float(gen3i[np.argmax(gen3i[:, 2]), 0]),
    }
    return item


def build(raw_directory: Path) -> dict[str, Any]:
    files = [_replay(raw_directory / item["name"], item) for item in FILES]
    channel_ok = all(
        item["identity_match"]
        and item["channel_replay"]
        and item["channel_replay"]["sigma_shape"] == [999999, 7]
        and item["channel_replay"]["gen3i_shape"][1] == 3
        and item["channel_replay"]["sigma_time_monotonic"]
        and item["channel_replay"]["gen3i_time_monotonic"]
        and item["channel_replay"]["sigma_finite"]
        and item["channel_replay"]["gen3i_finite"]
        for item in files
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "completed_raw_channel_timebase_replay",
        "source": {
            "doi": "10.23642/USN.17934047",
            "record": "https://dataverse.no/dataset.xhtml?persistentId=doi:10.23642/USN.17934047",
            "api": "https://dataverse.no/api/datasets/:persistentId/?persistentId=doi%3A10.23642%2FUSN.17934047",
            "license": "CC BY 4.0",
            "scope": "confined ignited hydrogen releases with Coriolis mass flow, upstream pressure, four thermocouples and GEN3i overpressure",
        },
        "raw_directory": str(raw_directory).replace("\\", "/"),
        "files": files,
        "replay_integrity": {
            "file_count": len(files),
            "all_files_present": all(item["present"] for item in files),
            "all_file_identities_match": all(item["identity_match"] for item in files),
            "all_channel_replays_valid": channel_ok,
            "common_sigma_time_basis_s": [0.0001, 99.9999],
            "model_comparison_performed": False,
        },
        "eligibility": {
            "consequence_component_evidence": channel_ok,
            "full_loop_station_vehicle_holdout_eligible": False,
            "saga_effectiveness_eligible": False,
            "reason": "This subset has release/overpressure channels but no gaseous H70 station controller, cascade, dispenser protocol or vehicle-side fueling loop.",
        },
        "claim_boundary": "The replay establishes provenance and synchronized channel integrity for three public ignited-release experiments. It does not validate the production consequence model, flame/radiation distance, station controls, emergency separation distance or SAGA effectiveness.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-directory", type=Path, default=Path("tmp/usn_17934047"))
    parser.add_argument("--output", type=Path, default=Path("research/usn_17934047_raw_subset_replay_2026_10_05.json"))
    args = parser.parse_args()
    payload = build(args.raw_directory)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
