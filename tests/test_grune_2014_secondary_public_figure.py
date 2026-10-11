import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research" / "grune_2014_secondary_public_figure_protocol_2026_10_12.json"
RESULT = ROOT / "research" / "grune_2014_secondary_public_figure_result_2026_10_12.json"
DATA = ROOT / "data" / "public_validation" / "derived" / (
    "grune_2014_ichs2011_inset_vector.csv"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_secondary_figure_route_is_integrity_checked_and_not_promoted():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    extraction = protocol["extraction"]

    assert protocol["status"] == (
        "secondary_figure_route_locked_before_vector_extraction"
    )
    assert extraction["derived_csv_sha256"] == _sha256(DATA)
    assert result["data_sha256"] == _sha256(DATA)
    assert result["protocol_sha256"] == _sha256(PROTOCOL)
    assert result["result"]["points"] >= 15
    assert result["result"]["experimental_half_pressure_time_s"] is not None
    assert result["result"]["joint_primary_screen_pass"] is False

    decision = protocol["decision"]
    assert decision["use_for_primary_gate"] is False
    assert extraction["runtime_model_changed"] is False
    assert extraction["thresholds_changed"] is False
    assert extraction["original_51_point_result_overwritten"] is False

