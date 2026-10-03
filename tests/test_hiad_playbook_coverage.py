from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_hiad_playbook_coverage import candidate_plans  # noqa: E402


def test_positive_ignition_is_not_inferred_from_no_ignition():
    assert "hydrogen_fire" not in candidate_plans({
        "title": "Detection of hydrogen release",
        "physical_effect": "Unignited Hydrogen Release",
        "consequence_nature": "Leak no ignition",
        "sub_application": "Hydrogen dispenser",
        "supply_chain_stage": "Hydrogen transfer",
    })


def test_storage_explosion_maps_to_fire_release_and_pressure_families():
    plans = candidate_plans({
        "title": "Explosion in the storage of a HRS",
        "physical_effect": "Hydrogen release and ignition",
        "consequence_nature": "Explosion",
        "sub_application": "HRS (70 Mpa)",
        "supply_chain_stage": "Hydrogen storage",
    })
    assert plans == ["hydrogen_fire", "gas_release", "overpressure"]


def test_non_hydrogen_canopy_damage_is_left_for_catalog_review():
    assert candidate_plans({
        "title": "Damage of a HRS canopy",
        "physical_effect": "No Hydrogen Release",
        "consequence_nature": "Near miss",
        "sub_application": "HRS",
        "supply_chain_stage": "Hydrogen delivery",
    }) == []
