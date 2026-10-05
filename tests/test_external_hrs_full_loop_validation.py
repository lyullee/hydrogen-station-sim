import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from intake_external_hrs_bundle import build_manifest  # noqa: E402
from validate_external_hrs_full_loop import validate_full_loop_trace  # noqa: E402


def _inputs(tmp_path: Path, *, omit: str | None = None):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    columns = [
        "time_s",
        "vehicle_pressure_mpa_abs",
        "temperature_degC",
        "mass_flow_g_s",
        "station_pressure_mpa_abs",
        "delivered_gas_temperature_degC",
        "cascade_source_pressure_mpa_abs",
        "cascade_selected_bank",
        "compressor_state",
        "precooler_state",
        "leak_check_state",
        "vent_state",
        "fault_state",
        "esd_state",
    ]
    if omit:
        columns.remove(omit)
    trace = bundle / "event.csv"
    with trace.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for index in range(20):
            row = {
                "time_s": str(index),
                "vehicle_pressure_mpa_abs": str(5 + index),
                "temperature_degC": "-40",
                "mass_flow_g_s": "10",
                "station_pressure_mpa_abs": str(8 + index),
                "delivered_gas_temperature_degC": "-35",
                "cascade_source_pressure_mpa_abs": "80",
                "cascade_selected_bank": "medium",
                "compressor_state": "running",
                "precooler_state": "ready",
                "leak_check_state": "passed",
                "vent_state": "closed",
                "fault_state": "none",
                "esd_state": "armed",
            }
            writer.writerow({key: value for key, value in row.items() if key in columns})
    protocol = ROOT / "research/external_hrs_intake_protocol.json"
    manifest = build_manifest(bundle, protocol)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    declaration = {
        "declaration_type": "external_hrs_bundle_metadata",
        "outcomes_accessed_before_freeze": False,
        "channels": {
            "common_time_base": {"present": True},
            "vehicle_or_receptacle_pressure": {"present": True, "unit": "MPa_abs"},
            "gas_or_tank_temperature": {"present": True, "unit": "degC"},
            "mass_flow_or_transferred_mass": {"present": True, "unit": "g/s"},
        },
        "metadata": {
            key: "declared"
            for key in json.loads(protocol.read_text(encoding="utf-8"))["required_metadata"]
        },
    }
    declaration_path = tmp_path / "declaration.json"
    declaration_path.write_text(json.dumps(declaration), encoding="utf-8")
    return trace, manifest_path, declaration_path, protocol


def test_full_loop_screen_accepts_synchronized_station_vehicle_trace(tmp_path):
    trace, manifest, declaration, protocol = _inputs(tmp_path)
    result = validate_full_loop_trace(trace, manifest, declaration, protocol)
    assert result["decision"] == "FULL_LOOP_TRACE_READY_FOR_EVALUATION"
    assert result["full_loop_trace_ready"] is True
    assert result["observed"]["rows"] == 20
    assert result["columns"]["esd_state"] == "esd_state"
    assert result["no_imputation_or_resampling"] is True


def test_full_loop_screen_retains_missing_protection_channel(tmp_path):
    trace, manifest, declaration, protocol = _inputs(tmp_path, omit="esd_state")
    result = validate_full_loop_trace(trace, manifest, declaration, protocol)
    assert result["decision"] == "FULL_LOOP_TRACE_NOT_READY"
    assert result["full_loop_trace_ready"] is False
    assert "esd_state" in result["reasons"][0]


def test_full_loop_screen_rejects_clock_gap_without_repair(tmp_path):
    trace, manifest, declaration, protocol = _inputs(tmp_path)
    lines = trace.read_text(encoding="utf-8").splitlines()
    fields = lines[11].split(",")
    fields[0] = "9"
    lines[11] = ",".join(fields)
    trace.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = validate_full_loop_trace(trace, manifest, declaration, protocol)
    assert result["decision"] == "INELIGIBLE_BASE_TRACE_SCREEN"
    assert result["full_loop_trace_ready"] is False
