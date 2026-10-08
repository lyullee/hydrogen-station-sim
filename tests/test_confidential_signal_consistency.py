from __future__ import annotations

import json
from pathlib import Path

from h2station.confidential_signal_consistency import audit_confidential_signal_consistency


def test_consistency_screen_finds_totalizer_flow_pair_without_disclosing_headers(tmp_path: Path):
    source = tmp_path / "private-source-name"
    source.mkdir()
    path = source / "secret-station-and-date.csv"
    rows = ["Timestamp,PT-secret,MFM_Rate-secret,MFM_Acc-secret"]
    accumulated = 0.0
    for index in range(180):
        flow = 0.2 + 0.12 * ((index % 30) / 29.0)
        accumulated += flow
        rows.append(f"{index},{40.0 + index * 0.01},{flow},{accumulated}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    result = audit_confidential_signal_consistency(source)
    encoded = json.dumps(result)

    assert result["screen"]["strong_consistency_pairs"] == 1
    assert result["eligibility"]["flow_channel_pair_attestation_candidate"] is True
    assert result["eligibility"]["absolute_mass_flow_supported"] is False
    assert result["eligibility"]["conditional_bank_inventory_estimation_supported"] is False
    assert "secret" not in encoded
    assert "private-source-name" not in encoded
    assert result["privacy"]["raw_rows_persisted"] is False


def test_consistency_screen_rejects_unrelated_flow_and_totalizer(tmp_path: Path):
    source = tmp_path / "controlled"
    source.mkdir()
    path = source / "trace.csv"
    rows = ["time,pressure,flow,total_mass"]
    accumulated = 0.0
    for index in range(180):
        unrelated = float((index * 17) % 31)
        accumulated += 0.1 + (index % 9) * 0.03
        rows.append(f"{index},{40 + index / 100},{unrelated},{accumulated}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    result = audit_confidential_signal_consistency(source)

    assert result["screen"]["strong_consistency_pairs"] == 0
    assert result["eligibility"]["flow_channel_pair_attestation_candidate"] is False


def test_constant_channels_do_not_become_physical_evidence(tmp_path: Path):
    source = tmp_path / "controlled"
    source.mkdir()
    (source / "trace.csv").write_text(
        "time,pressure,flow,total\n" + "\n".join(
            f"{index},40,0,0" for index in range(100)
        ),
        encoding="utf-8",
    )

    result = audit_confidential_signal_consistency(source)

    assert result["screen"]["variable_pressure_channels"] == 0
    assert result["screen"]["variable_flow_like_channels"] == 0
    assert result["screen"]["candidate_pairs_evaluated"] == 0
