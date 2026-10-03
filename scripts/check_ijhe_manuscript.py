"""Check the local IJHE working manuscript against explicit journal limits.

This is a format and completeness guard, not a scientific-quality or acceptance
test.  Current limits are recorded in ``manuscript/submission_readiness.md`` with
the official Guide for Authors URL and access date.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def _plain_text(latex: str) -> str:
    text = re.sub(r"%.*", " ", latex)
    text = re.sub(r"\\(?:href|url)\{[^}]*\}(?:\{([^}]*)\})?", r" \1 ", text)
    text = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^]]*\])?", " ", text)
    text = text.replace("~", " ")
    text = re.sub(r"[{}$\\]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _environment(source: str, name: str) -> str:
    match = re.search(
        rf"\\begin\{{{re.escape(name)}\}}(.*?)\\end\{{{re.escape(name)}\}}",
        source,
        flags=re.DOTALL,
    )
    if not match:
        raise ValueError(f"missing {name} environment")
    return match.group(1)


def check(manuscript: Path, highlights: Path) -> dict[str, object]:
    source = manuscript.read_text(encoding="utf-8")
    abstract = _plain_text(_environment(source, "abstract"))
    abstract_words = len(abstract.split())

    keyword_match = re.search(
        r"\\textbf\{Keywords:\}\s*(.*?)(?:\n\s*\n|\\section)",
        source,
        flags=re.DOTALL,
    )
    if not keyword_match:
        raise ValueError("missing Keywords field")
    keywords = [
        item.strip()
        for item in _plain_text(keyword_match.group(1)).split(";")
        if item.strip()
    ]

    highlight_lines = [
        line.strip().lstrip("•- ").strip()
        for line in highlights.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    highlight_lengths = [len(line) for line in highlight_lines]
    figure_count = len(re.findall(r"\\begin\{figure\}", source))
    table_count = len(re.findall(r"\\begin\{table\}", source))
    body_before_references = source.split(r"\begin{thebibliography}", 1)[0]
    approximate_words = len(_plain_text(body_before_references).split())

    checks = {
        "abstract_at_most_150_words": abstract_words <= 150,
        "keywords_at_most_6": len(keywords) <= 6,
        "highlights_count_3_to_5": 3 <= len(highlight_lines) <= 5,
        "each_highlight_at_most_85_characters": all(
            length <= 85 for length in highlight_lengths
        ),
        "research_paper_at_most_8000_words_approximate": approximate_words <= 8000,
        "diagrams_at_most_12": figure_count <= 12,
    }
    return {
        "manuscript": str(manuscript),
        "highlights": str(highlights),
        "counts": {
            "abstract_words": abstract_words,
            "keywords": len(keywords),
            "highlight_bullets": len(highlight_lines),
            "highlight_characters": highlight_lengths,
            "approximate_manuscript_words_before_references": approximate_words,
            "figures": figure_count,
            "tables": table_count,
        },
        "checks": checks,
        "format_gate_passed": all(checks.values()),
        "scientific_readiness_assessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manuscript",
        type=Path,
        default=Path("manuscript/ijhe_manuscript_draft.tex"),
    )
    parser.add_argument(
        "--highlights", type=Path, default=Path("manuscript/Highlights.txt")
    )
    args = parser.parse_args()
    result = check(args.manuscript, args.highlights)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["format_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
