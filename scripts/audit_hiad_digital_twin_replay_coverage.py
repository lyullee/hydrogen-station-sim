"""Audit how public HIAD HRS event families traverse the digital-twin runtime.

The public incident rows do not contain enough synchronized boundary data to
reconstruct an accident.  This audit therefore runs one declared canonical
fault recipe per mapped response family, then reports whether each HIAD case is
directly represented, represented by a bounded proxy, or response-only.

This is an integration and traceability audit.  It is not accident validation,
frequency estimation, response-effectiveness evidence, or a safe-distance
claim.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from audit_hiad_playbook_coverage import candidate_plans  # noqa: E402
from h2station.hazop.runtime import HazopMonitor  # noqa: E402
from h2station.risk.runtime_backend import NativeHyRAMBackend  # noqa: E402
from h2station.safety_runtime import FaultEvent, FaultKind  # noqa: E402
from h2station.scenario import ReferenceScenario, build_reference_scenario  # noqa: E402


EVIDENCE = ROOT / "research/hiad_hrs_public_evidence.json"
PLAYBOOKS = ROOT / "src/h2station/data/emergency_playbooks.json"
OUT_JSON = ROOT / "research/hiad_digital_twin_replay_coverage_2026_10_08.json"
OUT_MD = ROOT / "research/HIAD_DIGITAL_TWIN_REPLAY_COVERAGE_2026_10_08.md"

MODEL_INPUTS = (
    ROOT / "src/h2station/safety_runtime.py",
    ROOT / "src/h2station/safe_operation.py",
    ROOT / "src/h2station/hazop/runtime.py",
    ROOT / "src/h2station/hazop/mapping.py",
    ROOT / "src/h2station/risk/live.py",
    ROOT / "src/h2station/risk/runtime_backend.py",
    ROOT / "src/h2station/data/emergency_playbooks.json",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _recipe_catalog() -> dict[str, dict[str, Any]]:
    return {
        "gas_release": {
            "representation": "direct_physical_replay",
            "duration_s": 1.2,
            "event": FaultEvent(
                "hiad-gas-release", FaultKind.HYDROGEN_LEAK,
                "cascade.medium", 0.0, leak_diameter_m=0.001,
            ),
            "checks": ("finite_state", "physical_state_changed", "release_source",
                       "gas_detection", "native_consequence"),
            "boundary": "A 1 mm medium-bank release is a canonical test input, not the geometry of a HIAD event.",
        },
        "hydrogen_fire": {
            "representation": "direct_physical_replay",
            "duration_s": 1.2,
            "event": FaultEvent(
                "hiad-hydrogen-fire", FaultKind.HYDROGEN_LEAK,
                "cascade.medium", 0.0, leak_diameter_m=0.001,
                indoor=True, ignited=True, enclosure_volume_m3=100.0,
                enclosure_vent_area_m2=2.0,
            ),
            "checks": ("finite_state", "physical_state_changed", "release_source",
                       "gas_detection", "flame_detection", "native_consequence",
                       "ignited_consequence"),
            "boundary": "The declared enclosure is a detector/consequence integration fixture, not a HIAD-site reconstruction.",
        },
        "hose_connection": {
            "representation": "direct_physical_replay",
            "duration_s": 1.2,
            "event": FaultEvent(
                "hiad-hose-release", FaultKind.HYDROGEN_LEAK,
                "dispenser.hose", 0.0, leak_diameter_m=0.0005,
            ),
            "checks": ("finite_state", "physical_state_changed", "release_source",
                       "gas_detection", "native_consequence"),
            "boundary": "A 0.5 mm dispenser-hose opening tests the modeled connection zone without asserting actual break geometry.",
        },
        "overpressure": {
            "representation": "direct_physical_replay",
            "duration_s": 3.0,
            "event": FaultEvent(
                "hiad-overpressure", FaultKind.PRESSURE_DISTURBANCE,
                "cascade.medium", 0.0, magnitude=20.0, rate_s=0.5,
            ),
            "checks": ("finite_state", "physical_state_changed", "pressure_alarm"),
            "boundary": "The controlled mass-source disturbance tests overpressure propagation; it is not an inferred HIAD source term.",
        },
        "precooling_fault": {
            "representation": "direct_physical_replay",
            "duration_s": 4.0,
            "event": FaultEvent(
                "hiad-precooling-loss", FaultKind.PRECOOLER_LOSS,
                "precooler", 0.0, magnitude=0.0,
            ),
            "checks": ("finite_state", "physical_state_changed", "precooling_trip"),
            "boundary": "Complete cooling-capacity loss is a canonical fault envelope, not the severity of the source event.",
        },
        "fueling_fault": {
            "representation": "direct_physical_replay",
            "duration_s": 10.0,
            "event": FaultEvent(
                "hiad-fueling-fault", FaultKind.PCV_STUCK_CLOSED,
                "dispenser.pcv", 0.0,
            ),
            "checks": ("finite_state", "physical_state_changed", "fueling_flow_alarm"),
            "boundary": "A dispenser-1 PCV stuck closed tests failed delivery; it does not reproduce every dispenser malfunction.",
        },
        "compressor_thermal": {
            "representation": "proxy_partial_replay",
            "duration_s": 1.2,
            "event": FaultEvent(
                "hiad-compressor-fire", FaultKind.EXTERNAL_FIRE,
                "compressor", 0.0, external_temperature_k=1000.0,
                heat_transfer_ua_w_k=5000.0,
            ),
            "checks": ("finite_state", "physical_state_changed", "compressor_flame_detection"),
            "boundary": "The current compressor has no separate gas/metal inventory; heat is conservatively coupled to the connected high-bank surrogate. Cavitation and oil-leak physics are not reconstructed.",
        },
        "external_fire": {
            "representation": "direct_physical_replay",
            "duration_s": 1.2,
            "event": FaultEvent(
                "canonical-external-fire", FaultKind.EXTERNAL_FIRE,
                "cascade.medium", 0.0, external_temperature_k=1000.0,
                heat_transfer_ua_w_k=5000.0,
            ),
            "checks": ("finite_state", "physical_state_changed", "flame_detection"),
            "boundary": "The declared medium-bank heat exposure is a canonical external-fire integration fixture, not the fire geometry or heat flux of a source incident.",
        },
        "isolation_failure": {
            "representation": "proxy_partial_replay",
            "duration_s": 10.0,
            "event": FaultEvent(
                "canonical-isolation-failure", FaultKind.PCV_STUCK_OPEN,
                "dispenser.pcv", 0.0,
            ),
            "checks": ("finite_state", "physical_state_changed", "isolation_fault_alarm"),
            "boundary": "A dispenser PCV failed open is a bounded failed-isolation proxy. It does not reconstruct isolation-valve seat leakage, actuator travel or closure feedback.",
        },
        "structural_damage": {
            "representation": "response_only_no_physical_model",
            "duration_s": None,
            "event": None,
            "checks": (),
            "boundary": "Collision, canopy and structural mechanics are outside the current process-state model; only the staged response plan is available.",
        },
    }


def _serialise_event(event: FaultEvent | None) -> dict[str, Any] | None:
    if event is None:
        return None
    return {
        "event_id": event.event_id,
        "kind": event.kind.value,
        "target": event.target,
        "start_time_s": event.start_time_s,
        "magnitude": event.magnitude,
        "leak_diameter_m": event.leak_diameter_m,
        "indoor": event.indoor,
        "ignited": event.ignited,
        "enclosure_volume_m3": event.enclosure_volume_m3,
        "enclosure_vent_area_m2": event.enclosure_vent_area_m2,
        "rate_s": event.rate_s,
        "external_temperature_k": event.external_temperature_k,
        "heat_transfer_ua_w_k": event.heat_transfer_ua_w_k,
    }


def _run_scenario(event: FaultEvent | None, duration_s: float) -> tuple[Any, HazopMonitor]:
    config = ReferenceScenario(
        duration_s=duration_s,
        control_period_s=0.2,
        risk_update_period_s=0.2,
        fault_events=(() if event is None else (event,)),
    )
    built = build_reference_scenario(config, NativeHyRAMBackend.from_environment())
    monitor = HazopMonitor(virtual_detectors=True)
    built.simulator.hazop_monitor = monitor
    trajectory = built.simulator.simulate(
        built.initial_state, duration_s, config.control_period_s,
    )
    return trajectory, monitor


def _max_signal(monitor: HazopMonitor, prefix: str) -> tuple[float, list[str]]:
    maxima: dict[str, float] = {}
    for frame in monitor.frames:
        for tag, signal in frame.get("signals", {}).items():
            if tag.startswith(prefix):
                maxima[tag] = max(maxima.get(tag, 0.0), float(signal.get("value", 0.0)))
    value = max(maxima.values(), default=0.0)
    tags = sorted(tag for tag, observed in maxima.items() if observed > 0.0)
    return value, tags


def _run_recipe(family: str, recipe: dict[str, Any]) -> dict[str, Any]:
    event = recipe["event"]
    duration_s = float(recipe["duration_s"])
    baseline, _ = _run_scenario(None, duration_s)
    trajectory, monitor = _run_scenario(event, duration_s)
    alarm_rows = [row for frame in monitor.frames for row in frame.get("active", [])]
    alarm_sensors = sorted({str(row.get("sensor_id")) for row in alarm_rows})
    alarm_rules = sorted({str(row.get("rule_id")) for row in alarm_rows})
    trip_causes = sorted({cause for command in trajectory.safety_commands for cause in command.trip_causes})
    gas_max, gas_tags = _max_signal(monitor, "GD-")
    flame_max, flame_tags = _max_signal(monitor, "FD-")
    releases_by_id: dict[str, dict[str, Any]] = {}
    for frame in monitor.frames:
        for release in frame.get("releases", []):
            current = releases_by_id.setdefault(str(release["release_id"]), {
                "release_id": str(release["release_id"]),
                "component_id": str(release["component_id"]),
                "maximum_mass_flow_g_s": 0.0,
                "consequence_statuses": [],
                "ignited_enclosure_statuses": [],
                "maximum_sampled_effect_radius_m": 0.0,
            })
            current["maximum_mass_flow_g_s"] = max(
                current["maximum_mass_flow_g_s"], float(release.get("mass_flow_g_s", 0.0))
            )
            consequence = release.get("consequence") or {}
            status = consequence.get("status")
            if status and status not in current["consequence_statuses"]:
                current["consequence_statuses"].append(status)
            ignited_status = consequence.get("ignited_enclosure_status")
            if ignited_status and ignited_status not in current["ignited_enclosure_statuses"]:
                current["ignited_enclosure_statuses"].append(ignited_status)
            current["maximum_sampled_effect_radius_m"] = max(
                current["maximum_sampled_effect_radius_m"],
                float(consequence.get("sampled_effect_radius_m") or 0.0),
            )
    releases = list(releases_by_id.values())
    native_consequence = bool(releases) and all(
        "calculated" in release["consequence_statuses"] for release in releases
    )
    ignited_consequence = any(
        "calculated" in release["ignited_enclosure_statuses"] for release in releases
    )
    checks = {
        "finite_state": bool(np.isfinite(trajectory.states).all()),
        "physical_state_changed": bool(
            not np.allclose(trajectory.final_state.as_vector(), baseline.final_state.as_vector(),
                            rtol=1.0e-9, atol=1.0e-9)
        ),
        "release_source": bool(releases) and all(
            release["maximum_mass_flow_g_s"] > 0.0 for release in releases
        ),
        "gas_detection": gas_max > 0.0,
        "flame_detection": flame_max >= 1.0,
        "native_consequence": native_consequence,
        "ignited_consequence": ignited_consequence,
        "pressure_alarm": "PT-0801" in alarm_sensors,
        "precooling_trip": "precooling-temperature-high" in trip_causes,
        "fueling_flow_alarm": "FT-1101" in alarm_sensors,
        "compressor_flame_detection": "FD-0601" in flame_tags,
        "isolation_fault_alarm": bool({
            "FT-1501", "FT-1701", "PT-1102", "PT-1401", "PT-1501", "TT-1401",
        } & set(alarm_sensors)),
    }
    required = tuple(recipe["checks"])
    return {
        "family": family,
        "representation": recipe["representation"],
        "status": "passed" if all(checks[name] for name in required) else "failed",
        "duration_s": duration_s,
        "control_period_s": 0.2,
        "fault": _serialise_event(event),
        "required_checks": list(required),
        "checks": {name: checks[name] for name in required},
        "observed": {
            "sample_count": int(len(trajectory.time_s)),
            "esd_time_s": trajectory.esd_time_s,
            "trip_causes": trip_causes,
            "alarm_sensor_ids": alarm_sensors,
            "alarm_rule_ids": alarm_rules,
            "gas_detector_max_volpct": gas_max,
            "gas_detector_positive_tags": gas_tags,
            "flame_detector_max_bool": flame_max,
            "flame_detector_positive_tags": flame_tags,
            "releases": releases,
        },
        "claim_boundary": recipe["boundary"],
    }


def _case_representation(plans: list[str], catalog: dict[str, dict[str, Any]]) -> str:
    levels = [catalog[plan]["representation"] for plan in plans]
    if "response_only_no_physical_model" in levels:
        return "response_only_no_physical_model"
    if "proxy_partial_replay" in levels:
        return "proxy_partial_replay"
    return "direct_physical_replay" if levels else "unmapped"


def build_audit() -> dict[str, Any]:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    playbooks = json.loads(PLAYBOOKS.read_text(encoding="utf-8"))
    valid_plans = {str(item["id"]) for item in playbooks.get("plans", [])}
    catalog = _recipe_catalog()
    recipe_results: dict[str, dict[str, Any]] = {}
    for family, recipe in catalog.items():
        if recipe["event"] is None:
            recipe_results[family] = {
                "family": family,
                "representation": recipe["representation"],
                "status": "not_run_no_physical_model",
                "fault": None,
                "required_checks": [],
                "checks": {},
                "observed": {},
                "claim_boundary": recipe["boundary"],
            }
        else:
            recipe_results[family] = _run_recipe(family, recipe)

    cases = []
    for case in evidence["cases"]:
        plans = [plan for plan in candidate_plans(case) if plan in valid_plans]
        representation = _case_representation(plans, catalog)
        executable = [plan for plan in plans if catalog[plan]["event"] is not None]
        failed = [plan for plan in executable if recipe_results[plan]["status"] != "passed"]
        cases.append({
            "event_id": str(case["event_id"]),
            "candidate_plan_ids": plans,
            "representation": representation,
            "executed_recipe_ids": executable,
            "failed_recipe_ids": failed,
            "integration_trace_pass": bool(plans) and not failed,
        })

    counts = {
        level: sum(case["representation"] == level for case in cases)
        for level in (
            "direct_physical_replay", "proxy_partial_replay",
            "response_only_no_physical_model", "unmapped",
        )
    }
    executable_results = [
        result for result in recipe_results.values()
        if result["status"] != "not_run_no_physical_model"
    ]
    passed = sum(result["status"] == "passed" for result in executable_results)
    return {
        "schema_version": 1,
        "artifact_type": "hiad_to_digital_twin_canonical_replay_coverage_audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_family_level_integration_audit",
        "evidence_role": "retrospective_metadata_to_canonical_runtime_traceability_only",
        "source": {
            "hiad_inventory": str(EVIDENCE.relative_to(ROOT)).replace("\\", "/"),
            "hiad_inventory_sha256": _sha256(EVIDENCE),
            "playbook_catalog": str(PLAYBOOKS.relative_to(ROOT)).replace("\\", "/"),
            "playbook_catalog_sha256": _sha256(PLAYBOOKS),
            "model_input_sha256": {
                str(path.relative_to(ROOT)).replace("\\", "/"): _sha256(path)
                for path in MODEL_INPUTS
            },
            "public_response_text_used": False,
            "case_narrative_used_for_physical_parameters": False,
        },
        "runtime": {
            "backend": "HyRAM+ 6.1 native",
            "virtual_detector_mode": True,
            "unique_family_recipes_run": len(executable_results),
            "family_recipe_pass_count": passed,
            "all_executable_recipes_passed": passed == len(executable_results),
        },
        "aggregate": {
            "case_count": len(cases),
            "integration_trace_pass_count": sum(case["integration_trace_pass"] for case in cases),
            "representation_case_counts": counts,
            "mapped_family_count": len(catalog),
            "physical_or_proxy_family_count": len(executable_results),
            "response_only_family_count": 1,
        },
        "family_recipes": recipe_results,
        "cases": cases,
        "claim_boundary": [
            "HIAD metadata selects a response family; incident narratives do not set pressure, temperature, opening size, enclosure geometry or timing in the canonical recipes.",
            "A passed trace shows that the declared family can traverse process physics, virtual detection, HAZOP/safety logic, native consequence calculation where applicable, and a registered response-plan handoff.",
            "It does not reconstruct any HIAD accident, validate accident frequencies or safe distances, establish operator benefit, or show that an action is correct or effective.",
            "Compressor thermal events remain a partial proxy because the compressor has no separate dynamic inventory, and structural damage remains response-only because structural mechanics are outside the model.",
        ],
    }


def write_outputs(result: dict[str, Any]) -> None:
    OUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    aggregate = result["aggregate"]
    counts = aggregate["representation_case_counts"]
    lines = [
        "# HIAD-to-digital-twin canonical replay coverage",
        "",
        "This audit checks whether each public HIAD HRS metadata family can enter the",
        "actual digital-twin runtime. It uses declared canonical fault fixtures because",
        "the incident inventory has no synchronized process boundary traces.",
        "",
        f"- Public HIAD HRS cases: **{aggregate['case_count']}**",
        f"- Direct physical replay coverage: **{counts['direct_physical_replay']}** cases",
        f"- Bounded proxy/partial replay: **{counts['proxy_partial_replay']}** cases",
        f"- Response-only, no physical model: **{counts['response_only_no_physical_model']}** case",
        f"- Unmapped: **{counts['unmapped']}** cases",
        f"- Executable canonical recipes passed: **{result['runtime']['family_recipe_pass_count']}/{result['runtime']['unique_family_recipes_run']}**",
        "",
        "## Canonical runtime traces",
        "",
        "| Family | Representation | Result | Runtime evidence |",
        "| --- | --- | --- | --- |",
    ]
    for family, row in result["family_recipes"].items():
        observed = row.get("observed") or {}
        evidence = []
        if observed.get("alarm_sensor_ids"):
            evidence.append("alarms " + ", ".join(observed["alarm_sensor_ids"]))
        if observed.get("trip_causes"):
            evidence.append("trips " + ", ".join(observed["trip_causes"]))
        if observed.get("releases"):
            evidence.append(f"releases {len(observed['releases'])}")
        if observed.get("flame_detector_positive_tags"):
            evidence.append("flame " + ", ".join(observed["flame_detector_positive_tags"]))
        lines.append(
            f"| `{family}` | `{row['representation']}` | `{row['status']}` | "
            + ("; ".join(evidence) or "staged response plan only") + " |"
        )
    lines += [
        "",
        "## Interpretation boundary",
        "",
        *[f"- {item}" for item in result["claim_boundary"]],
        "",
        "The JSON artifact contains source hashes, exact canonical fault inputs,",
        "required checks, observed sensors, safety trips, releases and consequence",
        "statuses for reproducible review.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    result = build_audit()
    write_outputs(result)
    print(json.dumps(result["aggregate"], ensure_ascii=False, indent=2))
    if not result["runtime"]["all_executable_recipes_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
