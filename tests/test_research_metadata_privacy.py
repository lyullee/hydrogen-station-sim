from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
LOCAL_PATH = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]+(?:Users|home)[\\/]|\\\\(?:Users|home)[\\/]|/(?:Users|home)/)"
)


def test_research_metadata_does_not_publish_workstation_paths():
    violations: list[str] = []
    for path in RESEARCH.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if LOCAL_PATH.search(text):
            violations.append(path.relative_to(ROOT).as_posix())
    assert violations == []
