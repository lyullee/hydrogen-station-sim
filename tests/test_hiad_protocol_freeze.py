from __future__ import annotations

from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import freeze_hiad_study_protocol as protocol  # noqa: E402


def _package(tmp_path: Path, placeholder: bool = True) -> Path:
    for relative in protocol.REQUIRED_FILES:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        content = "protocol material"
        if relative == "research/HIAD_EXPERT_STUDY_PREREGISTRATION.md":
            content += "\nNo holdout model responses or expert ratings collected"
        if placeholder and relative == "research/ETHICS_DETERMINATION_REQUEST.md":
            content += f"\n{protocol.PLACEHOLDER}"
        path.write_text(content, encoding="utf-8")
    return tmp_path


def test_pending_protocol_freeze_records_recruitment_gate(tmp_path: Path):
    root = _package(tmp_path)
    manifest = protocol.build_manifest(root, "pending")
    assert manifest["ethics_status"] == "pending"
    assert manifest["reviewer_recruitment_permitted"] is False
    assert manifest["holdout_response_collection_permitted"] is False
    assert len(manifest["required_file_sha256"]) == len(protocol.REQUIRED_FILES)
    assert protocol.validate_manifest_integrity(root, manifest) == []


def test_resolved_ethics_requires_determination_id(tmp_path: Path):
    root = _package(tmp_path, placeholder=False)
    with pytest.raises(SystemExit, match="determination ID is required"):
        protocol.build_manifest(root, "exempt")


def test_resolved_ethics_rejects_unfilled_institution_fields(tmp_path: Path):
    root = _package(tmp_path, placeholder=True)
    with pytest.raises(SystemExit, match="fields remain incomplete"):
        protocol.build_manifest(root, "approved", "IRB-123")


def test_resolved_complete_packet_permits_collection(tmp_path: Path):
    root = _package(tmp_path, placeholder=False)
    manifest = protocol.build_manifest(root, "not-required", "DET-456")
    assert manifest["reviewer_recruitment_permitted"] is True
    assert manifest["holdout_response_collection_permitted"] is True
    assert protocol.validate_manifest_integrity(
        root, manifest, require_collection_permission=True
    ) == []


def test_protocol_integrity_rejects_stale_collection_code(tmp_path: Path):
    root = _package(tmp_path, placeholder=False)
    manifest = protocol.build_manifest(root, "exempt", "EX-123")
    target = root / "scripts/run_hiad_decision_evaluation.py"
    target.write_text("changed after freeze", encoding="utf-8")

    errors = protocol.validate_manifest_integrity(
        root, manifest, require_collection_permission=True
    )

    assert errors == [
        "protocol hash mismatch: scripts/run_hiad_decision_evaluation.py"
    ]
