from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "research/compressor_package_isolation_audit_2026_10_13.json"


def test_compressor_package_isolation_audit_is_current_and_bounded():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert record["status"] == "completed_development_physics_audit"
    assert record["model_status"] == "DEVELOPMENT_PHYSICS_UNVALIDATED"
    assert all(record["checks"].values())
    assert abs(record["results"]["high_bank_mass_change_after_esd_kg"]) <= 1.0e-9
    assert abs(record["results"]["mass_balance_residual_kg"]) <= 5.0e-6
    assert record["results"]["package_pressure_final_mpa_abs"] < record[
        "results"
    ]["package_pressure_at_esd_mpa_abs"]
    assert "have not been validated" in record["claim_boundary"]
    assert "cannot establish" in record["claim_boundary"]
    for relative, digest in record["source_hashes"].items():
        assert sha256((ROOT / relative).read_bytes()).hexdigest() == digest
