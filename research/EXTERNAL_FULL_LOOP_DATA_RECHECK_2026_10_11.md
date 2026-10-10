# External full-loop data recheck — 2026-10-11

This recheck records newly located independent hydrogen-refuelling experiments without treating a paper, plot, or data-on-request statement as an eligible raw holdout.

## Finding

No new public machine-readable station-to-sink trace was identified. The full-loop external validation gate therefore remains **FAIL**. The recheck produces three concrete data-request leads:

- FCH2RAIL: real dispenser and train-tank measurements are described, but the public paper exposes no common-time-base export.
- ZBT/NPL sampling campaign: dispenser and sink data were logged at a real HRS, but the article states that raw data are available from the authors on request.
- NREL H2IQ heavy-duty fast-flow briefing: useful pressure, hose, receptacle and flow context is shown, but no raw trace is published.

## Eligibility boundary

An accepted holdout still requires an independent physical fueling event, a synchronized vehicle or receptacle pressure channel, mass flow or transferred mass, units and initial conditions, protocol metadata, and reuse terms that permit publication of derived results. Plot-only or request-only material remains a request lead.

The machine-readable record is [external_full_loop_data_recheck_2026_10_11.json](external_full_loop_data_recheck_2026_10_11.json).
