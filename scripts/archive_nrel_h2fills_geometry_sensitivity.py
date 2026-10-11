"""Archive a privacy-safe aggregate of the NREL HDVS geometry sensitivity.

The numerical workbook is locally licensed/ignored and was opened before this
diagnostic was designed.  This writer deliberately emits aggregate metrics only
and marks the result as post-access development evidence.  It must not be used
to promote a runtime geometry or close an external-validation gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / (
    "data/public_validation/results/nrel_h2fills_hdvs_typeiv/"
    "geometry_sensitivity.json"
)
DEFAULT_OUTPUT = ROOT / (
    "research/nrel_h2fills_geometry_sensitivity_2026_10_12.json"
)
DEFAULT_REPORT = ROOT / (
    "research/NREL_H2FILLS_GEOMETRY_SENSITIVITY_2026_10_12.md"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _aggregate(variant: dict[str, Any]) -> dict[str, Any]:
    aggregate = variant["aggregate"]
    return {
        "screening_pass_count": int(aggregate["screening_pass_count"]),
        "screening_pass_fraction": float(aggregate["screening_pass_fraction"]),
        "pressure_rmse_mpa": float(aggregate["pressure_rmse_mpa"]),
        "temperature_rmse_c": float(aggregate["temperature_rmse_c"]),
        "mass_final_error_kg": float(aggregate["mass_final_error_kg"]),
        "pressure_final_error_mpa": float(aggregate["pressure_final_error_mpa"]),
        "base_volume_m3": float(variant["base_volume_m3"]),
        "effective_volume_multiplier": float(variant["effective_volume_multiplier"]),
    }


def build_archive(source: dict[str, Any], *, source_path: Path) -> dict[str, Any]:
    variants = source["variants"]
    return {
        "schema_version": 1,
        "artifact_type": "nrel_h2fills_geometry_sensitivity_archive",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "post_access_development_diagnostic",
        "evidence_role": "mechanism_and_geometry_sensitivity_only",
        "source": {
            "dataset_family": "public NREL H2FillS HDVS Type-IV sample",
            "source_result_sha256": _sha256(source_path),
            "tank_count": int(len(source["source"]["tank_ids"])),
            "capacity_kg_per_tank": float(source["source"]["capacity_kg"]),
            "reference_pressure_mpa": float(source["source"]["reference_pressure_pa"] / 1.0e6),
            "reference_temperature_c": float(source["source"]["reference_temperature_k"] - 273.15),
            "capacity_eos_volume_m3": float(source["source"]["capacity_eos_volume_m3"]),
        },
        "screening_limits": {
            "pressure_rmse_mpa_max": 5.0,
            "temperature_rmse_c_max": 10.0,
            "mass_final_abs_error_kg_max": 0.5,
            "joint_rule": "pressure, temperature and final-mass screens per tank",
        },
        "variants": {
            "legacy_frozen": _aggregate(variants["legacy_frozen"]),
            "capacity_eos_with_frozen_fit": _aggregate(
                variants["capacity_eos_with_frozen_fit"]
            ),
            "capacity_eos_no_volume_fit": _aggregate(
                variants["capacity_eos_no_volume_fit"]
            ),
        },
        "finding": {
            "preferred_physical_sensitivity": "capacity_eos_no_volume_fit",
            "preferred_screen_pass_count": int(
                variants["capacity_eos_no_volume_fit"]["aggregate"]["screening_pass_count"]
            ),
            "preferred_screen_total": int(len(source["source"]["tank_ids"])),
            "interpretation": (
                "The legacy capacity scaling overpredicts the effective gas volume; "
                "a declared-capacity EOS volume removes the systematic pressure bias "
                "in this post-access sample. This is a mechanism diagnosis, not a "
                "confirmatory validation result."
            ),
        },
        "governance": {
            "outcomes_accessed_before_diagnostic": True,
            "parameter_fitting": False,
            "runtime_default_changed": False,
            "validation_gate_effect": "none",
            "next_required_step": (
                "Freeze the capacity/EOS geometry rule and score a new untouched "
                "tank-and-hose trace with declared capacity, vessel geometry, "
                "inlet pressure/temperature and mass boundary before promotion."
            ),
        },
        "source_commit": _git_commit(),
        "claim_boundary": (
            "Aggregate post-access sensitivity only. It does not validate a full "
            "station-to-vehicle loop, station control, safety logic, consequence "
            "distance or field operation, and it does not authorize a runtime "
            "geometry change."
        ),
    }


def render_report(archive: dict[str, Any]) -> str:
    v = archive["variants"]
    preferred = v["capacity_eos_no_volume_fit"]
    return "\n".join(
        [
            "# NREL H2FillS geometry sensitivity — 2026-10-12",
            "",
            "이 기록은 이미 수치 결과를 열어 본 뒤 수행한 개발 진단이다. 독립 검증 결과나 런타임 기본값 변경으로 해석하지 않는다.",
            "",
            "## 관찰 결과",
            "",
            f"- 대상: 공개 NREL H2FillS HDVS Type-IV 탱크 {archive['source']['tank_count']}개 aggregate",
            f"- 기존 고정 체적 규칙: {v['legacy_frozen']['screening_pass_count']}/{archive['finding']['preferred_screen_total']} 통과",
            f"- 용량·EOS 체적 + 기존 열전달 보정: {v['capacity_eos_with_frozen_fit']['screening_pass_count']}/{archive['finding']['preferred_screen_total']} 통과",
            f"- 용량·EOS 체적 + 유효체적 보정 제거: {preferred['screening_pass_count']}/{archive['finding']['preferred_screen_total']} 통과",
            f"- 선호 민감도 압력 RMSE: {preferred['pressure_rmse_mpa']:.3f} MPa",
            f"- 선호 민감도 온도 RMSE: {preferred['temperature_rmse_c']:.3f} °C",
            "",
            "## 해석과 제한",
            "",
            "용량·EOS로 선언한 체적을 사용하면 이 자료에서 기존 체적 규칙의 압력 편향이 사라진다. 그러나 결과를 본 뒤 선택한 민감도이므로 검증 PASS로 승격할 수 없고, 기본 모델도 바꾸지 않았다.",
            "",
            "다음 단계는 체적 규칙, 탱크 용량·기하, 입구 압력·온도, 질량유량 경계를 사전에 동결한 새 untouched tank-and-hose trace 평가다. 새 자료가 없으면 이 결과는 기전 진단으로만 보고한다.",
            "",
            f"원본 aggregate 해시: `{archive['source']['source_result_sha256']}`",
            f"소스 커밋: `{archive['source_commit']}`",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    source = json.loads(args.input.read_text(encoding="utf-8"))
    archive = build_archive(source, source_path=args.input)
    args.output.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(render_report(archive), encoding="utf-8")
    print(json.dumps(archive, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
