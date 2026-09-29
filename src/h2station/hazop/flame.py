"""Virtual, location-scoped flame heads for the H70 reference station.

These proxy channels respond to injected fire geometry after a modeled detector
delay. They are not independent field measurements or validated coverage maps.
"""
from __future__ import annotations

FLAME_RESPONSE_DELAY_S = 0.5

# A detector only sees incident targets explicitly assigned to its modeled zone.
FLAME_DETECTORS = (
    ("FD-0101", "N01", "공급 트레일러·하역 구역", ("supply", "unloading")),
    ("FD-0601", "N06", "압축기 패키지", ("compressor",)),
    ("FD-0701", "N07", "저압 저장뱅크", ("cascade.low",)),
    ("FD-0801", "N08", "중압 저장뱅크", ("cascade.medium",)),
    ("FD-0901", "N09", "고압 저장뱅크", ("cascade.high",)),
    ("FD-1301", "N13", "1번 디스펜서·차량", ("dispenser", "vehicle.tank", "pcv")),
    ("FD-1701", "N17", "2번 디스펜서·차량", ("dispenser_2", "vehicle_2.tank", "pcv_2")),
    ("FD-1901", "N19", "프리쿨러 패키지", ("cooler", "precooler")),
    ("FD-2001", "N20", "벤트·공통 헤더", ("vent", "header")),
)


def sees_target(target: str, prefixes: tuple[str, ...]) -> bool:
    target = str(target).lower()
    return any(target == prefix or target.startswith(prefix + ".") for prefix in prefixes)
