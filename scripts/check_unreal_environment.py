"""Inspect installation prerequisites without reading accounts or credentials."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def _toolchain_candidates() -> list[Path]:
    """Return usable VS C++ roots even when VS instance registration is stale.

    A completed Build Tools installation can temporarily be absent from
    ``vswhere`` until Windows restarts.  UnrealBuildTool ultimately needs the
    compiler, MSBuild and an SDK, so inspect those artifacts as a safe fallback
    instead of reporting the machine as unprepared.
    """
    roots: list[Path] = []
    vswhere = Path(
        "C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe"
    )
    if vswhere.is_file():
        result = subprocess.run(
            [
                str(vswhere),
                "-products",
                "*",
                "-requires",
                "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                "-property",
                "installationPath",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        roots.extend(Path(line) for line in result.stdout.splitlines() if line.strip())

    conventional = Path(
        "C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools"
    )
    if conventional.is_dir():
        roots.append(conventional)

    unique: list[Path] = []
    for root in roots:
        resolved = root.resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique


def _inspect_toolchains() -> list[dict[str, object]]:
    toolchains: list[dict[str, object]] = []
    sdk_root = Path("C:/Program Files (x86)/Windows Kits/10")
    sdk_versions = sorted(
        (path.name for path in (sdk_root / "Lib").glob("10.*") if path.is_dir()),
        reverse=True,
    ) if (sdk_root / "Lib").is_dir() else []

    for root in _toolchain_candidates():
        msvc_root = root / "VC/Tools/MSVC"
        compiler_versions = sorted(
            path.name
            for path in msvc_root.glob("*")
            if (path / "bin/Hostx64/x64/cl.exe").is_file()
        ) if msvc_root.is_dir() else []
        msbuild = root / "MSBuild/Current/Bin/MSBuild.exe"
        usable = bool(compiler_versions and msbuild.is_file() and sdk_versions)
        toolchains.append(
            {
                "root": str(root),
                "compiler_versions": compiler_versions,
                "msbuild": str(msbuild) if msbuild.is_file() else None,
                "windows_sdk_versions": sdk_versions,
                "usable": usable,
            }
        )
    return toolchains


def _inspect_epic_entitlement() -> dict[str, object]:
    """Classify the Launcher UE catalog state without exposing account data."""
    local_app_data = os.getenv("LOCALAPPDATA")
    if not local_app_data:
        return {"status": "UNKNOWN", "reason": "LOCALAPPDATA is unavailable"}
    log_root = Path(local_app_data) / "EpicGamesLauncher/Saved/Logs"
    logs = sorted(
        log_root.glob("*.log"), key=lambda path: path.stat().st_mtime, reverse=True
    ) if log_root.is_dir() else []
    if not logs:
        return {"status": "UNKNOWN", "reason": "Launcher log is unavailable"}

    text = logs[0].read_text(encoding="utf-8", errors="replace")
    counts = [int(value) for value in re.findall(r"found (\d+) entitled apps", text)]
    zero_items = "Loaded 0 item files" in text
    waiting = "WaitingForBuildsAndItemFiles" in text
    if counts and counts[-1] == 0 and zero_items and waiting:
        status = "ZERO_ENTITLEMENTS"
        reason = "Launcher received no UE item files or entitled apps"
    elif counts and counts[-1] > 0:
        status = "ENTITLEMENTS_PRESENT"
        reason = f"Launcher reported {counts[-1]} entitled apps"
    else:
        status = "UNKNOWN"
        reason = "Launcher log has no conclusive entitlement count"
    return {
        "status": status,
        "reason": reason,
        "latest_log": logs[0].name,
    }


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
    toolchains = _inspect_toolchains()
    usable_toolchain = any(item["usable"] for item in toolchains)
    launcher_candidates = [
        Path("C:/Program Files/Epic Games/Launcher/Portal/Binaries/Win64/EpicGamesLauncher.exe"),
        Path("C:/Program Files (x86)/Epic Games/Launcher/Portal/Binaries/Win64/EpicGamesLauncher.exe"),
        Path("C:/Program Files (x86)/Epic Games/Launcher/Portal/Binaries/Win32/EpicGamesLauncher.exe"),
    ]
    launcher = next((path for path in launcher_candidates if path.is_file()), None)
    return {"launcher_installed": launcher is not None,
            "launcher_path": str(launcher) if launcher else None, "engines": engines,
            "epic_entitlement": _inspect_epic_entitlement(),
            "cpp_toolchains": toolchains, "free_disk_gib": round(shutil.disk_usage(Path.cwd().anchor).free / 1024**3, 1),
            "engine_build_status": "READY_TO_ATTEMPT" if engines and usable_toolchain else "PREREQUISITES_PENDING"}


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
