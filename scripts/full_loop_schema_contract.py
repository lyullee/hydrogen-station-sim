"""Privacy-safe channel-role contract for station-to-vehicle traces.

The older schema scan deliberately used broad groups (``pressure`` and
``temperature``).  Those groups are useful for inventory, but they can produce
false positives when a file contains only station pressure and an unrelated
vehicle identifier.  This module adds a stricter *header-only* contract that
requires the receiving vehicle and the station/dispenser boundary to be
represented explicitly in the same logical table.

Only aggregate set membership is returned to callers.  No original labels,
rows, timestamps, or source paths are persisted by the intake tools.
"""
from __future__ import annotations

import re
from typing import Iterable


CONTRACT_REQUIRED = frozenset(
    {
        "common_time",
        "vehicle_pressure",
        "vehicle_temperature",
        "station_pressure",
        "delivered_temperature",
        "mass_flow",
        "cascade_or_storage",
        "controller_state",
        "vehicle_identity",
    }
)

_VEHICLE = (
    "vehicle", "car", "automobile", "veh", "fcev", "receptacle",
    "차량", "자동차", "수소차", "리셉터클",
)
_STATION = (
    "station", "dispenser", "nozzle", "hose", "delivery", "refuel",
    "fill", "cascade", "bank", "storage", "vessel", "compressor",
    "precool", "supply", "충전소", "충전기", "노즐", "호스", "공급",
    "뱅크", "저장", "용기", "압축", "냉각",
)
_DELIVERY = (
    "dispenser", "nozzle", "hose", "delivery", "refuel", "fill",
    "충전기", "노즐", "호스", "충전", "공급",
)
_PRESSURE = ("pressure", "press", "pt", "pi", "압력")
_TEMPERATURE = ("temperature", "temp", "tt", "온도")
_FLOW_OR_MASS = ("flow", "mass", "rate", "mfm", "fqi", "fwg", "유량", "질량")
_CASCADE = ("cascade", "bank", "storage", "vessel", "뱅크", "저장", "용기")
_CONTROLLER = (
    "state", "status", "valve", "esd", "mode", "control", "alarm",
    "interlock", "fault", "상태", "밸브", "차단", "제어", "경보", "고장",
)
_IDENTITY = ("id", "identifier", "name", "serial", "번호", "식별", "이름")
_TIME = ("time", "timestamp", "datetime", "localtime", "elapsed", "common", "sync", "일시", "시각", "시간")


def _contains(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def contract_coverage(labels: Iterable[object]) -> frozenset[str]:
    """Return only strict aggregate contract groups for one logical header."""
    parts = [str(value or "").strip().lower() for value in labels if str(value or "").strip()]
    # Evaluate each label independently so a vehicle name in one column cannot
    # incorrectly qualify a station pressure column in another.
    groups: set[str] = set()
    for label in parts:
        text = re.sub(r"[^a-z0-9가-힣]+", " ", label)
        has_vehicle = _contains(text, _VEHICLE)
        has_station = _contains(text, _STATION)
        has_delivery = _contains(text, _DELIVERY)
        has_pressure = _contains(text, _PRESSURE)
        has_temperature = _contains(text, _TEMPERATURE)
        if _contains(text, _TIME):
            groups.add("common_time")
        if has_vehicle and has_pressure:
            groups.add("vehicle_pressure")
        if has_vehicle and has_temperature:
            groups.add("vehicle_temperature")
        if has_station and has_pressure:
            groups.add("station_pressure")
        if has_delivery and has_temperature:
            groups.add("delivered_temperature")
        if _contains(text, _FLOW_OR_MASS):
            groups.add("mass_flow")
        if _contains(text, _CASCADE):
            groups.add("cascade_or_storage")
        if _contains(text, _CONTROLLER):
            groups.add("controller_state")
        if has_vehicle and _contains(text, _IDENTITY):
            groups.add("vehicle_identity")
    return frozenset(groups)


def missing_contract_groups(coverage: Iterable[str]) -> list[str]:
    return sorted(CONTRACT_REQUIRED - set(coverage))
