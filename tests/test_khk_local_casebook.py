import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "prepare_khk_local_casebook.py"
spec = importlib.util.spec_from_file_location("prepare_khk_local_casebook", SCRIPT)
khk = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(khk)


def test_khk_station_boundary_requires_hydrogen_and_station_marker():
    base = {"物質名": "水素", "事故名称": "", "業種": "その他(水素ステーション)", "設備区分": "安全弁", "事故概要": "", "取扱状態": ""}
    assert khk.is_station_case(base) is True
    base["物質名"] = "液化石油ガス"
    assert khk.is_station_case(base) is False


def test_khk_mapping_preserves_compound_response_families():
    row = {
        "事故名称": "水素ステーション充填ホースからの水素漏えい火災",
        "1次事象": "漏洩",
        "2次事象": "火災",
        "設備区分": "充てんホース",
        "事故概要": "FCV充填中にガス検知器警報と自動緊急停止",
    }
    plans = khk.response_plan_candidates(row)
    assert "gas_release" in plans
    assert "hydrogen_fire" in plans
    assert "hose_connection" in plans
    assert "fueling_fault" in plans


def test_khk_pipeline_metadata_keeps_public_claim_closed():
    import json

    record = json.loads(
        (ROOT / "research" / "khk_local_casebook_pipeline_2026_10_04.json").read_text(encoding="utf-8")
    )
    assert record["raw_or_derived_casebook_committed"] is False
    assert record["validation_classification"]["expert_holdout_ready"] is False
    assert record["validation_classification"]["goal_completion_permitted"] is False
