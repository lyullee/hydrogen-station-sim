"""Recheck the public metadata boundary of the Mendeley HRS dataset.

The DOI is useful provenance for simulation benchmarking, but its public
abstract explicitly describes generated HRS performance-model outputs.  This
script records that classification so the dataset cannot silently become an
independent station/vehicle validation holdout.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen


DOI = "10.17632/mnjs94yzfc.1"
API_URL = f"https://api.datacite.org/dois/{DOI}"
LANDING_URL = "https://data.mendeley.com/datasets/mnjs94yzfc/1"


def _fetch() -> dict[str, object]:
    request = Request(API_URL, headers={"User-Agent": "hrs-validation-recheck/1.0"})
    with urlopen(request, timeout=60) as response:
        payload = response.read()
    return json.loads(payload.decode("utf-8"))


def recheck() -> dict[str, object]:
    raw = _fetch()
    attributes = ((raw.get("data") or {}).get("attributes") or {})
    descriptions = attributes.get("descriptions") or []
    abstract = next(
        (item.get("description", "") for item in descriptions if item.get("descriptionType") == "Abstract"),
        "",
    )
    rights = [item.get("rights", "") for item in (attributes.get("rightsList") or [])]
    cc_by_4_present = any(
        "cc by 4.0" in value.lower()
        or "creative commons attribution 4.0" in value.lower()
        for value in rights
    )
    abstract_lower = abstract.lower()
    simulation_only = "simulation" in abstract_lower and "time-resolved simulation outputs" in abstract_lower
    no_experimental_claim = "experimental" not in abstract_lower or "not experimental" in abstract_lower
    return {
        "schema_version": 1,
        "rechecked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PUBLIC_MENDELEY_HRS_METADATA_RECHECKED",
        "source": {
            "doi": DOI,
            "title": attributes.get("titles", [{}])[0].get("title"),
            "url": LANDING_URL,
            "api_url": API_URL,
            "publisher": attributes.get("publisher"),
            "publication_year": attributes.get("publicationYear"),
            "creators": [
                item.get("name") or item.get("familyName")
                for item in (attributes.get("creators") or [])
            ],
            "rights": rights,
        },
        "metadata_integrity": {
            "http_status": 200,
            "abstract_sha256": hashlib.sha256(abstract.encode("utf-8")).hexdigest(),
            "abstract_present": bool(abstract),
            "simulation_language_present": simulation_only,
            "cc_by_4_present": cc_by_4_present,
        },
        "dataset_characterization": {
            "simulation_only": simulation_only,
            "time_resolved_simulation_outputs": "time-resolved simulation outputs" in abstract_lower,
            "experimental_logger_archive": False,
            "real_station_full_loop": False,
            "public_metadata_only_rechecked": True,
        },
        "eligibility_decision": {
            "public_metadata_verified": bool(abstract) and cc_by_4_present,
            "full_loop_external_holdout_eligible": False,
            "allowed_use": [
                "simulation benchmark provenance",
                "model-comparison context",
                "reproducibility and scenario-design reference",
            ],
            "prohibited_use": [
                "independent physical validation",
                "station-to-vehicle full-loop score",
                "post-hoc parameter fitting",
            ],
        },
        "claim_boundary": (
            "The DOI metadata verifies an openly licensed HRS simulation dataset. "
            "It does not provide synchronized real-station logger data and remains "
            "ineligible for independent full-loop validation."
        ),
        "recheck_assertions": {
            "simulation_only": simulation_only,
            "no_experimental_claim_in_abstract": no_experimental_claim,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path,
        default=Path("research/hrs_mendeley_simulation_dataset_boundary_2026_10_05.json"),
    )
    args = parser.parse_args()
    report = recheck()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
