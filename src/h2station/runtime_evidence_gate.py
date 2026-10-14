"""Machine-readable evidence boundary for runtime safety recommendations.

The consequence model may inform an operator, but a component-level screening
calculation must never become an autonomous actuator command.  This module
keeps that distinction in the payload consumed by the UI and LLM.
"""

from __future__ import annotations

from typing import Any, Mapping


def runtime_evidence_gate(
    result: Mapping[str, Any],
    *,
    model_id: str = "HyRAM+ 6.1 native",
    model_version: str = "6.1",
    input_quality: str = "GOOD",
) -> dict[str, Any]:
    """Return the permitted uses of one consequence calculation.

    Deterministic PLC/interlock logic is outside this gate.  The gate applies
    to actions proposed *because of* a model consequence result.
    """

    status = str(result.get("status") or "missing").upper()
    validation = str(
        result.get("consequence_validation_status") or "UNDECLARED"
    ).upper()
    quality = str(input_quality or "UNKNOWN").upper()
    evidence = str(result.get("consequence_validation_artifacts") or "")
    uncertainty_status = str(
        result.get("release_flow_uncertainty_status") or "NOT_QUANTIFIED"
    )

    blockers: list[str] = []
    if status != "CALCULATED":
        blockers.append("CONSEQUENCE_NOT_CALCULATED")
    if quality != "GOOD":
        blockers.append("INPUT_QUALITY_NOT_GOOD")
    if validation != "FULL_LOOP_SITE_VALIDATED":
        blockers.append("NO_FULL_LOOP_SITE_VALIDATION")
    if not bool(result.get("site_specific_safety_distance_supported", False)):
        blockers.append("SITE_SPECIFIC_DISTANCE_NOT_VALIDATED")
    if not evidence:
        blockers.append("EVIDENCE_ARTIFACT_NOT_DECLARED")

    advisory = status == "CALCULATED" and quality in {"GOOD", "UNCERTAIN"}
    return {
        "model_id": model_id,
        "model_version": model_version,
        "validation_status": validation,
        "applicability_range": str(
            result.get("consequence_validation_scope") or "UNDECLARED"
        ),
        "input_quality": quality,
        "uncertainty_status": uncertainty_status,
        "evidence_artifacts": evidence,
        "operator_advisory_authorized": advisory,
        "automatic_actuation_authorized": not blockers,
        "automatic_actuation_blockers": blockers,
        "decision_rule": (
            "Model output is advisory until a site-specific full-loop validation "
            "passes. Deterministic PLC/interlock actions use their independent "
            "validated logic and are not authorized by this consequence result."
        ),
    }
