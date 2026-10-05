import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from intake_external_hrs_bundle import build_manifest  # noqa: E402
from validate_external_hrs_trace import validate_trace  # noqa: E402


def _inputs(tmp_path: Path, *, rows: list[dict[str, str]]):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    trace = bundle / "trace.csv"
    with trace.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time_s", "pressure_mpa_abs", "temperature_degC", "mass_flow_g_s"])
        writer.writeheader()
        writer.writerows(rows)
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
        "metadata": {key: "declared" for key in json.loads(protocol.read_text(encoding="utf-8"))["required_metadata"]},
    }
    declaration_path = tmp_path / "declaration.json"
    declaration_path.write_text(json.dumps(declaration), encoding="utf-8")
    return trace, manifest_path, declaration_path, protocol


def test_quality_screen_accepts_finite_monotonic_trace(tmp_path):
    rows = [
        {"time_s": str(index), "pressure_mpa_abs": str(5 + index), "temperature_degC": "-40", "mass_flow_g_s": "10"}
        for index in range(20)
    ]
    trace, manifest, declaration, protocol = _inputs(tmp_path, rows=rows)
    result = validate_trace(trace, manifest, declaration, protocol)
    assert result["decision"] == "QUALITY_SCREEN_PASS"
    assert result["observed"]["rows"] == 20
    assert result["numerical_values_inspected"] is True


def test_quality_screen_rejects_non_monotonic_time_without_repair(tmp_path):
    rows = [
        {"time_s": str(index), "pressure_mpa_abs": "20", "temperature_degC": "25", "mass_flow_g_s": "0"}
        for index in range(20)
    ]
    rows[10]["time_s"] = "9"
    trace, manifest, declaration, protocol = _inputs(tmp_path, rows=rows)
    result = validate_trace(trace, manifest, declaration, protocol)
    assert result["decision"] == "QUALITY_SCREEN_FAIL"
    assert "time base is not strictly increasing" in result["reasons"]


def test_quality_screen_rejects_missing_required_channel(tmp_path):
    rows = [
        {"time_s": str(index), "pressure_mpa_abs": "20", "temperature_degC": "25", "mass_flow_g_s": "0"}
        for index in range(20)
    ]
    trace, manifest, declaration, protocol = _inputs(tmp_path, rows=rows)
    trace.write_text("time_s,pressure_mpa_abs,temperature_degC\n0,20,25\n", encoding="utf-8")
    fresh_manifest = build_manifest(trace.parent, protocol)
    manifest.write_text(json.dumps(fresh_manifest), encoding="utf-8")
    result = validate_trace(trace, manifest, declaration, protocol)
    assert result["decision"] == "INELIGIBLE_TRACE_CHANNELS"
    assert any("mass_flow" in reason for reason in result["reasons"])
