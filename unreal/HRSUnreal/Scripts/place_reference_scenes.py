"""Place validated reference glTF scenes in the station map.

The Interchange scene importer preserves the node hierarchy and transforms that
are lost when the GLB files are imported only as content assets.  Each imported
actor receives its simulator component ID as an Actor tag.  The C++ station
actor then hides the matching primitive fallback while retaining its live
labels, valves, incident overlays and selection behavior.

Run after ``bootstrap_scene.py`` and ``import_reference_assets.py`` through
UnrealEditor-Cmd.  Existing tagged actors are preserved to avoid destroying
manual edits.  Bounds are checked against the source manifest so a metre/cm
conversion regression fails the build instead of producing tiny equipment.
"""
from __future__ import annotations

import json
from pathlib import Path

import unreal


PROJECT_DIR = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
REPO_DIR = PROJECT_DIR.parents[1]
SOURCE_DIR = REPO_DIR / "output" / "unreal" / "assets"
DESTINATION = "/Game/HRS/Scenes"
LEVEL_PATH = "/Game/HRS/Maps/Station"
TAG_REFERENCE = "HRS_REFERENCE_MODEL"

# Asset, simulator component ID, and the C++ station origin in Unreal cm.
PLACEMENTS = (
    ("tube-trailer", "supply", (-2200.0, -150.0, 0.0)),
    ("compressor", "compressor", (-640.0, -600.0, 0.0)),
    ("precooler", "cooler", (1100.0, -600.0, 0.0)),
    ("storage-low", "cascade.low", (-100.0, -600.0, 0.0)),
    ("storage-medium", "cascade.medium", (300.0, -600.0, 0.0)),
    ("storage-high", "cascade.high", (700.0, -600.0, 0.0)),
    ("vehicle", "vehicle.tank", (280.0, 700.0, 0.0)),
    ("vehicle", "vehicle_2.tank", (1080.0, 700.0, 0.0)),
)


def load_inputs() -> tuple[dict[str, list[float]], dict]:
    manifest = json.loads((SOURCE_DIR / "manifest.json").read_text(encoding="utf-8"))
    validation = json.loads((SOURCE_DIR / "validation.json").read_text(encoding="utf-8"))
    if validation.get("status") != "PASS":
        raise RuntimeError("Reference GLB validation must be PASS before scene placement")
    dimensions = {row["name"]: row["dimensions_m"] for row in manifest["assets"]}
    required = {row[0] for row in PLACEMENTS}
    missing = sorted(required - dimensions.keys())
    if missing:
        raise RuntimeError("Reference manifest is incomplete: " + ", ".join(missing))
    return dimensions, validation


def actor_tag_strings(actor) -> set[str]:
    return {str(tag) for tag in actor.get_editor_property("tags")}


def tagged_actors(actor_subsystem, component_id: str) -> list:
    return [actor for actor in actor_subsystem.get_all_level_actors()
            if component_id in actor_tag_strings(actor)]


def combined_bounds(actors: list) -> tuple[unreal.Vector, unreal.Vector, list[float]]:
    minimum = unreal.Vector(float("inf"), float("inf"), float("inf"))
    maximum = unreal.Vector(float("-inf"), float("-inf"), float("-inf"))
    found = False
    for actor in actors:
        origin, extent = actor.get_actor_bounds(False)
        if extent.x <= 0 and extent.y <= 0 and extent.z <= 0:
            continue
        found = True
        minimum.x = min(minimum.x, origin.x - extent.x)
        minimum.y = min(minimum.y, origin.y - extent.y)
        minimum.z = min(minimum.z, origin.z - extent.z)
        maximum.x = max(maximum.x, origin.x + extent.x)
        maximum.y = max(maximum.y, origin.y + extent.y)
        maximum.z = max(maximum.z, origin.z + extent.z)
    if not found:
        raise RuntimeError("Imported scene has no renderable actor bounds")
    return minimum, maximum, [maximum.x - minimum.x, maximum.y - minimum.y, maximum.z - minimum.z]


def validate_scale(asset_name: str, actors: list, dimensions_m: dict[str, list[float]]) -> list[float]:
    _, _, actual_cm = combined_bounds(actors)
    expected_cm = [value * 100.0 for value in dimensions_m[asset_name]]
    # glTF-to-Unreal axis conversion can permute dimensions, so compare sorted extents.
    ratios = [actual / expected for actual, expected in zip(sorted(actual_cm), sorted(expected_cm))]
    if any(ratio < 0.75 or ratio > 1.25 for ratio in ratios):
        raise RuntimeError(
            f"{asset_name} physical scale mismatch: actual_cm={actual_cm}, "
            f"expected_cm={expected_cm}, ratios={ratios}"
        )
    return actual_cm


def align_to_station_origin(actors: list, target: tuple[float, float, float]) -> None:
    minimum, maximum, _ = combined_bounds(actors)
    center_x = (minimum.x + maximum.x) * 0.5
    center_y = (minimum.y + maximum.y) * 0.5
    delta = unreal.Vector(target[0] - center_x, target[1] - center_y, target[2] - minimum.z)
    for actor in actors:
        actor.set_actor_location(actor.get_actor_location() + delta, False, True)


def tag_scene(actors: list, component_id: str) -> None:
    for actor in actors:
        tags = list(actor.get_editor_property("tags"))
        for value in (component_id, TAG_REFERENCE):
            tag = unreal.Name(value)
            if tag not in tags:
                tags.append(tag)
        actor.set_editor_property("tags", tags)
        actor.set_actor_enable_collision(True)


def import_scene(manager, current_level, actor_subsystem, asset_name: str,
                 component_id: str, target: tuple[float, float, float]) -> tuple[list, str]:
    existing = tagged_actors(actor_subsystem, component_id)
    if existing:
        unreal.log(f"HRS placement preserved {component_id}: {len(existing)} actors")
        return existing, "preserved"

    source_path = SOURCE_DIR / f"{asset_name}.glb"
    if not source_path.is_file():
        raise RuntimeError(f"Missing validated GLB scene: {source_path}")
    before = {actor.get_path_name() for actor in actor_subsystem.get_all_level_actors()}
    source_data = unreal.InterchangeManager.create_source_data(str(source_path))
    parameters = unreal.ImportAssetParameters(
        is_automated=True,
        import_level=current_level,
        destination_name=component_id.replace(".", "_"),
        replace_existing=False,
    )
    if not manager.import_scene(f"{DESTINATION}/{asset_name}", source_data, parameters):
        raise RuntimeError(f"Interchange scene import failed: {source_path}")
    # Interchange can complete asynchronously even in commandlet mode. Bounds
    # and tagging must run only after every scene actor exists.
    manager.wait_until_all_tasks_done(False)
    created = [actor for actor in actor_subsystem.get_all_level_actors()
               if actor.get_path_name() not in before]
    if not created:
        raise RuntimeError(f"Interchange created no level actors for {source_path}")
    align_to_station_origin(created, target)
    tag_scene(created, component_id)
    return created, "imported"


dimensions, _ = load_inputs()
level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if not level_subsystem.load_level(LEVEL_PATH):
    raise RuntimeError(f"Unable to load station level: {LEVEL_PATH}")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
current_level = world.get_current_level()
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
manager = unreal.InterchangeManager.get_interchange_manager_scripted()

results = []
for asset_name, component_id, target in PLACEMENTS:
    scene_actors, action = import_scene(
        manager, current_level, actor_subsystem, asset_name, component_id, target)
    actual_cm = validate_scale(asset_name, scene_actors, dimensions)
    results.append({
        "asset": asset_name,
        "component_id": component_id,
        "action": action,
        "actor_count": len(scene_actors),
        "bounds_cm": [round(value, 3) for value in actual_cm],
        "target_cm": list(target),
    })

if not level_subsystem.save_current_level():
    raise RuntimeError("Unable to save station map after reference scene placement")
report_path = Path(unreal.Paths.project_saved_dir()) / "HRS" / "reference-scenes.json"
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps({
    "level": LEVEL_PATH,
    "destination": DESTINATION,
    "scale_validation": "PASS",
    "physics_capacity_changed": False,
    "placements": results,
}, ensure_ascii=False, indent=2), encoding="utf-8")
unreal.log(f"HRS reference scene placement complete: {report_path}")
