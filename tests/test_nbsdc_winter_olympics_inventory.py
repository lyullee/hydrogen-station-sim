import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from intake_external_hrs_bundle import build_manifest  # noqa: E402
from validate_nbsdc_winter_olympics_inventory import validate_inventory  # noqa: E402


ROLE_IDS = {
    "description_document": "641874c7e39c3b0b8e3274ab",
    "transaction_records": "641874c7e39c3b0b8e3274a8",
    "dispenser_records": "641874c7e39c3b0b8e3274a9",
    "compressor_records": "641874c7e39c3b0b8e3274aa",
}


def _inputs(tmp_path: Path, *, omit_role: str | None = None):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    paths = {
        "description_document": "description.docx",
        "transaction_records": "transaction.xlsx",
        "dispenser_records": "dispenser.xlsx",
        "compressor_records": "compressor.xlsx",
    }
    for role, filename in paths.items():
        (bundle / filename).write_bytes((role + "\n").encode("utf-8"))
    protocol = ROOT / "research/nbsdc_winter_olympics_intake_protocol_2026_10_04.json"
    manifest = build_manifest(bundle, protocol)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    declaration = {
        "declaration_type": "nbsdc_winter_olympics_file_roles",
        "roles": {
            role: {"source_file_id": ROLE_IDS[role], "relative_paths": [filename]}
            for role, filename in paths.items()
        },
    }
    if omit_role:
        declaration["roles"].pop(omit_role)
    declaration_path = tmp_path / "declaration.json"
    declaration_path.write_text(json.dumps(declaration), encoding="utf-8")
    return manifest_path, declaration_path, protocol


def test_nbsdc_inventory_requires_all_roles(tmp_path):
    manifest, declaration, protocol = _inputs(tmp_path)
    report = validate_inventory(manifest, declaration, protocol)
    assert report["decision"] == "INVENTORY_READY_FOR_CHANNEL_MAPPING"
    assert report["inventory_ready"] is True
    assert report["numerical_values_inspected"] is False
    assert report["reasons"] == []


def test_nbsdc_inventory_retains_missing_role(tmp_path):
    manifest, declaration, protocol = _inputs(tmp_path, omit_role="compressor_records")
    report = validate_inventory(manifest, declaration, protocol)
    assert report["decision"] == "INVENTORY_INCOMPLETE"
    assert report["inventory_ready"] is False
    assert "missing file role or relative path: compressor_records" in report["reasons"]


def test_nbsdc_inventory_rejects_unopened_contract_violation(tmp_path):
    manifest, declaration, protocol = _inputs(tmp_path)
    value = json.loads(manifest.read_text(encoding="utf-8"))
    value["numerical_values_inspected"] = True
    manifest.write_text(json.dumps(value), encoding="utf-8")
    report = validate_inventory(manifest, declaration, protocol)
    assert report["inventory_ready"] is False
    assert "manifest does not prove numerical values were unopened" in report["reasons"]
