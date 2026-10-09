from scripts.recheck_nbsdc_liquid_hrs_access import DATA_ID, ROOT_PID, _role


def test_nbsdc_liquid_recheck_is_bound_to_public_catalogue_and_safe_roles():
    assert DATA_ID == "67d50e37195d260905af9869"
    assert ROOT_PID == "1"
    assert _role("70MPa加氢机.csv") == "dispenser_70mpa"
    assert _role("液氢泵-液氢储罐.xlsx") == "liquid_pump_tank"
    assert _role("液氢加氢站运行数据集数据说明 .docx") == "description"
