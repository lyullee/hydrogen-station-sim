# Public HRS data search addendum — 2026-10-04

This addendum records a targeted search for a new, independent station-to-
vehicle raw logger archive. The full-loop gate requires a common time base for
vehicle or receptacle pressure, temperature, and mass flow/transferred mass,
plus initial conditions, protocol metadata, units and reuse terms. A paper,
plot, availability feed, aggregate log, or component-only release does not meet
that rule.

## Sources checked

| Source | What is public | Classification |
| --- | --- | --- |
| [Oh et al. KGS HRS study](https://doi.org/10.1007/s11814-025-00551-9) | Six Korean operating-HRS scenarios and pressure/temperature/flow comparisons are reported; the synchronized KGS logger export is not included | High-value data-request lead |
| [HySam measurement data, Zenodo 10.5281/zenodo.20590842](https://zenodo.org/records/20590842) | Three XLSX sampling-system experiments with pressure/temperature conditions | Sampling-system data, not vehicle fueling |
| [Hydrogen dispersion experiment, DOI 10.23642/USN.26117989](https://doi.org/10.23642/USN.26117989) | Release mass flow, filling pressure and 29 hydrogen-concentration channels | Consequence-model candidate, not HRS full loop |
| [H2-Stations API](https://docs.h2-stations.eu/for-data-users/) | Licensed station inventory, availability and selected storage/usage status | Station status data, not synchronized transient logger data |
| [NREL H2IQ high-flow experiment](https://www.energy.gov/sites/default/files/2024-04/h2iqhour-03262024.pdf) | Real high-flow operating-range plots and summary values | Plot/aggregate benchmark; raw trace request required |
| [NLR/NREL HDTADA repository](https://github.com/NREL/HDTADA) | The pinned public repository contains installer binaries and a licence; direct file inspection found no HDTA raw pressure-temperature-IR event files | Software/processing tool only; no independent validation data |
| [NLR public data catalog](https://data.nlr.gov/submissions) | Five public submission pages were inspected for HRS, HDTA, HITRF and vehicle-fueling terms; no matching raw logger submission was listed | Catalog negative search; no new validation data |
| [H2-Stations API v2](https://docs.h2-stations.eu/for-data-users/api-v2/) | Public layout plus availability, usage, hydrogen-storage and pricing signals; protocol details are reserved and not populated | Operations/status context only; no vehicle pressure, temperature and mass-flow time series |
| [ENDA H2 MOBILITY monitoring](https://enda.eu/en/h2_monitoring) | Monitoring deployment reports approximately 75–400 technical parameters per station and short-interval database capture | Controlled operator-monitoring lead; no public machine-readable logger archive or reuse terms |
| [PRHYDE/ZBT D6.7](https://lbst.de/wp-content/uploads/2023/04/PRHYDE_Deliverable-D6-7_Results_as_Input_for_Standardisation_V1-2_final_Apr_2023.pdf) | Public report tables for 35/50/70 MPa ZBT tests and a stated 2 Hz PLC logger | Public report/data-request lead; raw synchronized export and reuse terms still required |
| [KIT H2 release archive, DOI 10.35097/1483](https://doi.org/10.35097/1483) | Public 5 GB experiment metadata lists pressure, mass flow, heat flux, thermocouples, weather and video; CC BY-SA 4.0 | Consequence/detector submodel candidate; not vehicle-fueling full loop |
| [CIP 35/70 MPa fueling study](https://esst.cip.com.cn/article/2020/2095-4239/2095-4239-2020-9-3-702.shtml) | Measured 35/70 MPa fueling pressure, temperature and flow curves; linked T3/T4 CSV ZIPs are summary-table exports, not synchronized logger rows | Real experiment aggregate/table-only; raw trace request required |
| [ZBT/MetHyTrucks sampling intercomparison](https://doi.org/10.3390/cleantechnol8030091) | Real test-HRS experiments report logged dispenser/tank channels. The supplementary file contains sampling-condition/contaminant tables; the article states raw data are available from authors on request | Strong station-to-receptacle data-request lead; not public synchronized raw data |

## Decision

No new eligible public raw full-loop set was found. The CIP article was checked
directly: its T3/T4 “CSV” downloads contain only table rows, while the
pressure/temperature/flow time histories remain figures. The ZBT/MetHyTrucks
article states that raw logged dispenser/tank data are available on request, but
no public machine-readable archive or reuse terms were found. Existing H2Protocol and
NREL files remain governed by their already-frozen roles; they cannot be
reused as a new untouched holdout. The independent full-loop validation gate
therefore remains open. Any future file must be quarantined and hashed with
`scripts/intake_external_hrs_bundle.py` before numerical values are opened.
## 2026-10-04 discovery refresh

The official public inventories found in a second repository search were also
checked against the same intake rule:

| Source | Observed fields | Decision |
| --- | --- | --- |
| [European Hydrogen Observatory HRS workbook](https://observatory.clean-hydrogen.europa.eu/hydrogen-landscape/distribution-and-storage/hydrogen-refuelling-stations) | Station location and dispenser type; no vehicle pressure, gas temperature or mass-flow logger | Static infrastructure context only |
| [California MDHD infrastructure dataset](https://lab.data.ca.gov/dataset/medium-and-heavy-duty-infrastructure) | Station coordinates, dispenser/nozzle counts and funding fields under CC BY | Static infrastructure context only |
| [H2-Stations API v2 documentation](https://docs.h2-stations.eu/for-data-users/) | Static layout plus availability, usage, hydrogen-storage and pricing signals | Operations context only; no synchronized transient fill trace |
| [NREL H2FillS user manual](https://www.nrel.gov/docs/libraries/hydrogen/h2fills-user-manual.pdf?sfvrsn=b2960c3d_1) | Simulator result channels and example output schema | Software documentation, not independent measured station data |

## 2026-10-04 primary-source refresh: public context and data-access limits

Two additional primary sources were checked because they are frequently cited as
if they were downloadable full-loop validation sets:

| Source | What is actually public | Decision |
| --- | --- | --- |
| [Genovese et al., *Hydrogen station in situ back-to-back fueling data for design and modeling*, DOI 10.1016/j.jclepro.2021.129737](https://doi.org/10.1016/j.jclepro.2021.129737) and its [OSTI accepted manuscript](https://www.osti.gov/servlets/purl/1977265) | Cal State LA HRFF operator logs are described as one-second station/vehicle records with pressure, temperature, flow, valve and compressor/chiller states; the public record exposes the manuscript and figures, not a CSV/XLSX/SQL export or reuse terms | High-value real-station data-request lead; not a scorable holdout |
| [Kurtz, *Hydrogen Station Reliability Status and Advances* dissertation](https://api.mountainscholar.org/server/api/core/bitstreams/474f5f0b-4d5d-417a-a2c8-71633293835d/content) and [NREL/NFCTEC report](https://www.osti.gov/servlets/purl/1603259) | NREL reports large real-world samples (fill date/amount/rate/start/end pressure and maintenance events) and explains that detailed raw data are secured; the public releases provide tables, aggregate CDPs and examples, not an untouched synchronized p/T/flow logger archive | Field face-validity and reliability context; not full-loop transient validation |
| [CSIC supplementary material for on-site HRS modelling](https://digital.csic.es/bitstream/10261/334805/1/1-s2.0-S0360319923042167-mmc1.pdf) ([README](https://digital.csic.es/bitstream/10261/334805/2/README%20.txt)) | Public CC BY-NC-ND supplementary PDF/README with operational-logic diagrams and simulated one-day/one-year traces; no measured station-to-vehicle logger | Simulation/protocol reproducibility context only |
| [DTU Hydrogen-Fuelling-Station library](https://github.com/DTU-TES/Hydrogen-Fuelling-Station) | Public Modelica library and `.mat` coefficient tables; the associated thesis describes a confidential 2011 H2Logic test and compares it with the model, but the repository contains no raw fill trace | Open model/protocol context; not raw-data validation |

The refresh confirms a recurring limitation: high-quality papers often describe
real station logs, while public artifacts stop at aggregate tables, plots,
software or secured operator data. The Cal State LA and NREL sources are still
the best acquisition routes, but they cannot be promoted to the untouched
full-loop gate until a custodian supplies de-identified synchronized files,
channel definitions, calibration/quality flags and written reuse terms.

The [NREL HITRF description](https://www.nrel.gov/hydrogen/hitrf-animation?print=)
also confirms that automated logging exists for the integrated station, while
the public [holistic validation report](https://www.nrel.gov/docs/fy21osti/79223.pdf)
states that a public holistic station-to-vehicle dataset was not available and
that HITRF hardware data were used instead. This supports a data-request route,
not a claim that the public report itself is a validation dataset.

These sources are useful for station topology, equipment mix and operating
context, but none meets the required station-to-vehicle pressure/temperature/
mass-flow time-series rule. They therefore do not change the independent
full-loop gate or justify a publication claim of validated station control.

## 2026-10-04 file-level access refresh: CARB and 3Emotion

Two high-value real-world sources were checked again at the file level because
both are sometimes described as if their underlying logger files were openly
downloadable:

| Source | File-level finding | Decision |
| --- | --- | --- |
| [CARB 2024 Existing Light-Duty Hydrogen Refueling Stations In-Use Study](https://ww2.arb.ca.gov/sites/default/files/2024-12/Existing%20Light-Duty%20Hydrogen%20Refueling%20Stations%20In-Use%20Study%20Report%20ADA%20AL.pdf) | Appendix A says the 22-station study results were tabulated in an Excel workbook. The report PDF is public, but the workbook was not linked from the report or the CARB hydrogen-infrastructure page during the recheck. | Public real-station test report and workbook-request lead; no untouched holdout |
| [3Emotion four-year operational analysis](https://doi.org/10.1051/e3sconf/202233406008) and [project Description of Work](https://3emotion.eu/sites/default/files/documents/3EMOTION_DOW.pdf) | The paper describes operator logbooks and aggregate fill amount/duration/flow results. The project document assigns predefined Excel sheets to operators, but no operator workbook or synchronized pressure/temperature/mass-flow archive is public. | Public real-station aggregate context and data-request lead; no untouched holdout |
| [BAM/KETI demonstration-station monitoring study](https://doi.org/10.3390/app16157856) | The article confirms continuous pressure, temperature and flow-rate monitoring at a real BAM demonstration HRS and reports that original contributions are available in the article or from the corresponding author; no public synchronized logger archive or reuse terms are provided. | Public real-station method/provenance and data-request lead; no untouched holdout |
| [Zenodo chillerless tank-validation deposit](https://doi.org/10.5281/zenodo.20183753) | The archive contains reproducible code and nine literature-digitized temperature fills, but each case is marked as manually digitized from figures with no raw file; no station-to-vehicle logger is included. | Derived tank-temperature context only; not a new holdout |

The machine-readable inspection record, including source hashes and the exact
eligibility boundary, is in
[`research/public_data_access_refresh_2026_10_04.json`](public_data_access_refresh_2026_10_04.json).
Neither source changes the independent full-loop gate. If a custodian releases
the CARB workbook or 3Emotion event logs, the files must be quarantined,
hash-locked and scored under the frozen protocol before any outcome is read.
The same rule applies to the BAM/KETI station export; its article-level data
availability statement is not a licence for raw-data redistribution.
The Zenodo tank deposit was also quarantined and inspected by archive hash; its
embedded digitizations remain derivative context and are not counted as a new
independent measured dataset.


## 2026-10-04 Cal State LA experiment and SunHydro/HSDC follow-up

Two additional real-world routes were registered after a source-level review:

| Source | Evidence and limitation | Acquisition route |
| --- | --- | --- |
| [Cal State LA HRFF cascade/directly-pressurized experiments](https://doi.org/10.3390/en16155749) | Three real heavy-duty refuelling experiments are reported, including cascade/direct pressure endpoints and chiller/nozzle comparisons. The public article provides summaries and figures, not synchronized logger files or reuse terms. | [`research/CALSTATE_CASCADE_EXPERIMENT_DATA_REQUEST_DRAFT.md`](CALSTATE_CASCADE_EXPERIMENT_DATA_REQUEST_DRAFT.md) |
| [DOE SunHydro final report](https://www.osti.gov/servlets/purl/1783792), [2015 AMR report](https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/review15/tv020_moulthrop_2015_o.pdf) and [NREL HSDC overview](https://www.nrel.gov/docs/fy12osti/54860.pdf) | Real SunHydro station operating data were collected and exported to HSDC, but detailed partner records are controlled and public products are aggregate. No synchronized station-to-vehicle raw archive is public. | [`research/SUNHYDRO_DATA_REQUEST_DRAFT.md`](SUNHYDRO_DATA_REQUEST_DRAFT.md) |

Both routes are real-data acquisition leads. They do not close the independent full-loop gate until de-identified synchronized files, hashes, written reuse terms and the frozen no-fitting scoring protocol are available.

## 2026-10-04 BAM research-station route

The official [BAM H2Safety@BAM station description](https://www.bam.de/Content/EN/Standard-Articles/Topics/Energy/Hydrogen/hydrogen-h2-filling-stations.html)
confirms a real, digitally networked research refuelling station containing an
electrolyser, compressor, buffer storage, gas cooler and dispenser. BAM states
that operating data, measurement uncertainties, sensor histories and procedures
are collected for digital-twin and safety research. The public page does not
provide a synchronized station-to-vehicle logger archive or reuse terms, so the
route is recorded as a controlled-data request lead only. The prepared request
is [`research/BAM_HRS_DATA_REQUEST_DRAFT.md`](BAM_HRS_DATA_REQUEST_DRAFT.md).
