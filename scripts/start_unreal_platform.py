"""Start the complete HRS dashboard and Unreal Pixel Streaming stack.

This is the PyCharm entry point. It keeps the Python API, signalling server,
and Unreal as separate child processes while presenting one Run/Stop lifecycle.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser


ROOT = Path(__file__).resolve().parents[1]
API_URL = "http://127.0.0.1:8000"
PLAYER_URL = "http://127.0.0.1:18080/hrs-player.html"
PROJECT = ROOT / "unreal" / "HRSUnreal" / "HRSUnreal.uproject"
NODE = ROOT / "unreal" / ".tooling" / "node-v22.15.0-win-x64" / "node.exe"
SIGNALLING_ROOT = ROOT / "unreal" / "PixelStreamingInfrastructure" / "SignallingWebServer"
SIGNALLING_ENTRY = SIGNALLING_ROOT / "dist" / "index.js"
SIGNALLING_WWW = SIGNALLING_ROOT / "www"
SIGNALLING_WRAPPER = ROOT / "scripts" / "pixel_streaming_local.cjs"


def http_json(url: str, timeout: float = 2.0) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.load(response)
    except (OSError, ValueError, urllib.error.URLError):
        return None


def http_ready(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 400
    except (OSError, urllib.error.URLError):
        return False


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def wait_until(label: str, predicate, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            print(f"[READY] {label}", flush=True)
            return
        time.sleep(0.4)
    raise RuntimeError(f"{label} did not become ready within {timeout:.0f} seconds")


def find_unreal_editor() -> Path:
    candidates = []
    configured = os.environ.get("HRS_UNREAL_ENGINE_ROOT") or os.environ.get("HRS_UNREAL_ROOT")
    if configured:
        candidates.append(Path(configured))
    candidates.extend(
        [
            Path(r"C:\Program Files\Epic Games\UE_5.8"),
            Path(r"C:\Program Files\Epic Games\UE_5.7"),
            Path(r"C:\Program Files\Epic Games\UE_5.6"),
        ]
    )
    for engine in candidates:
        editor = engine / "Engine" / "Binaries" / "Win64" / "UnrealEditor.exe"
        if editor.is_file():
            return editor
    raise FileNotFoundError(
        "UnrealEditor.exe was not found. Set HRS_UNREAL_ENGINE_ROOT to the installed UE directory."
    )


def hrs_unreal_running() -> bool:
    command = (
        "$p=Get-CimInstance Win32_Process -Filter \"Name='UnrealEditor.exe'\" | "
        "Where-Object {$_.CommandLine -like '*HRSUnreal.uproject*'} | Select-Object -First 1; "
        "if($p){$p.ProcessId}"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        text=True,
        capture_output=True,
        check=False,
    )
    return bool(result.stdout.strip())


def require_files(editor: Path) -> None:
    required = [
        editor,
        PROJECT,
        NODE,
        SIGNALLING_ENTRY,
        SIGNALLING_WRAPPER,
        ROOT / "unreal" / "player" / "hrs-player.html",
        ROOT / "unreal" / "player" / "hrs-player.js",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required runtime files are missing:\n" + "\n".join(missing))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the complete HRS Unreal platform")
    parser.add_argument("--check", action="store_true", help="validate prerequisites without starting processes")
    parser.add_argument("--no-browser", action="store_true", help="do not open the dashboard in a browser")
    parser.add_argument("--startup-timeout", type=float, default=90.0)
    args = parser.parse_args()
    external = os.environ.get("HRS_EXTERNAL_ACCESS", "1").strip().lower() not in {"0", "false", "off", "no"}
    api_bind = "0.0.0.0" if external else "127.0.0.1"

    editor = find_unreal_editor()
    require_files(editor)
    print(f"[OK] repository: {ROOT}")
    print(f"[OK] Python: {sys.executable}")
    print(f"[OK] Unreal: {editor}")
    if args.check:
        print(
            json.dumps(
                {
                    "api_ready": http_json(f"{API_URL}/api/health") is not None,
                    "player_ready": http_ready(PLAYER_URL),
                    "streamer_port_ready": port_open(18888),
                    "hrs_unreal_running": hrs_unreal_running(),
                },
                ensure_ascii=False,
            )
        )
        return 0

    children: list[tuple[str, subprocess.Popen]] = []
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    env = os.environ.copy()
    env["H2STATION_UNREAL_PLAYER_URL"] = PLAYER_URL
    env["PYTHONUNBUFFERED"] = "1"
    env["HRS_PIXEL_STREAMING_PUBLIC_PORTS"] = "18080" if external else ""
    source_path = str(ROOT / "src")
    env["PYTHONPATH"] = source_path + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

    try:
        health = http_json(f"{API_URL}/api/health")
        if health is None:
            if port_open(8000):
                raise RuntimeError("Port 8000 is occupied by a non-HRS process")
            process = subprocess.Popen(
                [sys.executable, "-m", "h2station", "--host", api_bind, "--port", "8000"],
                cwd=ROOT,
                env=env,
                creationflags=creationflags,
            )
            children.append(("Python API", process))
            wait_until("Python API", lambda: http_json(f"{API_URL}/api/health") is not None, args.startup_timeout)
        else:
            config = http_json(f"{API_URL}/api/integrations/unreal/config") or {}
            if config.get("player_url") != PLAYER_URL:
                raise RuntimeError(
                    "An HRS API is already running without the Unreal player setting. Stop that server and run this configuration again."
                )
            print("[REUSE] Python API already running", flush=True)

        if not http_ready(PLAYER_URL):
            if port_open(18080) or port_open(18888):
                raise RuntimeError("Pixel Streaming ports are partially occupied. Stop the old streaming process first.")
            SIGNALLING_WWW.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / "unreal" / "player" / "hrs-player.html", SIGNALLING_WWW / "hrs-player.html")
            shutil.copy2(ROOT / "unreal" / "player" / "hrs-player.js", SIGNALLING_WWW / "hrs-player.js")
            process = subprocess.Popen(
                [
                    str(NODE), str(SIGNALLING_WRAPPER), str(SIGNALLING_ENTRY),
                    "--no_config", "--serve", "--player_port", "18080",
                    "--streamer_port", "18888", "--sfu_port", "18889",
                    "--http_root", str(SIGNALLING_WWW), "--homepage", "hrs-player.html",
                ],
                cwd=ROOT,
                env=env,
                creationflags=creationflags,
            )
            children.append(("Pixel Streaming", process))
            wait_until("Pixel Streaming", lambda: http_ready(PLAYER_URL), args.startup_timeout)
        elif not port_open(18888):
            raise RuntimeError("The player port is open but the Unreal streamer port is unavailable")
        else:
            print("[REUSE] Pixel Streaming already running", flush=True)

        if not hrs_unreal_running():
            process = subprocess.Popen(
                [
                    str(editor), str(PROJECT), "-game", "-windowed", "-ForceRes",
                    "-ResX=1920", "-ResY=1080", "-RenderOffscreen", "-AudioMixer",
                    "-PixelStreamingURL=ws://127.0.0.1:18888", f"-HRSApi={API_URL}",
                    "-HRSRenderer=default",
                ],
                cwd=ROOT,
                creationflags=creationflags,
            )
            children.append(("Unreal Engine", process))
            wait_until("Unreal Engine process", lambda: hrs_unreal_running(), args.startup_timeout)
        else:
            print("[REUSE] HRS Unreal process already running", flush=True)

        print(f"[READY] HRS platform: {API_URL}/", flush=True)
        if external:
            print("[READY] External listeners: TCP 8000 (dashboard), TCP 18080 (Unreal player)", flush=True)
        if not args.no_browser:
            webbrowser.open(f"{API_URL}/")
        print("Press PyCharm Stop to close processes started by this run.", flush=True)
        while True:
            for name, process in children:
                code = process.poll()
                if code is not None:
                    raise RuntimeError(f"{name} exited unexpectedly with code {code}")
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopping HRS Unreal platform...", flush=True)
    finally:
        for name, process in reversed(children):
            if process.poll() is None:
                print(f"[STOP] {name}", flush=True)
                process.terminate()
        for _, process in reversed(children):
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
