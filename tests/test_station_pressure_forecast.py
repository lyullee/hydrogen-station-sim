from __future__ import annotations

from h2station.station_pressure_forecast import forecast_storage_pressure
from h2station.llm_grounding import build_evidence_manifest, prompt_decision_evidence


def _frame(time_s: float, medium: float, high: float, *, flowing: bool = True) -> dict:
    return {
        "time_s": time_s,
        "bank_pressure_mpa": {"medium": medium, "high": high},
        "process_activity": {
            "pressure_recharge": {
                "state": "flowing" if flowing else "idle",
            }
        },
    }


def test_forecast_requires_flowing_recharge_and_causal_prefix() -> None:
    frames = [_frame(float(index), 60.0 + index * 0.05, 80.0) for index in range(11)]
    result = forecast_storage_pressure(frames)
    assert result["status"] == "available"
    assert result["bank"] == "medium"
    assert result["horizon_s"] == 30.0
    assert result["basis"]["holdout_case_count"] == 394
    assert result["basis"]["runtime_parameter_application"] is False
    assert result["basis"]["vehicle_fill_validation"] is False

    idle = forecast_storage_pressure([_frame(0.0, 60.0, 80.0, flowing=False)])
    assert idle["status"] == "not_available"
    assert idle["reason"] == "pressure_recharge_not_flowing"


def test_forecast_fails_closed_when_bank_response_is_not_dominant() -> None:
    frames = [_frame(float(index), 60.0 + index * 0.1, 80.0 + index * 0.09) for index in range(11)]
    result = forecast_storage_pressure(frames)
    assert result["status"] == "not_available"
    assert result["reason"] == "bank_response_not_dominant"


def test_llm_manifest_carries_forecast_with_claim_boundary() -> None:
    frames = [_frame(float(index), 60.0 + index * 0.05, 80.0) for index in range(11)]
    forecast = forecast_storage_pressure(frames)
    manifest = build_evidence_manifest(
        {"time_s": 10.0, "station_pressure_forecast": forecast},
        {},
        [],
        False,
        question="고압 뱅크 재충전 압력 상승을 예측해줘",
    )
    carried = manifest["station_pressure_forecast"]
    assert carried["status"] == "available"
    assert carried["basis"]["runtime_parameter_application"] is False
    assert carried["basis"]["full_loop_holdout_eligible"] is False
    prompt_evidence = prompt_decision_evidence(manifest)
    projected = prompt_evidence["current_station_pressure_forecast"]
    assert projected["status"] == "available"
    assert projected["forecast_pressure_mpa"] > projected["current_pressure_mpa"]
    assert projected["provenance"]["vehicle_fill_validation"] is False
