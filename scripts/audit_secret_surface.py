"""Privacy-safe static scan for credentials in tracked source files.

The scan intentionally reports classifications and variable names only.  It
does not print candidate values, and it is not a runtime or git-history scan.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


TEXT_SUFFIXES = {
    ".bat", ".cfg", ".cmd", ".env", ".example", ".ini", ".js", ".json",
    ".md", ".mjs", ".ps1", ".py", ".sh", ".toml", ".ts", ".tsx", ".txt",
    ".yaml", ".yml",
}
HIGH_CONFIDENCE_PATTERNS = {
    "openai": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "groq": re.compile(r"\bgsk_[A-Za-z0-9_-]{20,}\b"),
    "xai": re.compile(r"\bxai-[A-Za-z0-9_-]{20,}\b"),
    "google": re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    "github": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
_SECRET_SUFFIX = r"(?:API_KEY|ACCESS_KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH)"
ENV_NAME = re.compile(rf"\b([A-Z][A-Z0-9_]*_(?:{_SECRET_SUFFIX}))(?:\b|=)")
ENV_ASSIGNMENT = re.compile(
    rf"^\s*([A-Z][A-Z0-9_]*{_SECRET_SUFFIX}[A-Z0-9_]*)\s*=\s*(.*?)\s*(?:#.*)?$",
    re.I,
)
PLACEHOLDER = re.compile(
    r"^(?:$|none|null|unset|your[_ -].*|change[_ -]?me|replace[_ -].*|placeholder|dummy|example|<.*>|\*+)$",
    re.I,
)


def tracked_files(root: Path) -> list[Path]:
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
    return [root / item for item in raw.decode("utf-8", "surrogateescape").split("\0") if item]


def value_classification(value: str) -> str:
    value = value.strip().strip("\"'")
    if not value or PLACEHOLDER.fullmatch(value):
        return "empty_or_placeholder"
    return "nonempty_unverified"


def scan(root: Path) -> dict[str, object]:
    files = tracked_files(root)
    scanned = 0
    hits: list[dict[str, object]] = []
    assignments: list[dict[str, object]] = []
    env_files: list[str] = []
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name.lower() not in {".env", ".env.example", ".env.template"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned += 1
        if path.name.lower().startswith(".env"):
            env_files.append(path.relative_to(root).as_posix())
        for line_no, line in enumerate(text.splitlines(), 1):
            for kind, pattern in HIGH_CONFIDENCE_PATTERNS.items():
                if pattern.search(line):
                    hits.append({"file": path.relative_to(root).as_posix(), "line": line_no, "kind": kind})
            # Source files contain ordinary identifiers such as ``event_token``
            # and ``*_pass``.  Assignment classification is meaningful only in
            # dotenv/config files, so do not treat Python/JS locals as secrets.
            match = ENV_ASSIGNMENT.match(line) if path.name.lower().startswith(".env") else None
            if match:
                name, value = match.groups()
                assignments.append({
                    "file": path.relative_to(root).as_posix(),
                    "line": line_no,
                    "name": name,
                    "classification": value_classification(value),
                })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "tracked text files only; values are never emitted",
        "tracked_files": len(files),
        "scanned_text_files": scanned,
        "env_files": env_files,
        "high_confidence_secret_hits": hits,
        "environment_assignments": assignments,
        "provider_boundary": {
            "keys_are_expected_from_runtime_environment": True,
            "known_endpoint_variables": [
                "H2STATION_SAGA_URL", "H2STATION_SAGA_DIRECT_URL",
                "H2STATION_SAGA_CHAT_TIMEOUT_S", "H2STATION_HYRAM_EVALUATOR",
            ],
        },
        "limitations": [
            "This is a static working-tree scan and does not inspect untracked files, host environment variables, or git object history.",
            "Nonempty values in tracked configuration would require manual review; no secret value is disclosed by this report.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = scan(args.root.resolve())
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0 if not payload["high_confidence_secret_hits"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
