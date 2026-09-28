"""Validate LLM-proposed consequence scenarios before any physics call."""

from __future__ import annotations

import json
from typing import Any, Mapping


def parse_saga_plan(
    answer: str, eligible_nodes: set[str], catalog: Mapping[str, Any],
) -> list[dict[str, str]]:
    """Accept only HAZOP nodes and leak sizes with a defined numerical diameter."""
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
    proposals: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError("Every proposed scenario must be a JSON object")
        node_id = row.get("node_id")
        size_id = row.get("leak_size_id")
        if not isinstance(node_id, str) or node_id not in eligible_nodes:
            raise ValueError(f"Scenario {index} has no current GOOD-quality source sensors")
        if not isinstance(size_id, str) or size_id not in sizes:
            raise ValueError(f"Scenario {index} uses an undefined leak diameter")
        if (node_id, size_id) in seen:
            raise ValueError("Duplicate node and leak-size proposal")
        seen.add((node_id, size_id))
        rationale = row.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError(f"Scenario {index} is missing HAZOP reasoning")
        proposals.append({"scenario_id": f"LLM-{index}", "node_id": node_id,
                          "leak_size_id": size_id, "rationale": rationale.strip()[:250]})
    return proposals
