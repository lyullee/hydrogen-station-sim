"""Run inside Unreal Editor after the C++ module builds.

Creates only missing reference assets. It does not overwrite an edited map or
material. All visuals are owned reference primitives, with no confidential media.
"""
import unreal


def material(name, translucent=False):
    path = "/Game/HRS/Materials/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, "/Game/HRS/Materials", unreal.Material, unreal.MaterialFactoryNew())
    edit = unreal.MaterialEditingLibrary
    color = edit.create_material_expression(asset, unreal.MaterialExpressionVectorParameter, -360, -100)
    color.set_editor_property("parameter_name", "Color")
    color.set_editor_property("default_value", unreal.LinearColor(.65, .7, .75, 1))
    edit.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    roughness = edit.create_material_expression(asset, unreal.MaterialExpressionConstant, -360, 50)
    roughness.set_editor_property("r", .65)
    edit.connect_material_property(roughness, "", unreal.MaterialProperty.MP_ROUGHNESS)
    if translucent:
        asset.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        asset.set_editor_property("two_sided", True)
        opacity = edit.create_material_expression(asset, unreal.MaterialExpressionConstant, -360, 160)
        opacity.set_editor_property("r", .12)
        edit.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY)
    edit.recompile_material(asset)
    unreal.EditorAssetLibrary.save_asset(path)


material("M_HRSOpaque")
material("M_HRSTranslucent", True)
level_path = "/Game/HRS/Maps/Station"
if not unreal.EditorAssetLibrary.does_asset_exist(level_path):
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not levels.new_level(level_path):
        raise RuntimeError("Unable to create reference station map")
    levels.save_current_level()
unreal.log("HRS reference scene assets ready; run Play to connect to the station API.")
