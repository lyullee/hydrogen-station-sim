import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_validation_scope_manifest.py"
OUTPUT = ROOT / "research/validation_scope_manifest_verification_2026_10_11.json"


def test_validation_scope_manifest_verifier_passes_without_private_rows():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(ROOT), "--output", str(OUTPUT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert result["status"] == "PASS"
    assert result["failures"] == []
    assert result["checks"]["privacy_boundary"]["pass"] is True
    assert result["checks"]["owner_partition_rule"]["pass"] is True
    assert result["checks"]["full_loop_scope_exclusion"]["pass"] is True
    assert result["checks"]["referenced_artifact_hashes"]["pass"] is True
    assert "private rows" in result["claim_boundary"]
