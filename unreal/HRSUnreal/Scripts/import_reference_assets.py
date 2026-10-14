"""Import validated public-reference GLB files into the UE project.

Run through UnrealEditor-Cmd after ``export_unreal_assets.cjs`` and the Khronos
validator.  The importer never replaces an existing edited asset.  Imported
geometry is a visual reference only and does not change simulator capacity or
physics parameters.
"""
from __future__ import annotations

import json
from pathlib import Path

import unreal


PROJECT_DIR = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
REPO_DIR = PROJECT_DIR.parents[1]
SOURCE_DIR = REPO_DIR / "output" / "unreal" / "assets"
DESTINATION = "/Game/HRS/Models"
EXPECTED = {
    "storage-low", "storage-medium", "storage-high", "compressor",
    "precooler", "vehicle", "tube-trailer",
}


def load_validation() -> dict:
    validation_path = SOURCE_DIR / "validation.json"
    if not validation_path.is_file():
        raise RuntimeError(f"Missing Khronos validation report: {validation_path}")
    report = json.loads(validation_path.read_text(encoding="utf-8"))
    if report.get("status") != "PASS":
        raise RuntimeError("Refusing to import GLB files without a PASS validation report")
    validated = {Path(row["file"]).stem for row in report.get("assets", [])
                 if row.get("errors") == 0}
    missing = sorted(EXPECTED - validated)
    if missing:
        raise RuntimeError("Validated asset set is incomplete: " + ", ".join(missing))
    return report


def import_asset(name: str) -> list[str]:
    existing = unreal.EditorAssetLibrary.list_assets(f"{DESTINATION}/{name}", recursive=True)
    if existing:
        unreal.log(f"HRS import preserved existing {name}: {len(existing)} objects")
        return list(existing)
    source = SOURCE_DIR / f"{name}.glb"
    if not source.is_file():
        raise RuntimeError(f"Missing exported asset: {source}")
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(source))
    task.set_editor_property("destination_path", f"{DESTINATION}/{name}")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("save", True)
    # UE 5.6 exposes GLTFImportOptions.  Default importer settings remain a
    # safe fallback because glTF carries metres/Y-up metadata itself.
    options_type = getattr(unreal, "GLTFImportOptions", None)
    if options_type is not None:
        options = options_type()
        if hasattr(options, "import_scale"):
            options.set_editor_property("import_scale", 1.0)
        task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = list(task.get_editor_property("imported_object_paths"))
    if not imported:
        raise RuntimeError(f"Unreal imported no objects from {source}")
    unreal.log(f"HRS imported {name}: {len(imported)} objects")
    return imported


load_validation()
results = {name: import_asset(name) for name in sorted(EXPECTED)}
report_path = Path(unreal.Paths.project_saved_dir()) / "HRS" / "reference-assets.json"
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps({
    "source": str(SOURCE_DIR),
    "destination": DESTINATION,
    "physics_capacity_changed": False,
    "assets": results,
}, ensure_ascii=False, indent=2), encoding="utf-8")
unreal.log(f"HRS reference model import complete: {report_path}")
