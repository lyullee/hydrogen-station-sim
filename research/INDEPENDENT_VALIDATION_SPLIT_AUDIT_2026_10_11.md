# Independent validation split audit (2026-10-11)

The available public cases are now partitioned explicitly so that the paper can distinguish a same-source holdout from a genuinely independent station-to-vehicle external validation. This audit does **not** turn a retrospective or same-campaign split into a stronger claim.

## Available split

- Powertech Tables-method index: `data/public_validation/processed/h2protocol_cases.csv` (SHA-256 `f6bcc9a29da4e86f8376f14832192666002d7a9fb046ff00a3eb05d364c3e3ec`).
- 36 total cases.
- Calibration partition: test number modulo 3 ≠ 0, 24 cases.
- Deterministic within-source holdout: test number modulo 3 = 0, 12 cases.
- The split is reproducible and the case list is frozen in the companion JSON.

The 36 cases are from one public campaign and the comparison set was inspected during controller iteration. Therefore this partition is labelled **within-source public holdout**, not independent external station-to-vehicle validation. It is still useful for model debugging and source-generalisation reporting.

## Stronger external set already available

The separately frozen SAE J2601 MC Default archive is a different protocol family with 8 cases. It was evaluated after the model freeze without parameter retuning: 0/8 cases passed the joint engineering screen. It remains a valid negative external holdout and must be reported as such; it does not validate station-side bank dispatch or field safety.

## Goal boundary

No reuse-cleared, synchronized station-to-vehicle raw bundle is currently available. The primary goal and paper will therefore exclude that claim and state the limitation directly. A future new archive would need to be held out before outcome access, with synchronized station/vehicle clocks, pressure, temperature, mass-flow, SOC, protocol/valve state, calibration and reuse terms.
