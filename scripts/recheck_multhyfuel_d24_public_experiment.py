"""Recheck the public MultHyFuel HRS dispenser consequence experiments.

The public D2.4 deliverable reports measurements from a mock-up high-pressure
hydrogen dispenser.  It is useful external evidence for release, jet-fire and
internal overpressure benchmarking, but it does not contain a vehicle-fuelling
transaction trace and must not be promoted to full-loop or SAGA validation.
Only the digest and normalized evidence fields are retained in the repository;
the PDF itself is downloaded transiently and is not redistributed here.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen


REPORT_URL = (
    "https://multhyfuel.eu/images/event-documents/deliverables/"
    "MultHyFuel%20D2.4%20-%20Fire%20and%20explosion%20hazard%20assessment%20summary%20report%20-%20Final.pdf"
)
REPORT_SHA256 = "30765fd1512a8a6faadaa098d373417efd0519362487f14d29ccd6626b2bee7c"


def _fetch() -> tuple[int, str, bytes]:
    request = Request(REPORT_URL, headers={"User-Agent": "hrs-validation-recheck/1.0"})
    with urlopen(request, timeout=120) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read()


def _extract_pages(payload: bytes) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - environment diagnostic
        raise RuntimeError("pypdf is required to inspect the public PDF") from exc
    reader = PdfReader(io.BytesIO(payload), strict=False)
    return [page.extract_text() or "" for page in reader.pages]


def _normalized(text: str) -> str:
    # PDF extraction inserts line breaks and sometimes non-breaking spaces in
    # table rows; collapsing whitespace keeps the checks stable across readers.
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()


def _contains_any(text: str, *needles: str) -> bool:
    return all(needle.lower() in text.lower() for needle in needles)


def recheck() -> dict[str, object]:
    http_status, content_type, payload = _fetch()
    pages = _extract_pages(payload)
    page_text = [_normalized(page) for page in pages]
    all_text = " ".join(page_text)
    digest = hashlib.sha256(payload).hexdigest()

    # These anchors are deliberately tied to the report's experimental result
    # pages rather than inferred from the digital-twin model.
    executive = page_text[3] if len(page_text) > 3 else ""
    # The experiment description spans the report's printed pages 11-12.
    setup = " ".join(page_text[index] for index in (12, 13) if index < len(page_text))
    jetfire = page_text[14] if len(page_text) > 14 else ""
    internal = page_text[15] if len(page_text) > 15 else ""
    overpressure = page_text[16] if len(page_text) > 16 else ""
    barriers = page_text[19] if len(page_text) > 19 else ""
    scenario_anchor = _contains_any(all_text, "TT1", "TT22", "700 bar", "350 bar")

    reported = {
        "component_leak_range_g_s": [1.0, 30.0],
        "broken_hose_order_of_magnitude_g_s": 100.0,
        "jetfire_700bar_measured_flow_g_s": 40.0,
        "jetfire_300bar_measured_flow_g_s": 20.0,
        "jetfire_700bar_measured_flame_length_m_min": 5.0,
        "jetfire_300bar_measured_flame_length_m": 4.0,
        "jetfire_measured_temperature_c": 1200.0,
        "internal_700bar_0_2mm_flow_g_s": 9.0,
        "internal_700bar_0_2mm_max_h2_percent": 25.0,
        "internal_350bar_0_2mm_flow_g_s": 4.5,
        "internal_350bar_0_2mm_max_h2_percent": 20.0,
        "internal_700bar_0_5mm_flow_g_s": 16.0,
        "internal_700bar_0_5mm_max_h2_percent": 50.0,
        "inside_ignition_overpressure_mbar": {
            "inside": 626.0,
            "1_2m": 134.0,
            "2_4m": 85.0,
            "5m": 20.0,
        },
        "outside_ignition_overpressure_mbar": {
            "inside": 50.0,
            "1_2m": 1.0,
            "2_4m": 7.0,
            "5m": 4.0,
        },
        "external_fire_duration_min": 15.0,
    }
    anchors = {
        "executive_summary_page_2": _contains_any(
            executive, "leakage mass flowrates", "homogeneous flammable", "top venting"
        ),
        "experimental_setup_page_11": (
            "mock-up" in setup.lower()
            and "two 50 l cylinders" in setup.lower()
            and "350 or 700 bar" in setup.lower()
            and "pressure transducers" in setup.lower()
        ),
        "jetfire_results_page_13": _contains_any(
            jetfire, "maximum flowrate at 700 bars", "40 g/s", "5 m long", "1200 °C"
        ),
        "internal_release_results_page_14": _contains_any(
            internal, "TT04", "0.2", "700", "9", "25"
        ),
        "overpressure_results_page_15": _contains_any(
            overpressure, "626", "134", "85", "20", "50", "1", "7", "4"
        ),
        "safety_barrier_timing_page_18": _contains_any(
            barriers, "closing time", "shorter", "residence", "emergency shut down"
        ),
        "scenario_matrix_present": scenario_anchor,
    }
    all_anchors_present = all(anchors.values())

    return {
        "schema_version": 1,
        "rechecked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PUBLIC_MULTHYFUEL_D24_EXPERIMENT_RECHECKED",
        "source": {
            "title": "MultHyFuel D2.4 Fire and explosion hazard assessment summary report",
            "url": REPORT_URL,
            "publisher": "MultHyFuel / Clean Hydrogen Partnership",
            "deliverable": "D2.4",
            "public_report": True,
        },
        "download": {
            "http_status": http_status,
            "content_type": content_type,
            "bytes": len(payload),
            "sha256": digest,
            "expected_sha256": REPORT_SHA256,
            "sha256_matches_expected": digest == REPORT_SHA256,
            "pdf_pages": len(pages),
        },
        "evidence_role": "public_dispenser_consequence_experiment",
        "experimental_setup": {
            "device": "mock-up high-pressure H2 dispenser",
            "reservoir": "two 50 L cylinders at 350/700 bar",
            "instrumentation": [
                "pressure transducers",
                "thermocouples",
                "heat-flux gauges",
                "standard/IR/high-speed cameras",
                "hydrogen concentration measurements",
            ],
            "reported_scenarios": ["TT1-TT3", "TT4-TT13", "TT18", "TT20", "TT22"],
        },
        "reported_measurements": reported,
        "page_anchors": anchors,
        "eligibility_decision": {
            "public_experiment_verified": http_status == 200 and digest == REPORT_SHA256 and all_anchors_present,
            "consequence_benchmark_eligible": all_anchors_present,
            "full_loop_station_vehicle_holdout_eligible": False,
            "saga_effectiveness_eligible": False,
            "allowed_use": [
                "external HRS dispenser release/jet-fire benchmark",
                "internal-cloud overpressure and concentration scenario grounding",
                "independent safety-barrier timing and venting context",
            ],
            "prohibited_use": [
                "station-to-vehicle transaction validation",
                "SAGA effectiveness or operator-outcome validation",
                "post-hoc parameter fitting",
                "site-specific safety-distance certification",
            ],
        },
        "claim_boundary": (
            "The public report provides measured mock-up dispenser release, jet-fire, "
            "internal concentration and overpressure evidence. It supports an external "
            "consequence benchmark, but contains no synchronized real-station/vehicle "
            "transaction trace and cannot close the full-loop or SAGA-effectiveness gates."
        ),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/multhyfuel_d24_public_experiment_recheck_2026_10_05.json"),
    )
    args = parser.parse_args()
    report = recheck()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
