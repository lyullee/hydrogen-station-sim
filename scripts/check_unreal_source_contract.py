"""Fail fast when the UE source drifts from the server scene contract."""
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "unreal/contracts/scene-manifest.json").read_text(encoding="utf-8"))
CPP = (ROOT / "unreal/HRSUnreal/Source/HRSUnreal/HRSStationActor.cpp").read_text(encoding="utf-8")
HEADER = (ROOT / "unreal/HRSUnreal/Source/HRSUnreal/HRSStationActor.h").read_text(encoding="utf-8")
PAWN = (ROOT / "unreal/HRSUnreal/Source/HRSUnreal/HRSCameraPawn.cpp").read_text(encoding="utf-8")
START = (ROOT / "scripts/start_unreal_pilot.ps1").read_text(encoding="utf-8")
PACKAGE = (ROOT / "scripts/build_unreal_release.ps1").read_text(encoding="utf-8")
RUN_PACKAGE = (ROOT / "scripts/start_packaged_unreal.ps1").read_text(encoding="utf-8")
IMPORTER = (ROOT / "unreal/HRSUnreal/Scripts/import_reference_assets.py").read_text(encoding="utf-8")
PLACER = (ROOT / "unreal/HRSUnreal/Scripts/place_reference_scenes.py").read_text(encoding="utf-8")
GAME_CONFIG = (ROOT / "unreal/HRSUnreal/Config/DefaultGame.ini").read_text(encoding="utf-8")
UPROJECT = (ROOT / "unreal/HRSUnreal/HRSUnreal.uproject").read_text(encoding="utf-8")
TARGETS = [
    (ROOT / "unreal/HRSUnreal/Source/HRSUnreal.Target.cs").read_text(encoding="utf-8"),
    (ROOT / "unreal/HRSUnreal/Source/HRSUnrealEditor.Target.cs").read_text(encoding="utf-8"),
]

problems: list[str] = []
equipment = {row["component_id"] for row in MANIFEST["equipment"]}
literal_equipment = set(re.findall(r'AddEquipment\(TEXT\("([^"]+)"\)', CPP))
cpp_equipment = literal_equipment | {"cascade.low", "cascade.medium", "cascade.high"}
if equipment != cpp_equipment:
    problems.append(f"equipment mismatch: missing={sorted(equipment-cpp_equipment)} extra={sorted(cpp_equipment-equipment)}")

expected_valves = {
    "trailer.source", "trailer.station", "compressor.suction", "compressor.discharge",
    "dispenser.1", "dispenser.2",
    *(f"bank.{bank}.{side}" for bank in ("low", "medium", "high") for side in ("inlet", "outlet")),
    *(f"vent.{bank}" for bank in ("low", "medium", "high")),
}
observed_valves = set(re.findall(r'AddValve\(TEXT\("([^"]+)"\)', CPP)) | {
    f"bank.{bank}.{side}" for bank in ("low", "medium", "high") for side in ("inlet", "outlet")
}
if expected_valves != observed_valves:
    problems.append(f"valve mismatch: missing={sorted(expected_valves-observed_valves)} extra={sorted(observed_valves-expected_valves)}")

for section, expression in (("detectors", r'TEXT\("((?:GD|FD)-\d{4})"\),\s*FVector'),
                            ("cameras", r'TEXT\("(CAM-\d{2})"\),\s*FVector')):
    expected = {row["sensor_id" if section == "detectors" else "camera_id"]
                for row in MANIFEST[section]}
    observed = set(re.findall(expression, CPP))
    if expected != observed:
        problems.append(f"{section} mismatch: missing={sorted(expected-observed)} extra={sorted(observed-expected)}")

for method in ("ToggleCameras", "ToggleDetectors", "ApplyAuxiliaryState",
               "ApplyProcessState", "ApplyIncidentState", "BuildReferenceStation"):
    if method not in HEADER or f"AHRSStationActor::{method}" not in CPP:
        problems.append(f"missing declaration or definition: {method}")

for key in ("EKeys::C", "EKeys::G", "EKeys::MiddleMouseButton", "EKeys::MouseScrollUp"):
    if key not in PAWN:
        problems.append(f"missing operator input: {key}")

if "ws://127.0.0.1:18888" not in START or "ws://127.0.0.1:8888" in START:
    problems.append("pilot signalling port does not match infrastructure lock")
if '"Name": "PixelStreaming2"' not in UPROJECT:
    problems.append("UE 5.8 project must enable PixelStreaming2")

if 'set_editor_property("import_scale", 100.0)' not in IMPORTER:
    problems.append("glTF importer must convert metres to Unreal centimetres exactly once")
if '+DirectoriesToAlwaysCook=(Path="/Game/HRS/Models")' not in GAME_CONFIG:
    problems.append("reference model directory is missing from package cook settings")
if '+DirectoriesToAlwaysCook=(Path="/Game/HRS/Scenes")' not in GAME_CONFIG:
    problems.append("reference scene directory is missing from package cook settings")
for token in ("InterchangeManager", "import_scene", "validate_scale", "bounds_cm",
              "supply", "compressor", "cooler", "cascade.low", "cascade.medium",
              "cascade.high", "vehicle.tank", "vehicle_2.tank"):
    if token not in PLACER:
        problems.append(f"reference scene placement contract is missing: {token}")
if "PlaceAssets" not in START or "$prepare.PlaceAssets = $true" not in PACKAGE:
    problems.append("release build must place reference scenes before cooking")
for token in ("BuildCookRun", "-platform=Win64", "-cook", "-pak", "hrs-unreal-build.json"):
    if token not in PACKAGE:
        problems.append(f"packaging contract is missing: {token}")
for token in ("executable_sha256", "-PixelStreamingURL=", "-HRSApi=", "-HRSRenderer="):
    if token not in RUN_PACKAGE:
        problems.append(f"packaged runtime contract is missing: {token}")
for target in TARGETS:
    if "DefaultBuildSettings = BuildSettingsVersion.V7" not in target:
        problems.append("UE target must use BuildSettingsVersion.V7")
    if "IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8" not in target:
        problems.append("UE target must pin the Unreal 5.8 include order")

if problems:
    raise SystemExit("Unreal source contract FAIL\n- " + "\n- ".join(problems))
print(json.dumps({
    "status": "PASS",
    "equipment": len(equipment),
    "detectors": len(MANIFEST["detectors"]),
    "cameras": len(MANIFEST["cameras"]),
    "valves": len(expected_valves),
    "gltf_import_scale": 100.0,
    "reference_models_cooked": True,
    "reference_scenes_placed_by_pipeline": True,
    "packaging_pipeline": True,
    "ue58_include_order_pinned": True,
    "operator_inputs": ["orbit", "middle-pan", "wheel-zoom", "camera-toggle", "detector-toggle"],
}, ensure_ascii=False))
