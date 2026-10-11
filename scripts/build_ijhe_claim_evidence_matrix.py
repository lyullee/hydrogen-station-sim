"""Build the publication-safe IJHE claim/evidence matrix from the audit.

The matrix is a reviewer-facing companion artifact.  It deliberately copies
only bounded status, endpoint metrics and claim boundaries from the readiness
audit; it never turns a diagnostic or a failed screen into a validation claim.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


ROWS: tuple[dict[str, Any], ...] = (
    {
        "id": "tank_external_validation",
        "label": "Measured-boundary Type-IV tank thermodynamics",
        "evidence_summary": "12 independent public fills; pressure, temperature and SOC",
        "interpretation": "Tank submodel only; not cascade dispatch, precooling or vehicle-control validation.",
    },
    {
        "id": "dickens_typeiii_prospective_validation",
        "label": "Type-III thermal transfer",
        "evidence_summary": "Independent prospective fill",
        "interpretation": "Pressure screens passed, but gas-temperature screens failed; no temperature-transfer claim.",
    },
    {
        "id": "preslhy_partb_ambient_external_validation",
        "label": "Ambient PRESLHY source depletion",
        "evidence_summary": "Five Part-B cases",
        "interpretation": "Joint screen below the declared threshold; diameter-dependent boundary sensitivity remains unresolved.",
    },
    {
        "id": "proust_independent_release_validation",
        "label": "90 MPa aperture release",
        "evidence_summary": "Three INERIS/CEA series",
        "interpretation": "No series met the joint mass-flow rule; no universal aperture correction is supported.",
    },
    {
        "id": "schefer_transient_release_validation",
        "label": "Transient blowdown source model",
        "evidence_summary": "Sandia/SRI 2006 trace",
        "interpretation": "Peak-normalized NRMSE passed, but median error and half-peak timing failed.",
    },
    {
        "id": "ignited_pressure_peaking_external_validation",
        "label": "Ignited-enclosure consequence endpoint",
        "evidence_summary": "Installed HyRAM+ API and 27 ignited-enclosure cases",
        "interpretation": "Adapter and bounded enclosure peak-pressure translation only; not site consequence or separation-distance certification.",
    },
    {
        "id": "h2safe_spatial_detector_transfer_validation",
        "label": "Spatial detector transfer",
        "evidence_summary": "18 actual-hydrogen HyTunnel cases",
        "interpretation": "Rank/recall screens were not jointly met; geometry-only routing remains disabled at runtime.",
    },
    {
        "id": "full_loop_external_validation",
        "label": "Station-to-vehicle full loop",
        "evidence_summary": "Public-data search and consumed closed-loop diagnostic",
        "interpretation": "Out of scope: no rights-cleared synchronized station/controller/dispenser/vehicle raw cohort was found.",
    },
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(audit: dict[str, Any], *, audit_sha256: str) -> dict[str, Any]:
    gates = {row.get("id"): row for row in audit.get("gates", [])}
    rows: list[dict[str, Any]] = []
    for template in ROWS:
        gate = gates.get(template["id"])
        if not gate:
            raise ValueError(f"missing readiness gate: {template['id']}")
        rows.append(
            {
                **template,
                "status": "OUT OF SCOPE" if template["id"] == "full_loop_external_validation" else gate.get("status"),
                "audit_claim": gate.get("claim"),
                "evidence": gate.get("evidence"),
                "requirement": gate.get("requirement"),
                "observed": gate.get("observed"),
            }
        )
    return {
        "schema_version": 1,
        "artifact_type": "ijhe_claim_evidence_matrix",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_audit": "manuscript/ijhe_readiness_audit.json",
        "source_audit_sha256": audit_sha256,
        "paper_scope": "objective engineering and physics validation; no human-effectiveness or field-safety claim",
        "rows": rows,
        "decision_rule": "PASS is retained only for the declared component endpoint; FAIL, PENDING and OUT OF SCOPE remain explicit boundaries.",
    }


def _md(matrix: dict[str, Any]) -> str:
    lines = [
        "# IJHE claim/evidence matrix (2026-10-11)",
        "",
        "This reviewer-facing companion is generated from `manuscript/ijhe_readiness_audit.json`.",
        "It records bounded component claims and preserves failed or incomplete transfers.",
        "It does not establish journal acceptance, field safety, or human-effectiveness.",
        "",
        f"Audit SHA-256: `{matrix['source_audit_sha256']}`",
        "",
        "| Claim boundary | Evidence | Decision | Interpretation |",
        "|---|---|---|---|",
    ]
    for row in matrix["rows"]:
        interpretation = row["interpretation"].replace("|", "\\|")
        lines.append(
            f"| {row['label']} | {row['evidence_summary']} | {row['status']} | {interpretation} |"
        )
    lines.extend(
        [
            "",
            "The detailed endpoint values, protocol hashes and source paths remain in the JSON audit.",
            "A passing component is never promoted to a complete station-to-vehicle claim.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, default=Path("manuscript/ijhe_readiness_audit.json"))
    parser.add_argument("--json-output", type=Path, default=Path("research/ijhe_claim_evidence_matrix_2026_10_11.json"))
    parser.add_argument("--md-output", type=Path, default=Path("research/IJHE_CLAIM_EVIDENCE_MATRIX_2026_10_11.md"))
    args = parser.parse_args()
    audit_sha256 = _sha256(args.audit)
    matrix = build(json.loads(args.audit.read_text(encoding="utf-8")), audit_sha256=audit_sha256)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    args.md_output.write_text(_md(matrix), encoding="utf-8", newline="\n")
    print(json.dumps({"rows": len(matrix["rows"]), "audit_sha256": audit_sha256}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
