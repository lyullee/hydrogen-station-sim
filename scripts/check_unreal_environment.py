"""Inspect installation prerequisites without reading accounts or credentials."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess


def inspect():
    roots = [Path("C:/Program Files/Epic Games"), Path("D:/Epic Games")]
    if os.getenv("HRS_UNREAL_ROOT"):
        roots.insert(0, Path(os.environ["HRS_UNREAL_ROOT"]))
    candidates = []
    for root in roots:
        if root.is_dir():
            candidates.append(root)
            candidates.extend(path for path in root.glob("UE_*") if path.is_dir())
    engines = []
    for path in candidates:
        if (path / "Engine/Binaries/Win64/UnrealEditor.exe").is_file():
            version_file = path / "Engine/Build/Build.version"
            version = json.loads(version_file.read_text()) if version_file.is_file() else {}
            engines.append({"root": str(path), "version": ".".join(str(version.get(k, "?"))
                for k in ("MajorVersion", "MinorVersion", "PatchVersion"))})
    vswhere = Path("C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe")
    toolchains = []
    if vswhere.is_file():
        result = subprocess.run([str(vswhere), "-products", "*", "-requires",
            "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"],
            capture_output=True, text=True, check=False)
        toolchains = result.stdout.strip().splitlines()
    launcher = Path("C:/Program Files/Epic Games/Launcher/Portal/Binaries/Win64/EpicGamesLauncher.exe")
    return {"launcher_installed": launcher.is_file(), "engines": engines,
            "cpp_toolchains": toolchains, "free_disk_gib": round(shutil.disk_usage(Path.cwd().anchor).free / 1024**3, 1),
            "engine_build_status": "READY_TO_ATTEMPT" if engines and toolchains else "PREREQUISITES_PENDING"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = inspect()
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
