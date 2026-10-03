from __future__ import annotations

import json
from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_hiad_decision_evaluation import _response_payload  # noqa: E402


def _case() -> dict:
    return {
        "event_id": "401",
        "title": "Hose release",
        "description": "Hydrogen was released during filling.",
        "initiating_system": "Dispenser",
        "physical_effect": "Release",
        "consequence_nature": "Leak",
        "sub_application": "Road vehicle",
        "supply_chain_stage": "Distribution",
        "operational_condition": "Fuelling",
    }


def test_direct_and_standards_rag_variants_use_separate_saga_contracts():
    direct = _response_payload("saga-linked", _case(), "groq")
    rag = _response_payload("saga-standards-rag", _case(), "groq")

    assert direct["request_kind"] == "user_query"
    assert "context" in direct and "mode" not in direct
    assert rag["mode"] == "rag"
    assert rag["knowledge_mode"] == "standards"
    assert "Hose release" in rag["message"]
    json.dumps(rag)
