"""Validate the non-evidentiary external-data acquisition tracker."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_FIELDS = {
    "id", "draft", "source", "candidate_type", "status", "requested_fields",
    "minimum_acceptance", "rights", "next_action", "claim_boundary",
}


def audit(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    candidates = data.get("candidates") or []
    root = path.parent.parent
    errors: list[str] = []
    if data.get("status") != "open_data_not_yet_received":
        errors.append("tracker status must remain open_data_not_yet_received")
    boundary = str(data.get("claim_boundary", ""))
    if "not evidence" not in boundary.lower() or "does not change" not in boundary.lower():
        errors.append("global claim boundary must prevent evidence overclaim")
    common = data.get("common_acceptance") or {}
    for key in ("required_for_full_loop", "preferred", "freeze_protocol"):
        if not common.get(key):
            errors.append(f"common_acceptance.{key} missing")
    seen: set[str] = set()
    for index, candidate in enumerate(candidates):
        missing = sorted(REQUIRED_FIELDS - candidate.keys())
        if missing:
            errors.append(f"candidate[{index}] missing: {', '.join(missing)}")
        cid = candidate.get("id")
        if cid in seen:
            errors.append(f"duplicate candidate id: {cid}")
        seen.add(str(cid))
        draft = candidate.get("draft")
        if not isinstance(draft, str) or not (root / draft).is_file():
            errors.append(f"candidate[{index}] draft missing: {draft}")
        if not str(candidate.get("source", "")).startswith(("http://", "https://")):
            errors.append(f"candidate[{index}] source is not a URL")
        if not isinstance(candidate.get("requested_fields"), list) or not candidate.get("requested_fields"):
            errors.append(f"candidate[{index}] requested_fields empty")
        for field in ("minimum_acceptance", "rights", "next_action", "claim_boundary"):
            if not str(candidate.get(field, "")).strip():
                errors.append(f"candidate[{index}] {field} empty")
    return {
        "schema_version": 1,
        "status": "PASS" if not errors else "FAIL",
        "candidate_count": len(candidates),
        "request_draft_count": sum(
            1 for candidate in candidates if candidate.get("status") == "request_draft_ready"
        ),
        "errors": errors,
        "claim_boundary": data.get("claim_boundary"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=Path,
        default=Path("research/validation_data_acquisition_tracker.json"),
    )
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    report = audit(args.input)
    if args.markdown_output:
        lines = [
            "# Validation data-acquisition tracker audit", "",
            f"- Status: **{report['status']}**",
            f"- Candidates: **{report['candidate_count']}**",
            f"- Draft-ready requests: **{report['request_draft_count']}**", "",
            "This is a planning and provenance audit. It is not external validation and does not close the IJHE readiness gates.", "",
        ]
        if report["errors"]:
            lines.extend(["## Errors", "", *[f"- {error}" for error in report["errors"]]])
        args.markdown_output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
