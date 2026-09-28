"""Validate LLM-proposed consequence scenarios before any physics call."""

from __future__ import annotations

import json
import re
from typing import Any, Mapping


def parse_saga_plan(
    answer: str, target_nodes: set[str], catalog: Mapping[str, Any],
    pressure_tags: set[str], temperature_tags: set[str],
) -> list[dict[str, str]]:
    """Accept only HAZOP targets, defined leak sizes, and current GOOD P/T tags."""
    decoder = json.JSONDecoder()
    document = None
    for index, character in enumerate(answer[:20000]):
        if character != "{":
            continue
        try:
            candidate, _ = decoder.raw_decode(answer[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and "scenarios" in candidate:
            document = candidate
            break
    if document is None:
        raise ValueError("SAGA did not return a scenario JSON object")
    rows = document.get("scenarios")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 3:
        raise ValueError("SAGA must propose one to three scenarios")
    sizes = {size["size_id"]: size for size in catalog["leak_sizes"]
             if isinstance(size.get("직경_mm"), (int, float)) and 0.1 <= size["직경_mm"] <= 3.0}
    cases = {case["node_id"]: case for case in catalog["cases"]}
    sensor_nodes = {sensor["sensor_id"]: sensor["node_id"] for sensor in catalog["sensors"]}
    proposals: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError("Every proposed scenario must be a JSON object")
        node_id = row.get("node_id")
        size_id = row.get("leak_size_id")
        if not isinstance(node_id, str) or node_id not in target_nodes or node_id not in cases:
            raise ValueError(f"Scenario {index} has an unknown target node")
        if not isinstance(size_id, str) or size_id not in sizes:
            raise ValueError(f"Scenario {index} uses an undefined leak diameter")
        if (node_id, size_id) in seen:
            raise ValueError("Duplicate node and leak-size proposal")
        seen.add((node_id, size_id))
        rationale = row.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(f"Scenario {index} is missing HAZOP reasoning")
        case = cases[node_id]
        pressure_sensor = row.get("pressure_sensor")
        temperature_sensor = row.get("temperature_sensor")
        if pressure_sensor is None:
            pressure_sensor = next((tag for tag in re.findall(r"PT-\d{4}", case.get("압력_sensor") or "")
                                    if tag in pressure_tags), None)
        if temperature_sensor is None:
            temperature_sensor = next((tag for tag in re.findall(r"TT-\d{4}", case.get("온도_sensor") or "")
                                       if tag in temperature_tags), None)
        if (not isinstance(pressure_sensor, str) or pressure_sensor not in pressure_tags
                or not isinstance(temperature_sensor, str) or temperature_sensor not in temperature_tags):
            raise ValueError(f"Scenario {index} must select current GOOD pressure and temperature tags")
        proposals.append({"scenario_id": f"LLM-{index}", "node_id": node_id,
                          "leak_size_id": size_id, "rationale": rationale.strip()[:250],
                          "pressure_sensor": pressure_sensor, "temperature_sensor": temperature_sensor,
                          "pressure_source_node_id": sensor_nodes[pressure_sensor],
                          "temperature_source_node_id": sensor_nodes[temperature_sensor]})
    return proposals
