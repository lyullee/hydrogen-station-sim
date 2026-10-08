# Local candidate full-loop screen (2026-10-09)

The local search confirmed that the station data collection is large. Its main limitation is semantic coverage, not row count: the screened private bundle supports station-side pressure, temperature, flow-like, compressor and valve/ESD chronology, but it does not provide an attested vehicle or receiving-vessel boundary in the published-safe export.

Two staged public candidates were checked separately:

* **NREL H2FillS HDVS Type-IV workbook** — 351 one-second samples for seven tanks with hose and per-tank pressure, temperature and mass. It is a measured tank/hose boundary and remains useful for a component screen. It has no station controller, cascade, ESD, receptacle or vehicle protocol trace, and the frozen pressure screen failed. The raw workbook is not redistributed here; reuse rights must be checked with the custodian.
* **DTU-TES Hydrogen Fuelling Station v2.1** — a 45-member GPL-3.0 Modelica package with coefficient tables and graphics. It is a simulator/protocol reference, not a measured logger archive, so its outputs cannot be counted as independent experimental validation.

The machine-readable classification is in `research/local_candidate_full_loop_screen_2026_10_09.json`. No raw confidential rows, site identifiers, exact dates or private source paths are included.

## Decision boundary

The local evidence is sufficient for station-side calibration and chronological holdouts. It is not sufficient for a station-to-vehicle full-loop holdout, accident-frequency estimate, or site-specific consequence claim. A custodian-approved, de-identified export with a common clock, receiving-vessel/vehicle pressure and temperature, delivered mass or attested mass flow, and controller/protocol state remains the required next input.
