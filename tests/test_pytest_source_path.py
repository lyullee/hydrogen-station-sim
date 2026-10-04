import importlib


def test_pytest_configuration_exposes_the_current_source_tree():
    module = importlib.import_module("h2station")
    assert "hydrogen-station-sim" in module.__file__.replace("\\", "/")
    assert "/src/h2station/" in module.__file__.replace("\\", "/")
