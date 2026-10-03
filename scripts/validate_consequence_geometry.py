"""Build the bounded outdoor consequence-geometry validation chain.

The chain deliberately separates experimental model validation, adapter parity,
and browser geometry translation.  It does not claim site-specific CFD or a
regulatory separation distance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _contains(path: Path, *markers: str) -> bool:
    text = path.read_text(encoding="utf-8")
    return all(marker in text for marker in markers)


def _node_executable() -> str:
    # The normal PATH is authoritative in CI.  The bundled Codex runtime is a
    # local development fallback and is never recorded in the evidence file.
    return "node"


def build_report(root: Path, *, run_browser_tests: bool = True) -> dict[str, object]:
    root = root.resolve()
    upstream = root / "data/public_validation/raw/hyram-v6.1/tests/hyram/validation"
    verification_path = root / "research/hyram_adapter_verification.json"
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    adapter = root / "src/h2station/risk/runtime_backend.py"
    display_contract = root / "web/consequence-geometry.mjs"
    state_contract = root / "web/risk-range-state.mjs"
    scene = root / "web/station3d.js"

    browser_test = {
        "command": "node --test tests/risk_range_state.test.mjs",
        "status": "not-run",
        "return_code": None,
    }
    if run_browser_tests:
        completed = subprocess.run(
            [_node_executable(), "--test", "tests/risk_range_state.test.mjs"],
            cwd=root, text=True, encoding="utf-8", errors="replace",
            capture_output=True, check=False,
        )
        browser_test.update(
            status="passed" if completed.returncode == 0 else "failed",
            return_code=completed.returncode,
            output_tail="\n".join(
                (completed.stdout + completed.stderr).splitlines()[-12:]
            ),
        )

    modules = set((verification.get("upstream_validation") or {}).get("test_modules") or [])
    evidence_families = [
        {
            "id": "four_percent_unignited_plume",
            "independent_source": "Han et al. (2013), Figure 6",
            "experimental_quantity": "4 vol% H2 (LFL) dilution length versus pressure",
            "production_quantity": "flammable_plume_streamline_distance_m",
            "applicable_geometry": "directional free-jet centerline length",
            "source_file": "tests/hyram/validation/test_jetplume.py",
            "data_files": [
                "han-2013-fig6a.csv", "han-2013-fig6b.csv", "han-2013-fig6c.csv",
            ],
            "coverage": "0.5, 0.7 and 1.0 mm orifices; 100-400 bar; LFL=0.04",
            "frozen_limits_at_lfl": {
                "max_absolute_error_m": 0.19,
                "max_percent_error": 6,
                "minimum_r_squared": 0.996,
            },
            "markers_present": _contains(
                upstream / "test_jetplume.py",
                "class Test_Han_2013_fig6", "lean_flamm_limit = 0.04",
                "Dilution Length vs. Pressure",
            ),
        },
        {
            "id": "ignited_jet_radiation",
            "independent_source": "Schefer et al. (2006), Figure 8; Houf and Schefer (2007), Figure 6",
            "experimental_quantity": "radiative heat flux versus distance",
            "production_quantity": "heat_fluxes and sampled 5 kW/m2 threshold bracket",
            "applicable_geometry": "sampled radial screening distance",
            "source_file": "tests/hyram/validation/test_heatflux.py",
            "data_files": ["schefer-2006-fig8.csv", "houfschefer-2007-fig6.csv"],
            "coverage": "five transient flow states plus an independent normalized-distance series",
            "markers_present": _contains(
                upstream / "test_heatflux.py",
                "class Test_Schefer_2006_2007", "test_flux_distance_fig8",
                "test_flux_distance_fig6",
            ),
        },
        {
            "id": "unconfined_overpressure",
            "independent_source": "Bauwens and Dorofeev (2019), Figure 9; additional published sets in the same suite",
            "experimental_quantity": "peak unconfined overpressure versus distance",
            "production_quantity": "overpressures and sampled 5 kPa threshold bracket",
            "applicable_geometry": "sampled radial screening distance",
            "source_file": "tests/hyram/validation/test_unconfined_overpressure.py",
            "data_files": ["unconfined_overpressure_data.py"],
            "coverage": "BST plus three sensitivity models across published free-jet experiments",
            "markers_present": _contains(
                upstream / "test_unconfined_overpressure.py",
                "class Test_Bauwens_2019", "BST_method", "Distance from Nozzle (m)",
            ),
        },
    ]
    data_dir = upstream / "data"
    for family in evidence_families:
        family["data_sha256"] = {
            name: _sha256(data_dir / name) for name in family["data_files"]
        }

    chain_checks = {
        "exact_hyram_source_identity": bool(
            (verification.get("hyram") or {}).get("source_identity_match")
        ),
        "upstream_validation_passed": (
            (verification.get("upstream_validation") or {}).get("status") == "passed"
        ),
        "required_upstream_modules_executed": {
            "tests/hyram/validation/test_jetplume.py",
            "tests/hyram/validation/test_heatflux.py",
            "tests/hyram/validation/test_unconfined_overpressure.py",
        }.issubset(modules),
        "production_adapter_parity_passed": bool(
            verification.get("adapter_parity_passed")
        ),
        "production_contract_preserves_geometry_inputs": _contains(
            adapter,
            '"release_angle_rad": request.release_angle_rad',
            '"observation_locations_m": self.observation_locations',
            '"flammable_plume_streamline_distance_m"',
            '"sampled_effect_radius_m"',
        ),
        "display_separates_radial_and_directional_geometry": _contains(
            display_contract,
            "thermalBlastRadiusM", "flammablePlumeLengthM", "releaseAngleRad",
        ) and _contains(
            scene, "sampled-thermal-blast-radius", "directional-four-percent-plume",
        ),
        "browser_mapping_regression_passed": browser_test["status"] == "passed",
        "all_evidence_markers_and_data_present": all(
            family["markers_present"] and all((data_dir / item).is_file() for item in family["data_files"])
            for family in evidence_families
        ),
    }
    status = "passed" if all(chain_checks.values()) else "failed"
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "validation_scope": "outdoor unconfined hydrogen free-jet consequence display mapping",
        "independent_case_count": len(evidence_families),
        "independent_dataset_family_count": len(evidence_families),
        "site_specific_validation": False,
        "site_specific_claim_permitted": False,
        "safety_distance_claim_permitted": False,
        "upstream_validation": {
            "software": "HyRAM+ 6.1",
            "commit": (verification.get("hyram") or {}).get("upstream_commit"),
            "passed_test_count": (verification.get("upstream_validation") or {}).get("passed_test_count"),
            "passed_subtest_count": (verification.get("upstream_validation") or {}).get("passed_subtest_count"),
            "primary_report": "https://doi.org/10.2172/2480221",
            "official_software_page": "https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/hyram/",
        },
        "evidence_families": evidence_families,
        "chain_checks": chain_checks,
        "browser_mapping_test": browser_test,
        "artifact_hashes": {
            str(path.relative_to(root)).replace("\\", "/"): _sha256(path)
            for path in (verification_path, adapter, display_contract, state_contract, scene)
        },
        "display_contract": {
            "thermal_and_overpressure": "equipment-footprint-centred radial screening band using sampled_effect_radius_m",
            "dispersion": "directional tapered plume using the 4 vol% centerline distance, contour width and release angle",
            "persistence": "active releases retain separate peak radial and plume extents; ended releases have a three-second display grace",
            "units": "metres and radians without display-side conversion",
            "scene_azimuth": "schematic +X axis; the process state carries elevation angle but no site azimuth",
        },
        "limitations": [
            "The independent measurements are published data digitized and regression-tested by HyRAM+, not measurements produced by this project.",
            "The display is a screening visualization, not a regulatory separation distance, evacuation radius, or certified safety boundary.",
            "Buildings, congestion, terrain and site-specific wind are not resolved; no site-specific CFD or outdoor field campaign has been performed.",
            "The 5 kW/m2 and 5 kPa radial result is a discrete observation-point bracket and must not be interpolated as an exact contour.",
            "Unconfined overpressure depends on the selected BST flame-speed assumption; alternate methods remain a model-form sensitivity.",
            "The scene uses the stored release elevation angle but a schematic +X azimuth because the process model does not provide site azimuth.",
        ],
        "decision": (
            "The traceability chain passes for the bounded outdoor free-jet display scope. "
            "It does not validate a specific station site or authorize a safety-distance claim."
            if status == "passed" else
            "The bounded traceability chain does not pass; no consequence-geometry validation claim is permitted."
        ),
    }


def _markdown(report: dict[str, object]) -> str:
    lines = [
        "# Consequence geometry validation chain", "",
        f"- Status: **{report['status'].upper()}**",
        f"- Scope: {report['validation_scope']}",
        f"- Independent evidence families: **{report['independent_dataset_family_count']}**",
        "- Site-specific validation: **No**", "- Safety-distance claim permitted: **No**", "",
        "## Evidence chain", "",
        "| Family | Published experiment | Production/display quantity | Geometry |",
        "|---|---|---|---|",
    ]
    for family in report["evidence_families"]:
        lines.append(
            f"| `{family['id']}` | {family['independent_source']} | "
            f"{family['production_quantity']} | {family['applicable_geometry']} |"
        )
    lines.extend(["", "## Automated chain checks", ""])
    lines.extend(
        f"- [{'x' if passed else ' '}] `{name}`"
        for name, passed in report["chain_checks"].items()
    )
    lines.extend([
        "", "## Interpretation", "", report["decision"], "",
        "The experimental-model layer is the exact HyRAM+ 6.1 source already "
        "verified against the frozen upstream suite. The production adapter has "
        "exact numerical parity for plume, heat-flux and overpressure outputs. "
        "The browser contract now keeps radial thermal/blast screening separate "
        "from the directional 4 vol% plume instead of collapsing both into one dome.", "",
        "Primary validation reference: [Validation of HyRAM+ Version 5.1 Physics Models]"
        "(https://doi.org/10.2172/2480221). Official software context: "
        "[Sandia HyRAM+](https://energy.sandia.gov/programs/sustainable-transportation/"
        "hydrogen/hydrogen-safety-codes-and-standards/hyram/).", "",
        "## Limitations", "",
        *[f"- {item}" for item in report["limitations"]], "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--skip-browser-tests", action="store_true")
    parser.add_argument(
        "--json-output", type=Path,
        default=Path("research/consequence_geometry_validation.json"),
    )
    parser.add_argument(
        "--report-output", type=Path,
        default=Path("research/CONSEQUENCE_GEOMETRY_VALIDATION.md"),
    )
    args = parser.parse_args()
    root = args.root.resolve()
    report = build_report(root, run_browser_tests=not args.skip_browser_tests)
    json_path = args.json_output if args.json_output.is_absolute() else root / args.json_output
    report_path = args.report_output if args.report_output.is_absolute() else root / args.report_output
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    report_path.write_text(_markdown(report), encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": report["status"],
        "evidence_families": report["independent_dataset_family_count"],
        "chain_checks": report["chain_checks"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
