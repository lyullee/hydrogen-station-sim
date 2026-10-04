"""Recheck the KGS/Oh real-HRS paper's public appendix and code boundary.

The article reports six real refuelling scenarios, but a publication claim is
not a machine-readable raw-data release.  This script records what an
anonymous reader can actually retrieve: the two-page parameter appendix and
the linked Google Drive sign-in redirect.  It deliberately does not treat
figure values or model constants as a full-loop holdout.
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
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pypdf import PdfReader


PREPRINT_URL = "https://www.researchsquare.com/article/rs-6248350/v1"
APPENDIX_URL = (
    "https://assets-eu.researchsquare.com/files/rs-6248350/v1/"
    "6179b5ddc5929c6c28b2e5d4.pdf"
)
CODE_URL = "https://drive.google.com/drive/folders/1l_rKzlKZaxSVIyFwNkbVX0r2JLnRtosp"
EXPECTED_APPENDIX_SHA256 = "f70ec03b33da8caf1d7b9ee8b082e661a6e57b4115b6ffa3fe5d57364dbbd628"


def _get(url: str) -> tuple[int, str, str, bytes]:
    request = Request(url, headers={"User-Agent": "hrs-validation-recheck/1.0"})
    with urlopen(request, timeout=60) as response:
        return response.status, response.headers.get("Content-Type", ""), response.url, response.read()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def recheck() -> dict[str, object]:
    html_status, html_type, html_final_url, html_body = _get(PREPRINT_URL)
    html_text = html_body.decode("utf-8", errors="replace")
    discovered = re.findall(r"https://assets-eu\.researchsquare\.com/[^\"']+\.pdf", html_text)
    appendix_url = next((url for url in discovered if "6179b5ddc5929c6c28b2e5d4" in url), APPENDIX_URL)

    appendix_status, appendix_type, appendix_final_url, appendix_body = _get(appendix_url)
    reader = PdfReader(io.BytesIO(appendix_body))
    appendix_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    required_terms = ["Table A.1", "Table A.2", "Table A.3", "Base simulation conditions"]

    code_status, code_type, code_final_url, code_body = _get(CODE_URL)
    code_host = urlparse(code_final_url).netloc.lower()

    return {
        "schema_version": 1,
        "rechecked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PUBLIC_APPENDIX_PARAMETER_TABLE_ONLY_CODE_SIGN_IN_REDIRECT",
        "source": {
            "title": "Enhanced Thermofluidic Modeling and Open Source Rigorous Simulation of Hydrogen Fueling Systems Validated with Real-world Data",
            "published_doi": "10.1007/s11814-025-00551-9",
            "preprint_doi": "10.21203/rs.3.rs-6248350/v1",
            "preprint_url": PREPRINT_URL,
            "reported_real_hrs_scenarios": 6,
            "reported_measurements": ["vehicle pressure", "vehicle temperature", "mass flow"],
            "claimed_code_url": CODE_URL,
        },
        "appendix_access": {
            "article_http_status": html_status,
            "article_content_type": html_type,
            "article_final_url": html_final_url,
            "article_sha256": _sha256(html_body),
            "appendix_url": appendix_url,
            "appendix_http_status": appendix_status,
            "appendix_content_type": appendix_type,
            "appendix_final_url": appendix_final_url,
            "appendix_bytes": len(appendix_body),
            "appendix_sha256": _sha256(appendix_body),
            "appendix_sha256_expected": EXPECTED_APPENDIX_SHA256,
            "appendix_sha256_matches_expected": _sha256(appendix_body) == EXPECTED_APPENDIX_SHA256,
            "pdf_pages": len(reader.pages),
            "required_table_terms_present": {term: term in appendix_text for term in required_terms},
            "raw_synchronized_logger_present": False,
            "interpretation": "The public supplement is a two-page appendix of constants and base simulation conditions; it contains no synchronized station/vehicle logger rows.",
        },
        "code_access": {
            "url": CODE_URL,
            "http_status": code_status,
            "content_type": code_type,
            "final_url": code_final_url,
            "final_url_host": code_host,
            "response_bytes": len(code_body),
            "result": "REDIRECTED_TO_SIGN_IN" if code_host == "accounts.google.com" else "ANONYMOUS_RESPONSE_REQUIRES_REVIEW",
            "files_retrieved": 0,
        },
        "classification": {
            "parameter_appendix_public": True,
            "public_raw_logger_available": False,
            "full_loop_station_vehicle_holdout_eligible": False,
            "goal_completion_permitted": False,
        },
        "claim_boundary": "The paper establishes a high-value real-station acquisition lead. The appendix and anonymous code check do not provide a downloadable synchronized raw archive, so no full-loop validation score or IJHE readiness/completion claim is made.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("research/kgs_oh_preprint_appendix_recheck_2026_10_05.json"))
    args = parser.parse_args()
    report = recheck()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
