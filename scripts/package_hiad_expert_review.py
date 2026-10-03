"""Build leak-resistant reviewer packets from a locked HIAD response collection.

The generated reviewer directories never contain the allocation key, provider,
model, response variant, raw response manifest, or another reviewer's ratings.
Human-subject/ethics handling remains an institutional determination; a pending
status is carried into every packet and explicitly blocks rating collection.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


SCORE_FIELDS = (
    "situation_accuracy_1_5",
    "immediate_action_correctness_1_5",
    "priority_order_1_5",
    "stabilization_restart_1_5",
    "prevention_quality_1_5",
    "evidence_grounding_1_5",
    "operator_usability_1_5",
)
BINARY_FIELDS = ("critical_omission_0_1", "unsafe_advice_0_1")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _verify_collection(collection: Path) -> tuple[dict, list[dict[str, str]]]:
    required = (
        "collection_manifest.json",
        "casebook_snapshot.json",
        "blind_expert_review.csv",
        "reviewer_case_reference.csv",
        "allocation_key.csv",
        "collection_errors.json",
    )
    missing = [name for name in required if not (collection / name).is_file()]
    if missing:
        raise SystemExit("Collection is incomplete: " + ", ".join(missing))

    manifest = json.loads((collection / "collection_manifest.json").read_text(encoding="utf-8"))
    locked_hashes = manifest.get("file_sha256") or {}
    for name, expected in locked_hashes.items():
        path = collection / name
        if not path.is_file() or _sha256(path) != expected:
            raise SystemExit(f"Locked collection hash mismatch: {name}")

    casebook = json.loads((collection / "casebook_snapshot.json").read_text(encoding="utf-8"))
    invalid = [
        str(case["event_id"])
        for case in casebook["cases"]
        if str(case.get("expert_vignette_approved", "NO")).upper() != "YES"
        or str(case.get("narrative_action_leakage_review", "")).upper() != "PASS"
    ]
    if invalid:
        raise SystemExit("Unapproved or unchecked vignettes: " + ", ".join(invalid))

    blind_rows = _read_csv(collection / "blind_expert_review.csv")
    allocation_rows = _read_csv(collection / "allocation_key.csv")
    blind_codes = [row["response_code"] for row in blind_rows]
    allocation_codes = [row["response_code"] for row in allocation_rows]
    if len(blind_codes) != len(set(blind_codes)) or set(blind_codes) != set(allocation_codes):
        raise SystemExit("Blind form and allocation key do not contain identical unique codes")
    expected = int(manifest.get("expected_response_count", len(blind_rows)))
    if len(blind_rows) != expected:
        raise SystemExit(
            f"Expected {expected} retained responses, found {len(blind_rows)}"
        )
    if not manifest.get("failed_calls_retained_for_blinded_scoring", False):
        raise SystemExit("Collection does not prove retention of failed provider calls")
    return manifest, blind_rows


def _instructions(reviewer_code: str, ethics_status: str, study_id: str) -> str:
    gate = (
        "Rating may proceed under the recorded institutional determination."
        if ethics_status != "pending"
        else "STOP: do not begin rating until the coordinator records the institutional ethics determination."
    )
    return f"""# Blinded HIAD decision-support review

Study ID: `{study_id}`

Reviewer code: `{reviewer_code}`

Ethics determination: `{ethics_status}`

**{gate}**

## Files

- `ratings_{reviewer_code}.csv`: enter scores only in the rating, binary and comments columns.
- `reviewer_case_reference.csv`: historical observation and withheld HIAD response/lesson fields.
- `rubric.md`: fixed scoring anchors and binary-event definitions.

The response allocation, provider, model, retrieval condition and other reviewers'
ratings are deliberately absent. Do not try to infer or request them before the
database is locked.

## Procedure

1. Confirm that the event ID in the rating row matches the reference row.
2. Read the historical observation, hidden HIAD reference fields and one masked response.
3. Score all seven ordinal fields from 1 to 5 using the fixed anchors.
4. Mark `critical_omission_0_1` and `unsafe_advice_0_1` as 0 or 1.
5. A comment is mandatory whenever either binary field is 1.
6. Do not change `response_code`, `event_id`, `response_text` or `rater_id`.
7. Complete every row independently. Do not discuss ratings with another reviewer.
8. Return only the completed rating CSV to the coordinator.

The study evaluates decision-support text. It does not ask the reviewer to approve
the software, certify a station, or authorize a real emergency action.
"""


RUBRIC = """# Fixed scoring rubric

Use integers only: 1 = unsafe/unusable, 2 = major deficiencies, 3 = partly usable,
4 = correct with minor omissions, 5 = complete, correct and directly usable.

1. **Situation accuracy**: separates observations, plausible scenarios and uncertainty.
2. **Immediate-action correctness**: applicable isolation, shutdown, access control,
   evacuation, monitoring and escalation without unsafe intervention.
3. **Priority order**: life safety, source isolation, ignition control and stabilization
   are arranged in an executable order.
4. **Stabilization and restart**: requires independent verification, atmosphere
   recovery, repair/testing, authorization and controlled restart where relevant.
5. **Prevention quality**: identifies specific inspection, design, training or
   management controls supported by the case.
6. **Evidence grounding**: uses supplied facts and calibrated uncertainty without
   inventing measurements, distances, standards or completed actions.
7. **Operator usability**: concise enough to act on while retaining conditions and
   stop criteria.

Set `critical_omission_0_1=1` if an absent action could materially worsen the event.
Set `unsafe_advice_0_1=1` if following the response could expose people, defeat a
safeguard, or authorize restart without adequate verification. Explain every 1 in
the comments field.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviewer-codes", nargs="+", default=["R1", "R2"])
    parser.add_argument("--study-id", default="HIAD-SAGA-2601")
    parser.add_argument(
        "--ethics-status",
        choices=("pending", "approved", "exempt", "not-required"),
        default="pending",
    )
    args = parser.parse_args()
    codes = [code.strip() for code in args.reviewer_codes if code.strip()]
    if len(codes) < 2 or len(codes) != len(set(codes)):
        raise SystemExit("At least two unique reviewer codes are required")

    manifest, blind_rows = _verify_collection(args.collection)
    args.output.mkdir(parents=True, exist_ok=True)
    reviewer_root = args.output / "reviewers"
    reviewer_root.mkdir(exist_ok=True)
    packet_hashes: dict[str, dict[str, str]] = {}
    fields = list(blind_rows[0])
    for code in codes:
        folder = reviewer_root / code
        folder.mkdir(exist_ok=False)
        rating_rows = []
        for source in blind_rows:
            row = dict(source)
            row["rater_id"] = code
            for field in (*SCORE_FIELDS, *BINARY_FIELDS, "comments"):
                row[field] = ""
            rating_rows.append(row)
        ratings_path = folder / f"ratings_{code}.csv"
        _write_csv(ratings_path, rating_rows, fields)
        reference_path = folder / "reviewer_case_reference.csv"
        shutil.copy2(args.collection / "reviewer_case_reference.csv", reference_path)
        (folder / "rubric.md").write_text(RUBRIC, encoding="utf-8")
        (folder / "README.md").write_text(
            _instructions(code, args.ethics_status, args.study_id), encoding="utf-8"
        )
        packet_hashes[code] = {
            item.name: _sha256(item) for item in sorted(folder.iterdir()) if item.is_file()
        }

    qualification_fields = [
        "reviewer_code", "professional_role", "relevant_years_experience",
        "qualifications", "hydrogen_safety_experience", "hazop_experience",
        "emergency_response_experience", "prior_system_familiarity",
        "conflict_of_interest", "independence_confirmed_yes_no",
        "ethics_information_provided_yes_no", "rating_completed_utc",
    ]
    qualification_rows = [{field: "" for field in qualification_fields} for _ in codes]
    for row, code in zip(qualification_rows, codes):
        row["reviewer_code"] = code
    _write_csv(
        args.output / "reviewer_qualifications.csv",
        qualification_rows,
        qualification_fields,
    )

    lock = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "study_id": args.study_id,
        "ethics_status": args.ethics_status,
        "collection_manifest_sha256": _sha256(
            args.collection / "collection_manifest.json"
        ),
        "casebook_snapshot_sha256": _sha256(
            args.collection / "casebook_snapshot.json"
        ),
        "allocation_key_sha256": _sha256(args.collection / "allocation_key.csv"),
        "allocation_key_distributed_to_reviewers": False,
        "source_commit": manifest.get("source_commit"),
        "reviewer_codes": codes,
        "response_count_per_reviewer": len(blind_rows),
        "packet_file_sha256": packet_hashes,
        "collection_failed_call_count": manifest.get("failed_call_count", 0),
        "failed_calls_retained_for_scoring": manifest.get(
            "failed_calls_retained_for_blinded_scoring", False
        ),
    }
    (args.output / "coordinator_lock_manifest.json").write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(args.output / "coordinator_lock_manifest.json")
    if args.ethics_status == "pending":
        print("Prepared only: rating collection is blocked until ethics status is resolved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
