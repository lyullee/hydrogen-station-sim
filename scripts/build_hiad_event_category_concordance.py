from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HIAD = ROOT / "research/hiad_hrs_public_evidence.json"
DEFAULT_REPLAY = ROOT / "research/hiad_digital_twin_replay_coverage_2026_10_08.json"
DEFAULT_JSON = ROOT / "research/hiad_event_category_concordance_2026_10_11.json"
DEFAULT_MD = ROOT / "research/HIAD_EVENT_CATEGORY_CONCORDANCE_2026_10_11.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_family(physical_effect: str) -> tuple[str, list[str], list[str]]:
    """Map public physical-effect metadata to a predeclared runtime family contract.

    This intentionally uses only coarse public metadata, never incident narrative,
    action text, or measurements.  It is a retrospective category concordance and
    is not an accident reconstruction.
    """
    normalized = " ".join(physical_effect.lower().split())
    if normalized == "no hydrogen release":
        return "no_release", [], ["gas_release", "hydrogen_fire"]
    if "hydrogen release and ignition" in normalized:
        return "release_with_ignition", ["gas_release", "hydrogen_fire"], []
    if "unignited hydrogen release" in normalized:
        return "unignited_release", ["gas_release"], ["hydrogen_fire"]
    return "unclassified", [], []


def build(hiad_path: Path = DEFAULT_HIAD, replay_path: Path = DEFAULT_REPLAY) -> dict:
    hiad = json.loads(hiad_path.read_text(encoding="utf-8"))
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    hiad_cases = {str(case["event_id"]): case for case in hiad["cases"]}
    replay_cases = {str(case["event_id"]): case for case in replay["cases"]}
    if set(hiad_cases) != set(replay_cases):
        raise ValueError("HIAD and replay inventories must have identical event IDs")

    cases: list[dict] = []
    for event_id in sorted(hiad_cases, key=lambda value: int(value)):
        public = hiad_cases[event_id]
        runtime = replay_cases[event_id]
        family, required, forbidden = source_family(public["physical_effect"])
        executed = list(runtime.get("executed_recipe_ids", []))
        missing = [recipe for recipe in required if recipe not in executed]
        contradictory = [recipe for recipe in forbidden if recipe in executed]
        if family == "unclassified":
            concordance = "not_comparable"
            reason = "physical-effect metadata is outside the declared release-family contract"
        elif missing:
            concordance = "partial"
            reason = "required runtime family is absent from executed recipes"
        elif contradictory:
            concordance = "metadata_runtime_conflict"
            reason = "public metadata indicates no release but the candidate runtime includes a release family"
        else:
            concordance = "matched"
            reason = "required and prohibited family conditions are satisfied"
        cases.append(
            {
                "event_id": event_id,
                "public_physical_effect": public["physical_effect"],
                "public_consequence_nature": public["consequence_nature"],
                "source_family": family,
                "required_runtime_families": required,
                "forbidden_runtime_families": forbidden,
                "executed_recipe_ids": executed,
                "representation": runtime["representation"],
                "integration_trace_pass": bool(runtime["integration_trace_pass"]),
                "category_concordance": concordance,
                "concordance_reason": reason,
            }
        )

    counts = {
        "case_count": len(cases),
        "category_concordance_counts": {
            key: sum(case["category_concordance"] == key for case in cases)
            for key in ("matched", "partial", "metadata_runtime_conflict", "not_comparable")
        },
        "representation_case_counts": {
            key: sum(case["representation"] == key for case in cases)
            for key in (
                "direct_physical_replay",
                "proxy_partial_replay",
                "response_only_no_physical_model",
            )
        },
        "integration_trace_pass_count": sum(case["integration_trace_pass"] for case in cases),
    }
    return {
        "schema_version": 1,
        "artifact_type": "hiad_public_metadata_to_runtime_family_concordance",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_retrospective_category_concordance",
        "evidence_role": "supporting_traceability_only",
        "source": {
            "hiad_inventory": hiad_path.relative_to(ROOT).as_posix(),
            "hiad_inventory_sha256": sha256(hiad_path),
            "replay_coverage": replay_path.relative_to(ROOT).as_posix(),
            "replay_coverage_sha256": sha256(replay_path),
            "public_metadata_fields_used": ["physical_effect", "consequence_nature", "event_id"],
            "incident_narrative_used": False,
            "emergency_action_text_used": False,
            "physical_parameters_from_incident_text": False,
        },
        "mapping_contract": {
            "unignited_release": {"required": ["gas_release"], "forbidden": ["hydrogen_fire"]},
            "release_with_ignition": {"required": ["gas_release", "hydrogen_fire"], "forbidden": []},
            "no_release": {"required": [], "forbidden": ["gas_release", "hydrogen_fire"]},
            "unclassified": {"required": [], "forbidden": []},
            "rule": "A matched category means only that coarse public outcome metadata is consistent with the declared runtime family IDs; it does not validate numerical results or response correctness.",
        },
        "aggregate": counts,
        "cases": cases,
        "claim_boundary": [
            "This table compares coarse HIAD outcome metadata with the runtime family labels already used in the digital-twin trace audit.",
            "The comparison is retrospective traceability evidence, not independent accident reconstruction, frequency validation, or a safe-distance validation.",
            "A matched category does not show that pressure, temperature, release size, geometry, timing, or consequence magnitude are correct.",
            "Explicit no-release metadata is treated as a negative physical observation, so event 803 is not routed into gas-release or fire physics merely because its title contains the word release.",
            "It does not evaluate operator performance, human factors, ethics, or SAGA response effectiveness.",
        ],
    }


def render_markdown(artifact: dict) -> str:
    aggregate = artifact["aggregate"]
    lines = [
        "# HIAD event-category concordance (2026-10-11)",
        "",
        "This artifact compares coarse public HIAD outcome metadata with the already frozen digital-twin replay family IDs. It is a traceability check, not accident reconstruction.",
        "",
        f"- Cases joined: **{aggregate['case_count']}**",
        f"- Category match: **{aggregate['category_concordance_counts']['matched']}**",
        f"- Partial: **{aggregate['category_concordance_counts']['partial']}**",
        f"- Metadata/runtime conflict: **{aggregate['category_concordance_counts']['metadata_runtime_conflict']}**",
        f"- Integration traces passing: **{aggregate['integration_trace_pass_count']} / {aggregate['case_count']}**",
        "",
        "## Mapping contract",
        "",
        "| Public physical-effect category | Required runtime family | Prohibited runtime family |",
        "| --- | --- | --- |",
        "| Unignited Hydrogen Release | `gas_release` | `hydrogen_fire` |",
        "| Hydrogen release and ignition | `gas_release`, `hydrogen_fire` | — |",
        "| No Hydrogen Release | — | `gas_release`, `hydrogen_fire` |",
        "",
        "## Event concordance",
        "",
        "| Event | Public effect | Public consequence | Runtime recipes | Representation | Result |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for case in artifact["cases"]:
        recipes = ", ".join(f"`{recipe}`" for recipe in case["executed_recipe_ids"]) or "—"
        lines.append(
            f"| {case['event_id']} | {case['public_physical_effect']} | {case['public_consequence_nature']} | {recipes} | {case['representation']} | {case['category_concordance']} |"
        )
    lines += [
        "",
        "## Limits",
        "",
        "The public incident narrative and emergency-action text are not used as model inputs. A match only means the declared coarse family contract is consistent. It does not validate event frequency, numerical consequence magnitude, field safety distance, operator benefit, ethics, or human effectiveness.",
        "",
        f"Source HIAD SHA-256: `{artifact['source']['hiad_inventory_sha256']}`",
        f"Source replay SHA-256: `{artifact['source']['replay_coverage_sha256']}`",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    artifact = build()
    with args.json.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    with args.markdown.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_markdown(artifact))
    print(json.dumps(artifact["aggregate"], ensure_ascii=False))


if __name__ == "__main__":
    main()
