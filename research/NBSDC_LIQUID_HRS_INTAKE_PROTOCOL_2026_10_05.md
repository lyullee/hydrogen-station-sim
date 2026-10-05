# NBSDC liquid-HRS intake protocol (2026-10-05)

This is a prospective, no-fitting intake contract for the publicly listed
**Operating Dataset of Liquid Hydrogen Refueling Station** from Tongji
University (`CSTR:16666.11.nbsdc.nlMxRHct`, data id
`67d50e37195d260905af9869`). The current portal metadata reports `完全共享`
and exposes seven original XLSX/CSV/DOCX files. The model outcome must remain
unopened until this contract and its file-role manifest are committed.

## Required full-loop evidence

An event is eligible only when one clock can align vehicle/receptacle pressure
and temperature, transferred mass or mass flow, station/source/dispenser
channels, initial conditions, protocol/stop semantics, and quality/calibration
metadata. Station-only, compressor-only, liquid-pump, storage-only, or
description-only rows are retained as component evidence and do not close the
station-to-vehicle gate.

The frozen engineering screens are pressure RMSE ≤ 5 MPa, temperature RMSE ≤
10 °C, and transferred-mass relative error ≤ 10%. Every eligible event is
scored once with the locked model. No case selection, parameter fitting, time
warping, threshold change, or post-outcome tuning is permitted.

## Quarantine sequence

1. Commit this JSON protocol before reading numerical cells.
2. Download the seven original files to the ignored raw-data directory.
3. Record source IDs, byte sizes, and SHA-256 before parsing.
4. Inspect the description and headers for units, clocks, missing values and
   channel semantics.
5. Freeze event mapping and run the model once on untouched eligible fills.
6. Retain every ineligible or failed case and publish only permitted derived
   metrics and de-identified traces.

The protocol does not assume that a public file listing contains vehicle-side
telemetry or a fueling protocol. If those channels are absent, the result is a
documented component-data boundary rather than a full-loop validation claim.

Machine-readable contract: `research/nbsdc_liquid_hrs_intake_protocol_2026_10_05.json`.
