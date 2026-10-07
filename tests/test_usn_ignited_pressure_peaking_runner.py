import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_usn_ignited",
    ROOT / "scripts/run_usn_17934047_ignited_pressure_peaking.py",
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_holdout_manifest_and_vent_map_are_complete():
    assert set(range(2, 29)).issubset(MODULE.FILES)
    assert set(range(1, 32)) == set(MODULE.CASE_VENTS)
    assert MODULE.CASE_VENTS[19] == 1
    assert MODULE.CASE_VENTS[18] == 2
    assert MODULE.CASE_VENTS[14] == 3


def test_frozen_block_mean_is_deterministic():
    values = MODULE.np.arange(40, dtype=float)
    reduced = MODULE.block_mean(values)
    assert reduced.tolist() == [9.5, 29.5]


def test_missing_raw_files_are_reported_without_substitution(tmp_path):
    result = MODULE.run(tmp_path, [1, 2])
    assert result["aggregate"]["eligible_case_count"] == 0
    assert result["aggregate"]["excluded_case_count"] == 2
    assert result["aggregate"]["confirmatory_rule_met"] is False
