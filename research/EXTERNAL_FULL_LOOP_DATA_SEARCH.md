# Search for an untouched external full-loop validation set

Search frozen: **2026-10-03**

## Eligibility rule

A dataset can close the full-loop validation gate only when it is independent
of the Powertech Tables Method and MC Default files already used, represents a
physical hydrogen refuelling experiment or an in-use station fill, and exposes
a common time base with at least vehicle/receptacle pressure plus either mass
flow or transferred mass. Tank or fuel temperature is strongly preferred.
Initial conditions, tank capacity and protocol/ramp information must be
sufficient to run the model without fitting to the evaluation outcome.

Plots without underlying numbers, station-availability records, aggregate
histograms and simulator output are useful context but are not accepted as an
untouched experimental time-series validation set. A source that requires a
data request remains unavailable until the files, licence/permission and an
immutable digest are recorded.

## Screening result

| Candidate | Evidence found | Decision |
|---|---|---|
| CARB 2024 Existing Light-Duty HRS In-Use Study | Tests at 22 in-use stations; report figures include pressure, temperature, mass flow and SOC. Appendix A says results were tabulated in an Excel workbook. The public page links only the PDF; the PDF has no attachments or data links. | **Request data.** Strongest independent field candidate, but the published plot and summary table are not machine-readable validation data. |
| CARB/NREL HyStEP 2015–2017 dispenser test program | CEC report documents 11 California stations, three instrumented Type IV 70 MPa test tanks, pressure/temperature and dispenser communication/fueling measurements, plus CSA HGV 4.3 / SAE J2601 protocol and fault tests. The report explicitly says station test data and results are confidential and are not included. | **Request data.** Ask CARB/NREL for de-identified test matrices, data dictionary, calibration/quality flags and reuse terms; the report itself cannot close the untouched time-series gate. |
| Zhao et al. 35/70 MPa dispenser performance tests, DOI 10.19799/j.cnki.2095-4239.2020.0049 | A real-station study reports 35 MPa and 70 MPa vehicle fills and exposes four downloadable CSV links for initial/final tables. The files contain only summary values; the article reports that pressure/temperature/flow curves were recorded but no common-time-base trace is downloadable. | **Summary benchmark / request raw trace.** Use reported 35 MPa (8.21 kg, 470 s) and 70 MPa (5.08 kg, 276 s, 36 g/s peak) endpoints only for face-validity; request the original synchronized logger export before treating it as an untouched holdout. |
| H2Protocol.com SAE J2601 Tables and MC Default public archives | The H2Protocol data-sharing site currently exposes five SAE J2601 Tables ZIP archives and one MC Default ZIP archive. The local acquisition manifest records six archive SHA-256 values and the processed traces contain vehicle pressure, tank temperature, SOC, inlet-gas temperature and mass-flow channels on a common clock. | **Consumed source, not an independent holdout.** These Powertech archives are already used by the frozen development/MC evaluation; reusing them for a new prospective claim would violate independence. Preserve the hashes and obtain a separate CARB/HyStEP, NIST, CEC or GasTeF logger archive before reopening the gate. |
| NREL H2FillS | The official package includes `SupplementalData/20220816_hdvs_typeIV_test_result.xlsx`: a 351-sample, 1 s, seven-tank Type-IV HDVS test with per-tank inlet pressure/temperature, mass, internal pressure and internal temperature (61.5 kg reported transfer, 1.8→75.8 MPa). | **Independent tank-submodel candidate, not full loop.** The frozen tank model was run once without fitting on this workbook: 0/7 joint screens, mean pressure RMSE 6.164 MPa, temperature RMSE 4.625 °C and final mass error 0.120 kg. The raw package is retained locally because its internal-use-only licence does not permit redistribution; request permission before publishing derived values. Reproduction: `scripts/run_nrel_h2fills_hdvs_validation.py`. |
| NREL 2024 HITRF reliability/fueling report | Table 4 gives sample HITRF fill summaries with timestamp, amount, rate, start/end pressure, dispensing temperature and dispensing pressure. | **Report table only.** The PDF does not provide a common-time-base raw trace, so it is useful field context and a lead for a data request, not an untouched full-loop validation set. |
| DOE/NREL H2IQ Hour 2024 HD fast-flow experiment | 3/12/2024 HITRF test reports 73 kg in 423.5 s, 358.9 s fueling time, 172.3 g/s average, 483.33 g/s peak, 5.5→74.6 MPa, APRR 9.9 MPa/min under SAE J2601-5 MCF-HF-G H70 FM300 T40. | **Plot/summary only.** The presentation contains charts and aggregate endpoints but no machine-readable common-time-base trace; use for face-validity and operating-range checks only. |
| NREL HDVS August/October 2022 campaign summaries | DOE/NREL performance reporting gives 61.5 kg in 4.7 min (13.2 kg/min average, 18.7 kg/min peak) for the August Type-IV-only campaign and 82.3 kg in 6.6 min (12.6 kg/min average, 23 kg/min peak) for the October complete-HDVS campaign. | **Aggregate context only.** These independent heavy-duty endpoints are useful for operating-range checks and a raw-trace request, but the public report has no synchronized station/vehicle time series. |
| NREL HITRF 36 L experiment, Kuroki et al., DOI 10.1002/ente.202300239 | Open article describes a HITRF fill from 6.3 to 73.0 MPa in 186 s with inlet pressure, receptacle-exit temperature, internal hydrogen temperature and liner measurements. | **Request data.** The paper's data-availability statement says research data are not shared; figures and boundary conditions alone cannot close the time-series gate. |
| NREL/NatLabRockies HDTADA | Public repository contains the analysis-tool installers and licence. | **Not available.** No sample raw fueling traces are distributed in the repository. |
| NREL retail-station composite data products | Public aggregate statistics and histograms for station operation. | **Context only.** No fill-level pressure/temperature/flow time series. |
| Ramea et al. hourly station-capacity dataset, DOI 10.1016/j.ijhydene.2019.05.053 | The IJHE article states that a three-month hourly California station-capacity dataset was released to the research community, but the current repository/web search did not locate a working downloadable archive. | **Request/locate data.** It would support demand and availability context, not thermodynamic full-loop validation because it has no synchronized vehicle pressure, temperature and mass-flow channels. |
| NIST Transient Flow Facility | Official page documents 100 ms or faster pressure, temperature and transient-flow measurement capability. | **Request data.** No public experiment archive was identified from the project page. |
| NIST Hydrogen Field Test Standard, Pope & Wright, DOI 10.1016/j.flowmeasinst.2015.10.010 | NIST field tests used a 35 MPa Type III, 1 kg H₂ standard at a retail dispenser; three 0.41 kg and four 0.75 kg H₂ drafts were measured with continuous tank pressure/temperature and independent mass methods. | **Request raw traces.** The open article reports protocols, endpoints and uncertainty but no downloadable synchronized logger files; dispenser readout was disabled, so it is a metrology/partial-dispenser candidate rather than an available full-loop holdout. |
| Cal State LA back-to-back fueling study, DOI 10.1016/j.jclepro.2021.129737 | Peer-reviewed analysis of one year of station operation and back-to-back fills. | **Request data.** No public supplementary raw time-series archive was indexed with the article. |
| Cal State LA HRFF multi-year energy-performance study, DOI 10.1016/j.ijhydene.2023.04.084 | Open-access paper reports 2016–2020 operation, more than 4,500 fills, more than 8,800 kg dispensed, storage/compressor/dispensing-line performance and station data-acquisition methodology. | **Paper aggregate only.** The article does not expose a downloadable synchronized fill trace; request de-identified event-level and time-series exports from the HRFF authors. |
| JRC GasTeF reference database, DOI 10.1016/j.ijhydene.2014.03.227 | Open-access paper describes more than 133 real tank filling/emptying entries with internal and external temperature measurements plus gas-path pressure/temperature instrumentation. | **Request data.** The public JRC record and article do not link a machine-readable database or state reuse terms for the underlying traces. |
| Striednig Type-I tank filling data embedded in HydDown, DOI 10.1016/j.ijhydene.2014.03.028 | MIT-licensed HydDown commit `1040d758b819533451086baa5cf2a47b4292a22f` contains 5, 10 and 30 MPa/min time/gas-temperature measurement arrays and model boundary fields. | **Tank thermal submodel only.** No measured pressure or mass-flow array is embedded, and original measurement redistribution rights are unresolved. It cannot close the station-to-vehicle full-loop gate. |
| PRHYDE D6.7 heavy-duty fueling campaign | Public deliverable documents real ZBT and Nikola tests on 240 L H70, 350 L H50, 322 L H35 and 165 L H70 tanks, including pressure/temperature/flow plots and test matrices. | **Report/plot summary only.** No machine-readable synchronized trace archive was identified; request raw files and reuse terms before considering a holdout. |
| Tessema et al. HRS performance dataset, DOI 10.17632/mnjs94yzfc.1 | CC BY 4.0 record with time-resolved HRS variables. Its DataCite description explicitly classifies the contents as modelling and simulation results plus input parameters. | **Simulator output only.** It is useful for model comparison but cannot independently validate a physical station. |
| H2-Stations.eu Export API | Open station metadata and live/historical availability information; newer API describes usage and storage signals. | **Operations evidence only.** It does not expose the vehicle-fill thermodynamic traces needed for this gate, and live access requires a token. |
| PRESLHY E3.1 high-pressure discharge, DOI 10.35097/1187 | CC BY 4.0 experimental blowdown/discharge files. | **Eligible for a separate blowdown/vent submodel**, not for the station-to-vehicle closed loop. |
| USN open-channel dispersion, DOI 10.23642/USN.26117989 | CC BY 4.0 concentration, pressure and temporal mass-flow measurements. | **Already used for consequence validation**, not for vehicle fueling. |
| Empa Type-IV tank-filling experiments, Couteau et al., DOI 10.1016/j.ijhydene.2022.05.127 | Open-access paper describes four HRS tank-filling experiments with measured temperature evolution and inlet conditions. | **Request data / tank-thermal candidate.** No machine-readable raw trace or supplementary file was identified in the public repository record. |
| Klopčič et al. heavy-duty hydrogen refuelling and pre-cooling experiments, DOI 10.1016/j.ijhydene.2024.03.097 | Open-access IJHE paper reports three 350 L Type IV tank-dummy fills at a refuelling station and validates tank and aluminium-block heat-exchanger models. The public record exposes the paper/PDF but no synchronized logger archive. | **Request data / strong independent tank-thermal-full-loop candidate.** Obtain de-identified pressure, temperature, mass-flow and pre-cooling traces plus reuse terms before treating it as a holdout; draft: `research/KLOPCIC_2024_PRECOOLING_DATA_REQUEST_DRAFT.md`. |
| FCH2RAIL reference HRS and rail vehicle, Wieser et al., DOI 10.1016/j.ijhydene.2025.04.040 | Open-access IJHE paper analyzes 32 days of real HRS/train refuelling, including vehicle-module pressure and dispenser pressure, temperature and mass-flow plots. Section 1 explicitly says rail-vehicle refuelling measurement data were not publicly available; the DLR PDF record and Crossref relation metadata expose no synchronized machine-readable archive or supplement. | **Request data.** Contact DLR (Steffen.Wieser@dlr.de) for de-identified traces, protocol metadata, permission and an immutable archive digest; retain the paper as independent field evidence but do not call it a raw holdout. |
| 3Emotion operational HRS data, Caponi et al., DOI 10.1051/e3sconf/202233406008 | Multi-year operator logs from four 350-bar bus stations, reported as fill amount, duration, average flow, utilization and availability. | **Aggregate context only.** No synchronized pressure, temperature and mass-flow trace is public. |
| 3Emotion four-year operational analysis, Caponi et al., DOI 10.1016/j.ijhydene.2022.10.093 | Peer-reviewed analysis of four years of operator logbooks for five 350-bar stations and 34 buses; reports 14.62 kg/fill and 10.28 min overall means plus demand, utilization and availability. | **Aggregate operating-range benchmark only.** The article does not expose synchronized pressure/temperature/flow files or a machine-readable supplementary archive. |
| HYTRANSFER public GasTeF filling-campaign report | Public report describes 13 filling and 5 emptying tests and 18 recorded-data files with pressure, temperature, gas-path and flow measurements. | **Request files.** The public PDF does not expose the 18 machine-readable files or reuse terms; request them before treating the campaign as an untouched holdout. |
| Beijing Winter Olympics HRS Operational Data List, CSTR 16666.11.nbsdc.aI3fJrzX | National Basic Science Data Center metadata reports 2022 HRS data with dispenser monitoring, fueling records and compressor monitoring; four files, 10.22 MB. | **Access request.** The machine-readable record is marked “approval required” and the file-tree endpoint returns no files without authorization. It is a high-value candidate, not an available holdout. |
| Hungarian HRS digital-twin validation, Hasulyó, DOI 10.32604/ee.2026.081099 | Open-access paper reports operational pressure, temperature, mass-flow and refueling comparisons from an existing Hungarian HRS. | **Request data.** The paper's data-availability statement says supporting data are unavailable because of participant consent and legal restrictions. |
| MetHyTrucks HySaM system measurements, Zenodo DOI 10.5281/zenodo.20590842 | CC BY 4.0 record with three downloadable XLSX time series from hydrogen sampling-system experiments; the files contain 0.5 s pressure/temperature/flow-like channels. | **Measurement-system reference only.** There are no vehicle/tank/refuelling fields or station operating context, so this cannot close the station-to-vehicle full-loop gate. |
| DTU-TES Hydrogen Fuelling Station Library v2.1, Zenodo DOI 10.5281/zenodo.4436147 | Open archive contains a Modelica/Matlab SAE J2601 MC/APRR protocol implementation, coefficient tables and ejector models. | **Protocol/model reference only.** The archive has no measured station or vehicle time-series files, so simulator output cannot be counted as external experimental validation. |
| JRC HIAD 2.2 HRS application rows | Current public workbook contains 34 HRS incidents/near misses with source references, emergency actions, lessons learned and corrective measures. | **Accident-evidence track.** It is suitable for a separately frozen SAGA response-grounding evaluation, but it has no synchronized pressure/temperature/flow trajectory and cannot close the numerical full-loop gate. |
| NREL/National Laboratory of the Rockies retail-station composite products | Public aggregate safety, reliability and fueling-rate/final-pressure charts through 2020. | **Aggregate context only.** No row-level trace or incident narrative archive is exposed. |
| BAM demonstration-HRS monitoring study, DOI 10.3390/app16157856 | 2026 paper reports three days of real HRS monitoring across eight compressor/storage/dispenser safety sensors and chronological field deployment. | **Request data.** The data-availability statement directs requests to the corresponding author; no raw synchronized archive or vehicle-side full-loop data are publicly downloadable. |
| An et al. Samcheok HRS digital-twin sensor table, DOI 10.3390/su16219482 | Open-access paper prints a 24-channel HRS sensor schema and 1 s normal-operation examples covering trailer, chillers, compressors and storage banks. | **Sensor benchmark only.** Vehicle/receptacle pressure and mass-flow channels are absent from the printed table; abnormal compressor/chiller/dispenser values were artificially created, so the paper cannot close the physical full-loop gate. |

## CARB artifact inspection

The official report was downloaded only to the gitignored raw-data directory.

- URL: <https://ww2.arb.ca.gov/sites/default/files/2024-12/Existing%20Light-Duty%20Hydrogen%20Refueling%20Stations%20In-Use%20Study%20Report%20ADA%20AL.pdf>
- File size: 1,090,711 bytes
- SHA-256: `a49e46baa1151847b0d786d0a40c2cc08928e28043152e64ae95a22a06784766`
- PDF pages: 29
- Embedded attachments: 0
- Embedded external data links: 0

The report states that testing occurred from October 2023 through May 2024 and
that some older stations could not record or provide all HGV 4.3-required data.
This limits the likely completeness of any released workbook and must be
captured case by case if CARB supplies it.

## HyStEP artifact inspection

The California Energy Commission's public HyStEP report is a high-value
independent dispenser/protocol-validation lead:

- URL: <https://www.energy.ca.gov/sites/default/files/2021-05/CEC-600-2019-014.pdf>
- Scope: 11 California hydrogen stations were tested from December 2015 through
  August 2017 with three instrumented Type IV 70 MPa test tanks.
- Measurements and procedures: test-tank pressure/temperature, dispenser
  communication and fueling data, CSA HGV 4.3 / SAE J2601 table-based protocol
  checks, and general-fault tests.
- Limitation: the report states that station test data and results are
  confidential business information and therefore are not included in the
  public report.

This is retained as a data-request lead only. It must not be counted as an
eligible holdout until de-identified synchronized files, provenance,
calibration/quality metadata, reuse permission and a cryptographic digest are
obtained and frozen before model evaluation.

## Chinese 35/70 MPa dispenser-test artifact inspection

The article is a useful independent operating-range lead:

- URL: <https://esst.cip.com.cn/article/2020/2095-4239/2095-4239-2020-9-3-702.shtml>
- The page exposes four `T1.csv.zip`–`T4.csv.zip` downloads. Inspection shows
  they contain only initial and final summary tables, not the plotted pressure,
  temperature and mass-flow time series.
- Reported field endpoints include a 35 MPa fill of 8.21 kg in 470 s and a
  70 MPa fill of 5.08 kg in 276 s with a reported peak mass flow of 36 g/s.

These values are suitable for operating-range and face-validity checks only.
The original logger export, sampling interval, calibration records and reuse
permission must be requested before considering this source for a frozen
full-loop holdout.

## Samcheok HRS sensor-table artifact inspection

The open-access paper *Digital Twin-Based Hydrogen Refueling Station (HRS)
Safety Model: CNN-Based Decision-Making and 3D Simulation* provides a useful
public sensor-schema benchmark:

- URL: <https://www.mdpi.com/2071-1050/16/21/9482>
- It documents 24 channels with units and equipment mapping, and prints 1 s
  normal-operation samples for trailer, chiller, compressor and storage-bank
  signals.
- The paper states that abnormal compressor, chiller and dispenser data were
  created artificially, and its printed table does not contain vehicle-side
  pressure or mass-flow channels.

The artifact is therefore suitable for sensor naming, unit and normal-range
cross-checks only. It is not counted as an independent vehicle-fuelling
full-loop holdout.

## H2Protocol public archive inspection

The source page remains publicly reachable at
<http://www.h2protocol.com/h2-fueling-data/> and lists five Tables validation ZIPs
plus one MC Default ZIP. The six local SHA-256 values are recorded in
`data/public_validation/raw/acquisition.json` and mirrored in
`research/external_full_loop_data_search.json`. These are genuine experimental
traces, but they are the already-consumed Powertech source family; they are
retained as transparent benchmark evidence and explicitly excluded from the new
untouched-independent gate.

## NREL HITRF report artifact inspection

The NREL report is a primary source for field-operational context:

- URL: <https://docs.nrel.gov/docs/fy24osti/85333.pdf>
- Table 4 contains sample HITRF fill-level summary fields: timestamp, amount,
  rate, start/end pressure, dispensing temperature and dispensing pressure.
- The published report does not expose the underlying common-time-base sensor
  trace or a downloadable machine-readable workbook. It therefore cannot close
  the full-loop validation gate. It is retained as a lead for requesting
  de-identified HITRF traces from the data owner.

The H2FillS manual is screened separately because it documents an example
`supply_condition.csv` and exported pressure/temperature/mass-flow/SOC fields,
but those examples are part of a simulation package and are not independent
experimental observations:
<https://www.nrel.gov/docs/libraries/hydrogen/h2fills-user-manual.pdf?sfvrsn=b2960c3d_1>.

## NREL H2FillS HDVS supplemental workbook inspection

The official NLR download page exposes the H2FillS package:
<https://www.nlr.gov/hydrogen/h2fills-download>. Its supplemental workbook
`20220816_hdvs_typeIV_test_result.xlsx` is a physical NREL sample test from
2022-08-16, not a simulator-generated trace. It contains 351 one-second rows
for seven 9.8 kg Type-IV tanks (68.6 kg total capacity), with per-tank inlet
pressure and temperature, mass, internal pressure and internal temperature.
The description sheet reports 61.5 kg transferred in 279 s from 1.8 to
75.8 MPa.

The workbook was read locally and evaluated against the frozen Type-IV tank
fit from `research/tank_model_validation_v2.json`. No parameter was fitted or
changed after accessing this candidate. The resulting independent screen is
recorded in
`data/public_validation/results/nrel_h2fills_hdvs_typeiv/validation.json`:
seven tanks, zero joint screens, mean pressure RMSE 6.164 MPa, mean
temperature RMSE 4.625 °C and mean final mass error 0.120 kg. This is a useful
negative diagnostic: the existing tank fit is close on temperature and mass
closure but misses this larger HDVS pressure response. It is not a reason to
tune the model on the holdout.

The H2FillS package `LICENSE.txt` states internal-use-only terms and does not
grant raw-file redistribution. The workbook therefore remains under the
gitignored `data/public_validation/raw/` directory. The package SHA-256,
workbook SHA-256, source URL and rights boundary are recorded in
`research/data_sources.json`, `data/public_validation/raw/acquisition.json` and
`research/external_full_loop_data_search.json`. The missing hose, nozzle,
receptacle and station-controller channels mean this candidate cannot close
the station-to-vehicle full-loop gate.

On 2026-10-04 the official package was downloaded again to check source stability. The archive digest was `ad908714a8533a0049e243330a02aae4d1f8921be8bffca7494e69039a1c`, which differs from the earlier recorded container digest, but the supplemental workbook digest remained `1a3fbe64a50c1c97266bfe0372998513ad3ccec5600fab7bc4b9fc68ad4d9d0c` byte-for-byte. The validation therefore remains pinned to the workbook digest and records the package-container change explicitly; it is not treated as a new holdout or as permission to redistribute the file. The check is retained in `research/nrel_h2fills_package_retrieval_check.json`.

The diagnostic output also computes an EOS-equivalent volume from the measured
mass, internal pressure and internal temperature. Across the seven tanks the
median is 0.24388 m³ versus 0.26780 m³ for the frozen effective-volume
assumption (ratio 0.91071). This is retained in
`data/public_validation/results/nrel_h2fills_hdvs_typeiv/validation.json` as
`geometry_diagnostic.status=diagnostic_only_no_parameter_update`. It explains
why a larger pressure error is plausible without silently fitting the external
screen; it is not a vessel-geometry identification or a validation pass.

The follow-up geometry sensitivity is recorded in
`research/nrel_h2fills_geometry_sensitivity.json` and
`research/NREL_H2FILLS_GEOMETRY_SENSITIVITY.md`. It computes a declared-capacity
volume from the hydrogen EOS (9.8 kg at 70 MPa and 15 °C: 0.243943 m³) and
compares it with the legacy 0.254383 m³ assumption. The exploratory
capacity/EOS variants reduce the mean pressure error and pass the local 7-tank
screen, but the comparison was performed after the workbook was opened. It is
therefore a structural diagnostic only; a new frozen protocol and untouched
holdout are required before changing the default or claiming independent
validation.

## NREL HDVS aggregate campaign context

The DOE/NREL performance report records a second, October 2022 complete-HDVS
campaign in addition to the August Type-IV-only sample:
<https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/review23/scs031_onorato_2023_o-pdf.pdf?Status=Master>.
The public aggregate values are 61.5 kg in 4.7 minutes (13.2 kg/min average,
18.7 kg/min peak) and 82.3 kg in 6.6 minutes (12.6 kg/min average, 23 kg/min
peak). They are useful operating-range context and a request lead for the
second raw trace, but no synchronized station/vehicle time series are exposed,
so neither campaign closes the full-loop holdout gate by itself.

## UCI early HRS supplementary-artifact inspection

The UCI early HRS paper is an IJHE field-data lead:
<https://doi.org/10.1016/j.ijhydene.2020.08.251>. The publicly reachable
supplementary DOCX was downloaded from the article asset URL:
<https://ars.els-cdn.com/content/image/1-s2.0-S0360319920333073-mmc1.docx>.

- Local artifact: `data/public_validation/raw/uci_early_hrs/supplementary_mmc1.docx`
- Size: 66,116 bytes
- SHA-256: `a927984e5b9200cca68c1f559768758b2563fde8d2e8f70d9045136d8c6deaf8`
- Content: four aggregate operational charts; no row-level synchronized
  pressure, temperature, mass-flow or vehicle/receptacle trace.

This is therefore independent field context and a data-request lead only. The
charts were not digitized for the primary claim. The required request is a
de-identified event-level/logger export with a common clock, channel dictionary,
calibration and quality flags, initial conditions, protocol metadata and reuse
permission from the UCI NFCRC/CEC data custodian.

## NREL H2IQ December 2022 artifact inspection

The DOE/NREL briefing
<https://www.energy.gov/sites/default/files/2022-12/h2iq-121922.pdf> confirms
the HDVS configuration used in the heavy-duty demonstrations: nine configurable
tanks, including seven Type-IV tanks for the 60+ kg fill and two Type-III tanks
for the remaining capacity. It labels tank-by-tank internal pressure and
temperature channels and mass-flow context, which is useful for checking the
model's equipment map and operating-range assumptions.

The PDF is a plot/report artifact rather than a machine-readable logger export:

- Local artifact: `data/public_validation/raw/nrel_h2iq_2022/h2iq-121922.pdf`
- SHA-256: `73ee453a4efbdd76fa993df549c9d673b1a65fdf963593906985c4fd30660fc`
- Common time base: not publicly available.

It is retained for configuration and face-validity checks and as a request lead;
it cannot close the independent station-to-vehicle full-loop holdout gate.

## California Energy Commission Oakland/EBMUD fuel-log inspection

The CEC project report for the Oakland/EBMUD hydrogen station is another useful
field-data lead:
<https://www.energy.ca.gov/sites/default/files/2025-09/CEC-600-2025-032.pdf>.
The report says the commissioned station collected fuel-log data for both
heavy- and light-duty service and describes the fields available for each fill:
start time, hydrogen mass, fill duration, start/final pressure, final SOC,
communication status and calculated fill rate.

The same report identifies material gaps: no dispenser identifier, ambient
temperature, pre-cooling temperature, tank temperature or maintenance-event
description. The public PDF does not expose a synchronized row-level logger
export. The locally inspected artifact is 5,387,934 bytes with SHA-256
`6f3c4351b15bcdda54e06daef0c8ed789e49bfbdde381a266f6e4b1640231d04`.

This is a real-station event-summary benchmark and a high-value request lead,
not an eligible untouched full-loop holdout. The data request should seek the
de-identified event log and station/vehicle logger files, a channel dictionary,
calibration and quality flags, protocol metadata, maintenance markers and reuse
permission. The report's stated missing temperature fields also prevent a
defensible thermal-validation claim from the public artifact alone.

## NorCAL ZERO Oakland heavy-duty field report

The CARB/CEC NorCAL ZERO report covers 30 Hyundai XCIENT fuel-cell drayage
trucks and the FirstElement Fuel Oakland 700-bar station:
<https://ww2.arb.ca.gov/sites/default/files/2025-08/NorCAL%20ZERO%20Final%20Report.pdf>.
It describes operational collection from October 2022 through September 2025
and reports station event fields such as timestamps, hydrogen quantity, fill
duration, start/final pressure, final SOC and communication status. The report
also discusses station pressure/fill-time records and the practical problems
linking vehicle and station logs.

The public report is not a raw archive. The locally inspected PDF is 5,031,126
bytes with SHA-256
`c45ddbe0c1d9c68549ebc6408f5661819b46d9b6a6d78c80235ff7d29784ff4d` and does
not expose a downloadable synchronized row-level station/vehicle logger. The
report identifies missing or incomplete ambient-temperature, automatically
recorded pre-cooling/tank-temperature and maintenance linkage. It is therefore
an independent heavy-duty field benchmark and a strong data-request lead, not
an eligible untouched full-loop holdout.

## 2026-10-03 primary-source recheck

The Cal State LA back-to-back paper has a publicly reachable accepted-manuscript
record at the U.S. Department of Energy Office of Scientific and Technical
Information (OSTI):
<https://www.osti.gov/biblio/1977265>. The record exposes the manuscript PDF and
the DOI, but it does not expose the one-year synchronized station log described
in the paper as a downloadable raw data archive. The paper therefore remains a
data-request lead and is not promoted to a holdout by reading values from plots
or summary tables.

NREL's infrastructure-analysis page explicitly states that industry partners'
raw station data are secured and that public composite data products are
aggregated so individual companies cannot be identified:
<https://www.nrel.gov/hydrogen/hydrogen-infrastructure-analysis>. This confirms
that the public CDP charts cannot supply the pressure/temperature/flow time
series required by the full-loop gate.

The official H2FillS page documents validation against empirical fueling data,
but the software download is registration-gated and the product page does not
publish an independent raw trace archive:
<https://www.nrel.gov/hydrogen/h2fills>. H2FillS remains a reference simulator
and a possible data-request route, not an external dataset that can be scored
here.

The MetHyTrucks HySaM and NPL records are genuine open raw-data leads, but their
scope is hydrogen sampling-system metrology rather than a vehicle refuelling
event: <https://zenodo.org/records/20590842> and
<https://zenodo.org/records/20590761>. The 13 CC BY 4.0 XLSX files have
0.5-second time-of-day samples and pressure/temperature/flow-like channels,
but no public channel dictionary establishing vehicle or receptacle pressure,
transferred mass, tank capacity, vehicle temperature, initial state or
refuelling-protocol metadata. File hashes and workbook headers are frozen in
`research/metHyTrucks_public_measurement_recheck_2026_10_04.json`. They are
therefore retained for signal-handling and calibration context only and are not
promoted to the HRS full-loop holdout.

The Clean Hydrogen Partnership's H2-Stations export API is open under CC BY
4.0 and is useful for station inventory, layout, availability, usage status,
derived low-storage status, pricing, events and photographs:
<https://docs.h2-stations.eu/for-data-users/api-v2/>. It deliberately does not
publish synchronized pressure, temperature and mass-flow traces, numeric
storage inventory, or vehicle-side fill state. It is therefore operations
context and face-validity evidence only; it cannot close the untouched
full-loop fueling-validation gate.

The BAM demonstration-HRS monitoring study is a high-value request lead:
<https://doi.org/10.3390/app16157856>. It reports real station operation with
eight safety-critical compressor, storage and dispenser sensors and a
chronological field deployment, but its data-availability statement does not
publish the raw trace files. The article's semi-synthetic anomaly injections
must not be relabelled as independent incident data. Until de-identified raw
traces, channel definitions, calibration information and reuse terms are
received, this source supports a request for sensor/anomaly validation only.

BAM's facility description states that refuelling operating data are collected,
enriched with metadata and made available for model and digital-twin
development, which makes the BAM custodian a high-value access route even
though no public raw archive was found:
<https://www.bam.de/Content/EN/Standard-Articles/Topics/Energy/Hydrogen/hydrogen-h2-filling-stations.html?nn=83556>.

The NREL HITRF experiment reported by Kuroki et al. (DOI
<https://doi.org/10.1002/ente.202300239>) is a strong partial-station data
request lead: the paper gives a 6.3→73.0 MPa fill in 186 s and describes
pressure, receptacle temperature, internal gas temperature and liner channels.
The associated OSTI/NREL record states that research data are not shared, so
the experiment remains a request candidate rather than a public holdout.

The 3Emotion four-year operational study is published in the *International
Journal of Hydrogen Energy* (DOI
<https://doi.org/10.1016/j.ijhydene.2022.10.093>). Its public article reports
operator-logbook aggregates, including 14.62 kg per fill and 10.28 minutes
average refuelling time, for five stations and 34 buses, but does not provide
the synchronized pressure, temperature and flow files required by the primary
full-loop gate. It is retained as an external operating-range benchmark only.

The public HYTRANSFER GasTeF campaign report describes 18 recorded-data files
from filling and emptying tests:
<https://s02291b7740b89df1.jimcontent.com/download/version/1493713659/module/11623534399/name/HyTransfer_Report%20on%20the%20experimental%20filling%20test%20campaign_public.pdf>.
The report itself does not publish those files or their reuse terms, so they
have been added as a JRC/HyTransfer data-request lead rather than copied or
treated as a validation holdout.

## NIST field-test-standard artifact inspection

The NIST field-test-standard paper is a strong independent metrology lead:

- DOI: <https://doi.org/10.1016/j.flowmeasinst.2015.10.010>
- NIST used a 35 MPa Type III, approximately 1 kg H₂ field-test standard at a
  retail dispenser and performed three 0.41 kg and four 0.75 kg H₂ drafts.
- The standard continuously monitored tank pressure and temperature and
  compared gravimetric, PVT and master-meter mass results. The reported field
  methods agreed within 1.53%.
- The article provides protocol, uncertainty and plotted traces but no
  machine-readable synchronized logger export; the dispenser readout was
  intentionally disabled during the tests.

Request the de-identified logger files, sampling interval, calibration records,
and permission to publish derived metrics before using this source for a
frozen validation split.

## DOE/NREL H2IQ Hour experiment artifact inspection

The official March 2024 presentation reports a real HITRF heavy-duty fast-flow
experiment and gives enough aggregate endpoints to check whether a simulated
operating point is in a plausible field range:

- URL: <https://www.energy.gov/sites/default/files/2024-04/h2iqhour-03262024.pdf>
- 73 kg transferred in 423.5 s; 358.9 s active fueling time.
- Average flow 172.3 g/s and peak flow 483.33 g/s.
- Pressure increased from 5.5 to 74.6 MPa at 9.9 MPa/min under SAE
  J2601-5 MCF-HF-G H70 FM300 T40.

These values are not a primary validation set because the source supplies a
plot and aggregate summary rather than the underlying synchronized sensor
series. They must not be converted to a claimed time-series validation by
digitising the chart.

## Acquisition sequence

1. Send the prepared CARB request for the Appendix A workbook and de-identified
   fill-level exports behind the published figures.
2. Ask for timestamps, units, variable definitions, CHSS capacity, initial
   state, protocol version, temperature category and any quality/exclusion
   flags, together with reuse terms.
3. Send equivalent non-publishing requests to JRC GasTeF, the HYTRANSFER
   GasTeF file custodian, PRHYDE data custodians
   and the Cal State LA authors. The JRC draft is
   `research/JRC_GASTEF_DATA_REQUEST_DRAFT.md` and
   asks for the database described by the 2014 paper, including internal
   thermocouple, tank pressure, inlet pressure, inlet temperature, flow and
   test metadata, with permission to publish derived metrics.
4. Send the Empa/FCH2RAIL draft in
   `research/EMPA_FCH2RAIL_DATA_REQUEST_DRAFT.md` to the corresponding data
   custodians. Request de-identified synchronized traces and reuse terms;
   publication of the open articles alone is not treated as permission to
   redistribute measurements.
5. Send the Cal State LA request in `research/CALSTATE_DATA_REQUEST_DRAFT.md`
   to the HRFF data custodian. It covers both the multi-year
   energy-performance study and the back-to-back fueling study indexed by OSTI
   record 1977265.
6. Send the BAM demonstration-HRS request in
   `research/BAM_HRS_DATA_REQUEST_DRAFT.md` for de-identified field sensor
   traces and any vehicle-side channels. Treat semi-synthetic anomalies as a
   separate diagnostic unless a real incident label is supplied.
7. Send the NREL HITRF/NFCTEC request in
   `research/NREL_HITRF_DATA_REQUEST_DRAFT.md` for de-identified full-station
   traces or an approved access route. NREL's public composite products remain
   aggregate context only.
8. Send the Hungarian HRS request in
   `research/HUNGARIAN_HRS_DATA_REQUEST_DRAFT.md` to the study author or data
   custodian, subject to their consent and legal restrictions.
9. Send the NBSDC request in `research/NBSDC_HRS_DATA_REQUEST_DRAFT.md` to the
   National Basic Science Data Center/Tsinghua data custodian. Request the four
   files named by the catalog, field dictionaries, timestamps, units, quality
   flags, de-identification terms and permission to publish derived metrics.
10. On receipt, hash and quarantine the files before opening outcomes; freeze
   case eligibility and the corrected model commit in a new protocol manifest.
11. Evaluate the frozen model once. Retain every eligible failure and do not use
   the new outcomes for tuning.
12. If CARB, JRC, Cal State LA, Empa, FCH2RAIL, NREL HITRF, the BAM study, the Hungarian HRS study and
   NBSDC cannot release the traces, make an equivalent
   request to NIST using `research/NIST_FTS_DATA_REQUEST_DRAFT.md`. Do not
   substitute graph digitisation for raw data in the primary full-loop claim.

## Current conclusion

No newly located public source currently satisfies the full-loop eligibility
rule. The gate therefore remains **PENDING/FAIL**, and no broad station-model
validation claim is permitted. This search record prevents unavailable plots or
aggregate products from being silently relabelled as independent validation.

The machine-readable counterpart is
`research/external_full_loop_data_search.json`; its `review_log_2026_10_03`
records the URLs and the same access decisions used by the readiness audit.

## 2026-10-04 Zenodo and accident-evidence follow-up

A targeted Zenodo API review of records matching `hydrogen AND station`,
`hydrogen fueling` and `hydrogen refuelling station` found the DTU-TES
Hydrogen Fuelling Station Library (DOI
<https://zenodo.org/records/4436147>). The archive is useful for an
independent SAE J2601 MC/APRR protocol and Modelica implementation comparison,
but the downloaded release contains only source/model files and coefficient
tables; no measured station or vehicle time series are present. Its outputs
therefore cannot be used as an external validation set.

The current JRC page identifies HIAD 2.2 as the public accident/incident
workbook, updated through 31 December 2025:
<https://minerva.jrc.ec.europa.eu/en/shorturl/capri/hiadpt>. The repository
freezes 34 HRS application rows from the workbook in
`research/hiad_hrs_public_evidence.json`, including emergency-action, lesson
and corrective-measure fields. This is a strong source for scenario taxonomy
and response-grounding, but its event records are not synchronized process
trajectories. The casebook, ethics determination and independent expert
review remain separate pending gates; no accident-response effectiveness
claim is made from the workbook alone.

NREL's retail composite data products
(<https://www.nlr.gov/hydrogen/infrastructure-cdps-retail>) add independent
aggregate safety, reliability and fueling-range context. They do not expose
row-level pressure/temperature/flow traces or a machine-readable incident
archive and therefore do not close the numerical full-loop gate.
## 2026-10-04 H2-Stations and infrastructure-inventory follow-up

The current official H2-Stations documentation was rechecked:
<https://docs.h2-stations.eu/for-data-users/>. API v2 now documents static
station layouts and four signal types (availability, usage, hydrogen storage
and pricing), while the sandbox serves fixed sample fixtures. These are useful
for station topology and operations context, but the API does not expose a
common-time-base vehicle/receptacle pressure, temperature and mass-flow logger
or historical process trajectory. It remains **operations context only**.

Two additional public infrastructure inventories were screened:

- The European IPCEI/European Hydrogen Observatory May 2026 workbook lists
  public HRS locations and dispenser types but contains no process telemetry:
  <https://ipcei.observatory.clean-hydrogen.europa.eu/hydrogen-landscape/distribution-and-storage/hydrogen-refuelling-stations>.
- California's 2026 medium- and heavy-duty infrastructure dataset provides
  dispenser/nozzle counts, locations and funding fields under CC BY, but no
  tank, vehicle or controller telemetry:
  <https://lab.data.ca.gov/dataset/medium-and-heavy-duty-infrastructure>.

These sources improve static station-scale and equipment-mix context. They do
not change the full-loop gate: no new untouched public time-series holdout was
found, and no availability, usage, storage-status or static inventory record
may be relabelled as numerical fueling validation or accident-response
effectiveness evidence.
## 2026-10-04 Grüne and GasTeF follow-up

The primary Grüne et al. IJHE article confirms the pending pressure-decay
experiment (0.37 dm³ reservoir, 3/4/10 mm nozzles and initial pressure up to
200 bar), but the accessible publication exposes plots rather than a
machine-readable trace: <https://doi.org/10.1016/j.ijhydene.2013.08.076>. The
HyTunnel-CS technical report reproduces the pressure-decay figure and release
timing, but likewise does not publish the numeric series:
<https://hytunnel.net/wordpress/wp-content/uploads/2019/09/HyTunnel-CS_D1.2_Risks-and-Hazards.pdf>.
The repository therefore correctly keeps the Grüne gate pending because the
half-pressure endpoint cannot be independently traced from the available raster.

JRC confirms that GasTeF performs fast-fill experiments with pressure and
temperature instrumentation and its reference paper describes a 165-test
archive with 0.6 s logging, but no machine-readable archive or reuse terms were
found in the public sources. GasTeF remains a high-value raw-data request lead,
not an available holdout: <https://joint-research-centre.ec.europa.eu/what-we-do/laboratories/high-pressure-gas-testing-facility_en>.

Figures were not digitised into the primary claim, and facility descriptions
were not treated as access to the underlying logs.
## 2026-10-04 NRC British Columbia dispenser-reliability follow-up

The National Research Council Canada report *Dispenser reliability analysis for
hydrogen refuelling stations in British Columbia* is a useful independent field
benchmark (<https://doi.org/10.4224/40003368>; official PDF:
<https://nrc-publications.canada.ca/eng/view/ft/?id=19b8dc45-2084-4d87-8525-9f7e52c992ac>).
It analyzes approximately 22,593 H70T40 fueling events at four British Columbia
stations in 2022--2023 and describes SAE J2600/J2601/J2799 context, connection
pulses, leak-check periods, pressure/temperature/flow patterns and protocol-based
termination. Reported aggregate results include 6.5% connection retries, 69.4%
normal fills, 26.6% incomplete fills and 3.9% fault fills; the report attributes
fault fills to station-, user- and vehicle-related causes.

The official PDF was inspected for downloadable attachments and raw-data links.
It contains figures and aggregate tables but no CSV/XLSX attachment or
machine-readable common-time-base logger export. It is therefore classified as
**REPORT_CONTEXT_AND_DATA_REQUEST_LEAD**: valuable for face-validity checks,
fault-taxonomy coverage and test design, but ineligible to close the numerical
full-loop gate. The report figures are not digitised into the primary claim. A
follow-up request should seek de-identified station logs, field definitions,
quality flags, protocol version and permission to publish derived metrics.
The prepared request is stored in
`research/NRC_BC_DISPENSER_DATA_REQUEST_DRAFT.md`.
## 2026-10-04 recent IJHE high-flow experiment follow-up

A recent *International Journal of Hydrogen Energy* article reports an
independent 35 MPa high-flow hydrogen refuelling platform with large-scale
Type-IV storage, measured transient mass-flow boundaries and tank-temperature
responses (<https://doi.org/10.1016/j.ijhydene.2025.151093>). The paper reports
that measured transient flow improves peak-temperature agreement to within 3 K,
that a constant-flow assumption can overpredict the early peak by more than
10 K, and that 15--30 degree inlet angles reduce peak gas temperature by up to
12 K.

The public article record was screened for a machine-readable data archive. No
downloadable synchronized pressure--temperature--flow logger files or reuse
terms were located. The source is therefore registered as
**REQUEST_DATA_HIGH_VALUE_TANK_THERMAL_LEAD**: it can materially strengthen
independent large-tank thermal validation if the authors release de-identified
raw logs, but its figures and summary error claims are not counted as the
primary validation set. A prepared request is stored in
`research/DENG_2025_HIGHFLOW_DATA_REQUEST_DRAFT.md`.

## 2026-10-04 FCH2RAIL IJHE measurement-data follow-up

The open *International Journal of Hydrogen Energy* paper by Wieser et al. (DOI
<https://doi.org/10.1016/j.ijhydene.2025.04.040>) is a useful independent
large-capacity operating-range and protocol-context source. It analyses 32 days
of refuelling for a FCH2RAIL hydrogen train using a transportable HRS, with a
four-module Type-III vehicle system and station/trailer/HRS measurements. The
paper describes dispenser pressure, temperature and mass-flow channels together
with tank-module pressure/temperature measurements and compares measured
refuels with a model.

The DLR public record and article PDF do not expose a synchronized,
machine-readable logger archive or supplementary dataset; the article itself
states that public rail-vehicle refuelling measurement data were not available.
It is therefore registered as **REPORT_CONTEXT_AND_DATA_REQUEST_LEAD**, not as
an eligible untouched full-loop holdout. The prepared request is
`research/FCH2RAIL_DATA_REQUEST_DRAFT.md`. No figure digitisation is used for
the primary validation claim.

## 2026-10-04 JHFC/NEDO six-run data availability follow-up

The 2012 *International Journal of Hydrogen Energy* study by Monde et al.
reports six practical 35/70 MPa filling conditions from four vehicle tanks and
states that complete measurements had been opened for analysis. The described
channels include vehicle-tank pressure and hydrogen temperature plus the
station-supplied pressure and temperature:
<https://doi.org/10.1016/j.ijhydene.2011.12.136>.

The public article, the official JHFC archive and indexed supplementary
material were checked. They expose the paper, plots and project documents, but
not a machine-readable six-run logger archive, a common-time-base export or
reuse terms. The JHFC page is an archived project portal with reports and
station specification sheets, not a raw-data catalogue:
<https://www.jari.or.jp/jhfc/>.

This source is therefore recorded as **REPORT_CONTEXT_AND_DATA_REQUEST_LEAD**.
The historical statement that data were “made available” is a lead for the
authors and JARI/NEDO custodians, not evidence of current public access. No
figure digitisation is promoted to the primary claim. The independent
full-loop gate remains open until the six raw runs, channel dictionary,
calibration/provenance and reuse terms are received and frozen.

## 2026-10-04 PRHYDE public-deliverable inspection

The public PRHYDE D6.7 deliverable documents real ZBT and Nikola campaigns on
240 L H70, 350 L H50, 322 L H35 and 165 L H70 tanks. Its test matrices and
model-comparison figures describe pressure, temperature, flow and protocol
conditions in detail:
<https://lbst.de/wp-content/uploads/2023/04/PRHYDE_Deliverable-D6-7_Results_as_Input_for_Standardisation_V1-2_final_Apr_2023.pdf>.

The 222-page PDF was downloaded and checked for attachments and machine-readable
logger exports. It contains Tables 16--19, plots and aggregate error summaries,
but no CSV/XLSX time-series file or common-time-base archive. It is therefore
retained as **REPORT_PLOT_SUMMARY_ONLY** and a data-request lead. The report's
figures are not digitised into the primary validation set; the full-loop gate
remains unchanged.

## 2026-10-04 Green Hysland and H2 MOBILITY monitoring follow-up

The Green Hysland data-collection page advertises historical, standardised
time-series downloads for assets across its island hydrogen value chain:
<https://greenhysland.eu/data-collection-system/>. The public description is
useful as a reproducibility and data-catalogue lead, but it does not expose a
vehicle/receptacle refuelling logger, a common pressure--temperature--mass-flow
time base, or a downloadable HRS fill trace in the inspected page. It is
therefore retained as **VALUE_CHAIN_KPI_CONTEXT_ONLY** until the historical
repository exposes the required channel-level records and reuse terms.

The two linked report exports were also retrieved and inspected directly:
[daily report 38](https://enagasrenovable.idboxrt.com/reports/api/ReportViewer/exportOpenPermalink/38?op=uBIKdfHvI&sg=3)
(SHA-256 `06269271d5f954b7090d1522034c8fbaf982dc43d1b1f99e626dfc2b6b998e7a`)
and [historical report 46](https://enagasrenovable.idboxrt.com/reports/api/ReportViewer/exportOpenPermalink/46?op=KvUKXujUk&sg=3)
(SHA-256 `f8b089f25a73e775819b24ae428882f9a958d889b7ea0c515536d78265c57e00`).
They contain H2-plant and tube-trailer KPI fields, while the HRS Provisional
section has no populated pressure, dispenser, nozzle, vehicle, refuelling-time
or SOC observations. The reports therefore cannot close the full-loop gate.

ENDA describes an H2 MOBILITY monitoring deployment that records approximately
75--400 technical parameters at 90 German stations and stores short-interval
signals in time-series databases:
<https://enda.eu/en/h2_monitoring>. This is a strong custodian lead for a
large independent field archive, but the public page provides no export,
station logger schema, access terms or synchronized vehicle-side traces. It is
therefore classified as **REQUEST_DATA_FIELD_MONITORING_LEAD**, not as an
available holdout. No claim is made from the monitoring-system description
alone.

The new search did not identify a downloadable untouched full-loop HRS archive;
the numerical validation gate and the associated request list remain open.

## 2026-10-04 component datasets and station-protocol follow-up

The newly located [MHC Dataset](https://github.com/LukasFleming/MHC-Dataset)
and its [Zenodo record](https://zenodo.org/records/19036733) provide 29
two-stage metal-hydride compressor experiments under CC BY 4.0. The workbooks
contain raw and processed pressure, temperature and hydrogen mass-flow channels.
They are useful for a separately scoped compressor-component screen, but the
apparatus is not the positive-displacement/cascade HRS model in this repository
and has no dispenser, receptacle, vehicle tank or J2601 transaction trace. It is
therefore classified as **COMPRESSOR_COMPONENT_CONTEXT_ONLY** and is not added
to the full-loop holdout.

The public [HSR-Rig-Project](https://github.com/gadoseb/HSR-Rig-Project) also
describes timestamped laboratory logs with hydrogen flow, temperature, pressure,
cumulative hydrogen and absorption/desorption markers. Its metal-hydride
storage-reactor scope does not include station dispensing or a vehicle-side
receptacle, so it is retained as **STORAGE_REACTOR_CONTEXT_ONLY**.

The Zenodo PDF for the South African metal-hydride station
([Lototskyy et al., DOI 10.1016/j.ijhydene.2019.05.133](https://doi.org/10.1016/j.ijhydene.2019.05.133))
reports 50--60 bar feed, a 200 bar compressor, 6--15 minute dispensing and
13--28 kg/day throughput. The public item is a report with plots and summary
values, not a synchronized machine-readable logger, so it is recorded as
**REPORT_CONTEXT_AND_DATA_REQUEST_LEAD**; figures are not digitised for the
primary claim.

The official [Cal State LA operating sequence](https://www.calstatela.edu/ecst/h2station/operation)
documents storage-equilibrium compressor start, periodic 3000 psi leak-test
pauses and chilled dispensing targets near −17 to −20 °C. It is retained as
**OPERATING_PROTOCOL_CONTEXT_ONLY** because no downloadable synchronized
pressure--temperature--mass-flow archive is exposed.

These sources improve component and operating-procedure coverage but do not
close the independent station-to-vehicle full-loop gate. The repository keeps
that numerical claim open until an untouched raw archive with common time base,
vehicle/receptacle pressure, transferred mass or mass flow, units, initial
conditions, protocol metadata, provenance and reuse terms is received and
frozen before scoring.

## 2026-10-04 BAM living-lab and anomaly-data follow-up

The official [BAM H2Safety@BAM living-lab description](https://www.bam.de/Content/EN/Standard-Articles/Topics/Energy/Hydrogen/hydrogen-h2-filling-stations.html?nn=83556)
states that the research station records compressor, buffer-storage, gas-cooler
and dispenser operation with sensor uncertainty and external metadata for model
and digital-twin development. This makes BAM a high-value field-data custodian,
but the public page does not provide a synchronized station-to-vehicle logger,
data dictionary or reuse terms. It is therefore classified as
**REQUEST_DATA_HIGH_VALUE_FIELD_LIVING_LAB**, not as an available holdout.

The recent open paper by Kim et al. ([DOI 10.3390/app16157856](https://doi.org/10.3390/app16157856))
reports three days of BAM demonstration-station normal data sampled at one
second and downsampled to one minute, then evaluates spike, drift and noise
injections. The underlying sensor files are not released in the article record,
and the injected anomalies are semi-synthetic. It is retained as
**REPORT_CONTEXT_AND_DATA_REQUEST_LEAD** for anomaly-protocol comparison only.

The [H2-SimNet Zenodo release](https://zenodo.org/records/17871393) is a useful
open 509 MB multivariate benchmark with leak and compressor-fault labels, but it
is explicitly generated by a MATLAB/Simscape model for hydrogen-blend transport
networks. It is classified as **SIMULATION_CONTEXT_ONLY** and cannot support a
measured HRS physics claim or replace an independent station-to-vehicle holdout.

The BAM request should seek de-identified station, dispenser and vehicle logs,
channel definitions, time synchronisation, uncertainty/calibration records,
protocol versions, quality flags, initial conditions and permission to publish
derived metrics. Those files must be hashed and frozen before any scoring; no
paper or data-gate status is changed by the facility description alone.

## 2026-10-04 Canadian operational leakage-data custodian follow-up

The [Government of Canada DTPR AI Register entry](https://canada.clarable.ai/technologies/5d8e9751-afa5-40d2-87bd-ce3d90a64eaf)
identifies an NRC/HTEC system that uses anonymized operational hydrogen
refuelling-station streams for hydrogen produced, hydrogen filled and station
operating modes to detect losses and localize a responsible component. This is
a promising real-world safety-data custodian, but the public register exposes no
downloadable samples, channel dictionary, timestamps, event labels, or reuse
terms. It is therefore classified as
**REQUEST_DATA_OPERATIONAL_LEAKAGE_CUSTODIAN**.

The request should seek de-identified produced/filled mass, pressure,
temperature, flow, gas-detector and operating-mode streams together with
quality flags, event labels, provenance, and permission to publish derived leak
and decision-support metrics. The register description alone cannot support a
leak-detection performance claim or close the physical full-loop gate.

## 2026-10-04 Hungarian HRS digital-twin paper follow-up

The 2026 paper by Hasulyó, [*Dynamic Digital Twin Network for Real-Time Safety
Monitoring and Predictive Risk Assessment of Hydrogen Refueling
Infrastructure*](https://doi.org/10.32604/ee.2026.081099), is a useful methodological
analogue and a high-value data-request lead. It reports operational-data
comparisons for a Hungarian HRS: final pressure 948 versus 955 bar, peak tank
temperature 59.8 versus 61.5 °C, delivered mass 6.12 versus 6.20 kg, and average
mass flow 0.0171 versus 0.0178 kg/s. The paper describes 1 Hz PLC/Modbus data
integration and a ±5% acceptance threshold.

The paper's data-availability statement explicitly says that supporting data are
not publicly available because of participant consent and legal restrictions.
No machine-readable station/vehicle logger, channel dictionary, uncertainty
record or reuse terms were found in the article. It is therefore classified as
**REPORT_CONTEXT_AND_DATA_REQUEST_LEAD** and cannot close the independent
full-loop numerical gate. The controlled-access request is drafted in
[HUNGARIAN_HRS_DATA_REQUEST_DRAFT.md](HUNGARIAN_HRS_DATA_REQUEST_DRAFT.md).
The summary table is not digitised or counted as validation.

## 2026-10-04 open-repository recheck

I rechecked Zenodo's public records API with searches for `hydrogen fueling
data`, `hydrogen refuelling data`, `hydrogen refueling station time series`,
`hydrogen dispenser data` and `SAE J2601 data`, and repeated web/GitHub searches
for synchronized pressure, temperature and mass-flow traces. The returned
records were protocol/model libraries, sampling or metrology documents, static
inventories, simulation/component datasets, or the sources already recorded in
this log. The HSR-Rig-Project release has useful laboratory storage-reactor
logs, but no dispenser, receptacle or vehicle-side HRS loop.

No new public archive met the independent full-loop eligibility rule. Search
results are retained as discovery evidence only; none is counted as validation
without file-level provenance, a common time base, vehicle/receptacle pressure,
transferred mass or mass flow, initial conditions, protocol metadata and reuse
terms.
Add the official NREL HITRF page and the NREL Data Catalog follow-up to the
public-source screening log. The HITRF page confirms the integrated station,
automated data logging, and J2601-capable dispensing, while the catalogue
recheck and the 2024 IJHE sample-fill table still do not expose the full
synchronized station-to-vehicle logger needed for independent validation.

## 2026-10-04 NREL HITRF/data-catalog follow-up

The official [NREL Hydrogen Infrastructure Testing and Research Facility
(HITRF) description](https://www.nrel.gov/hydrogen/hitrf-animation?print=)
confirms an integrated production, compression, storage, chilling and H70/H35
dispensing facility. It states that an automated data-logging system collects
operating and maintenance data from HITRF components and that the research
dispenser supports SAE J2601/MC Formula fueling and component-reliability
experiments. The public page does not expose a downloadable synchronized
station-to-vehicle logger, channel dictionary, uncertainty record or reuse
terms, so it is classified as **REQUEST_DATA_HIGH_VALUE_FIELD_LIVING_LAB**.

The [NREL Data Catalog](https://data.nrel.gov/search-page) was rechecked for
HITRF, hydrogen-fueling and station time-series records. No public file with a
common time base, vehicle/receptacle pressure, temperature, mass flow or
transferred mass, initial conditions, protocol metadata and reuse terms was
identified. This is recorded as **NO_NEW_ELIGIBLE_PUBLIC_RAW_SET**; a negative
catalogue search does not imply that controlled-access NREL data do not exist.

The NREL-hosted [2024 *International Journal of Hydrogen Energy* paper](https://docs.nrel.gov/docs/fy24osti/85333.pdf)
contains a small HITRF sample-fill table with start/end pressure, dispensing
temperature, amount and rate, together with maintenance examples. The related
[dissertation record](https://api.mountainscholar.org/server/api/core/bitstreams/474f5f0b-4d5d-417a-a2c8-71633293835d/content)
describes the highly instrumented HITRF reliability programme and controlled
fill-cycle testing. These are useful endpoint and protocol-context leads, but
they do not publish the underlying synchronized logger package or a reusable
data dictionary. They are therefore classified as
**REPORT_CONTEXT_AND_DATA_REQUEST_LEAD**, not as a full-loop holdout.

The next evidence request should target a de-identified HITRF export with
common timestamps, vehicle/receptacle pressure, gas and tank temperature, mass
flow or transferred mass, source/cascade states, initial conditions, protocol
version, quality/calibration metadata and permission to publish derived metrics.
Any approved subset must be hashed and frozen before scoring. The independent
full-loop numerical gate remains open.

## 2026-10-04 Chinese 35/70 MPa dispenser endpoint-table follow-up

The public article [Study on comprehensive evaluation of 35 MPa/70 MPa hydrogen
dispenser refueling performance](https://esst.cip.com.cn/article/2020/2095-4239/2095-4239-2020-9-3-702.shtml)
(DOI [10.19799/j.cnki.2095-4239.2020.0049](https://doi.org/10.19799/j.cnki.2095-4239.2020.0049))
reports two real dispenser tests and provides CSV downloads for endpoint tables.
The 35 MPa test ends at 35.4 MPa, 64 °C, 8.21 kg and 470 s after a 2.2 MPa
start; the 70 MPa test ends at 81.6 MPa, 65.8 °C, 5.08 kg and 276 s after a
1.7 MPa start. The paper also describes pressure, temperature and mass-flow
curves, but the downloaded T1/T2/T4 files are endpoint tables rather than a
common-time-base raw station/vehicle logger. They are classified as
**PUBLIC_ENDPOINT_TABLE_DIAGNOSTIC**, with reuse terms requiring citation and
permission review.

The reproducible screen is stored in
[cip_dispenser_endpoint_screen.json](cip_dispenser_endpoint_screen.json) and is
run by `scripts/run_cip_dispenser_endpoint_screen.py`. Under the declared
85 °C safety limit, the current model stopped on `safety-temperature` in both
cases. It predicted 3.26 MPa versus 35.4 MPa for the 35 MPa case and 66.46 MPa
versus 81.6 MPa for the 70 MPa case, with corresponding SOC underprediction.
This is an independent negative diagnostic of the thermal/controller state and
source-boundary assumptions, not a full-loop validation pass.

## 2026-10-04 Byrnes/HydDown Zenodo exploratory screen

The open reproducibility archive [10.5281/zenodo.20728325](https://zenodo.org/records/20728325)
contains three embedded hydrogen blowdown validation YAML files (`Byrnes_run7`,
`Byrnes_run8`, and `Byrnes_run9`) with vessel geometry, initial state, orifice,
back pressure and pressure/temperature arrays. The archive is CC BY 4.0 and its
retrieved SHA-256 is recorded in `research/byrnes_zenodo_exploratory_protocol.json`.

Because the embedded validation values were visible before the runner and screen
were written, this is explicitly a post-access exploratory result. The
CoolProp-based non-adiabatic vessel model passes the pressure NRMSE screen in
all three cases and the half-pressure-time screen in two cases; the combined
result is 2/3 and `claim_supported` is false. This improves transparent
component-level evidence but does not close the prospective gate or validate a
station-to-vehicle loop, dispersion, ignition or emergency response.

Reproduction uses `scripts/run_byrnes_zenodo_exploratory.py`; the result is
`research/byrnes_zenodo_exploratory_result.json`.

## Zenodo 4106101 pressure-peaking follow-up (2026-10-04)

A new prospective protocol was frozen before raw outcomes were downloaded for the HyTunnel-CS/Zenodo **Unignited Pressure Peaking Phenomena** release ([10.5281/zenodo.4106101](https://doi.org/10.5281/zenodo.4106101); related publication [10.1016/j.ijhydene.2020.08.221](https://doi.org/10.1016/j.ijhydene.2020.08.221)). All ten experiments with synchronized pressure and mass-flow channels and documented vent geometry were retained. The fixed enclosure pressure-peaking model passed both primary metrics in 7/10 cases, below the predeclared 80% confirmatory threshold. This remains exploratory consequence-submodel evidence and does not change the open independent station-to-vehicle full-loop gate.

- Protocol: `research/zenodo_4106101_pressure_peaking_protocol.json`
- Result: `research/zenodo_4106101_pressure_peaking_result.json`
- Claim boundary: confined unignited pressure peaking only; no full HRS loop, outdoor dispersion, ignition, emergency-response or SAGA-effectiveness claim.
## 2026-10-04 HYTRANSFER report file-level inspection

The public 192-page HYTRANSFER GasTeF report was downloaded and inspected before any numerical data were used. It describes 18 recorded GasTeF files split into groups of 14 and 4 and lists tank pressure, internal/external/liner temperatures, gas-path instrumentation, mass/flow and test metadata. PDF inspection found no embedded data files or external machine-readable download URL. The inspection is recorded in `research/hytransfer_public_report_inspection.json`; the report remains a controlled-access request lead and was not treated as a validation holdout.

## 2026-10-04 Zenodo/API and public-repository recheck

The Zenodo API was rechecked for `hydrogen refueling station`, `hydrogen fueling station`, `hydrogen vehicle refueling`, `hydrogen dispenser`, `hydrogen tank filling` and `hydrogen refuelling`. The record-level classifications and query limitations are frozen in [`open_repository_search_2026_10_04.json`](open_repository_search_2026_10_04.json) and mirrored in `external_full_loop_data_search.json`. The search found no new synchronized station-to-vehicle pressure/temperature/mass-flow archive with initial conditions, protocol metadata and reuse terms. A 2026 *International Journal of Hydrogen Energy* publication record was publication-only (one PDF), so it was not counted as raw validation data.

The Mendeley record [10.17632/8km9z62tct.1](https://data.mendeley.com/datasets/8km9z62tct/1) is a CC BY 4.0, approximately one-second AB2 metal-hydride storage-tank experiment with pressure, flow, temperature and cumulative hydrogen channels. It is useful component storage evidence but has no compressed-gas dispenser, receptacle, cascade or vehicle protocol trace. The Figshare record [10.23642/usn.26117989.v2](https://doi.org/10.23642/usn.26117989.v2) contains mass-flow, filling-pressure and 29-sensor concentration measurements for open-channel hydrogen dispersion; it is already consumed in the repository's consequence validation and is not a new full-loop fueling holdout.

Decision: **NO_NEW_ELIGIBLE_PUBLIC_RAW_SET**. These are discovery classifications only; no publication, component experiment or already-consumed dispersion archive is promoted to the independent full-loop gate. The next request remains a de-identified NREL HITRF, JRC HYTRANSFER/GasTeF, CARB/HyStEP or NIST FTS logger export with hashes, metadata and reuse terms frozen before outcome access.

## 2026-10-04 Cal State LA HRFF public-data recheck

The Cal State LA Hydrogen Research and Fueling Facility is the strongest public
real-station lead found in this search. The open-access *International Journal
of Hydrogen Energy* article [10.1016/j.ijhydene.2023.04.084](https://doi.org/10.1016/j.ijhydene.2023.04.084)
reports 2016--2020 HRFF operation, more than 4,500 refueling events and more
than 8,800 kg dispensed. Its public PDF describes the station equipment and
multi-year KPI processing, but no downloadable synchronized station-to-vehicle
logger or data dictionary was located.

The accepted manuscript for the related *Journal of Cleaner Production* paper
[10.1016/j.jclepro.2021.129737](https://doi.org/10.1016/j.jclepro.2021.129737)
is publicly available through [OSTI record 1977265](https://www.osti.gov/biblio/1977265).
It is unusually valuable for a data request: it states that each fueling report
contains one-second dynamic trends including vehicle and hose pressure and
temperature, flow rate, storage pressure, density, APRR, valve states and
booster/chiller commands. The public record still provides the manuscript only;
no CSV/XLSX/SQL export, calibration package or raw-data reuse terms were found.

The [Cal State LA facility page](https://www.calstatela.edu/ecst/h2station) and
the DOE data-program materials corroborate real station provenance and SQL-backed
data acquisition. They are not a numerical holdout. The detailed recheck and
file hashes are stored in
[`cal_state_la_hrff_public_data_recheck_2026_10_04.json`](cal_state_la_hrff_public_data_recheck_2026_10_04.json).

Decision: **HIGH_VALUE_REAL_HRS_CANDIDATES_NO_PUBLIC_RAW_LOGGER_FOUND**. These
sources support a controlled-access request, but they do not close the
independent full-loop validation gate. Use
[`CALSTATE_DATA_REQUEST_DRAFT.md`](CALSTATE_DATA_REQUEST_DRAFT.md), and hash and
quarantine any approved export before reading outcomes or scoring the model.

## 2026-10-04 PRESLHY E3.5 RADAR/KIT metadata recheck

The RADAR/KIT record for the PRESLHY E3.5 liquid-hydrogen release experiments
was rechecked through the [DataCite metadata API](https://api.datacite.org/dois/10.35097/1481)
and the [RADAR landing page](https://radar.kit.edu/radar/en/dataset/nWczysTWjmuzgFKm).
The record is CC BY-SA 4.0, describes 25 elevated releases through 6, 12 and
25.4 mm nozzles at indicated tanker pressures of 1 or 5 barg, and exposes an
11.3 GB `application/x-tar` archive with a published MD5. The archive endpoint
also returned a metadata-only HTTP range response; the large archive was not
downloaded or mined for outcomes.

The record describes pressure, tank pressure, mass flow, near/far thermal,
hydrogen concentration, oxygen depletion, weather and video channels. It is a
strong independent raw-data candidate for liquid-release source,
dispersion/detector and incident-replay checks. Its phase, release geometry and
pressure domain do not match the gaseous station-to-vehicle loop, and it has no
vehicle-fill, cascade, compressor, precooler or dispenser-controller traces.
Therefore it remains consequence-only evidence and does not close the primary
full-loop gate. The exact metadata recheck, range-probe evidence and claim
boundary are frozen in
[`preslhy_e3_5_public_data_recheck_2026_10_04.json`](preslhy_e3_5_public_data_recheck_2026_10_04.json).

## 2026-10-04 HRS aggregate and experiment-summary recheck

The public-data search was extended to four current, high-value sources:

* The DOE/NREL H2IQ Hour presentation reports a real 73 kg heavy-duty fill
  (5.5 to 74.6 MPa, 172.3 g/s average and 483.33 g/s peak) under SAE J2601-5
  MCF-HF-G H70 FM300 T40, but publishes summary values rather than a
  synchronized logger export.
* The Digital.CSIC distribution for on-site HRS operation provides a PDF and
  README under CC BY-NC-ND 4.0; its figures are simulation results, not a
  measured station holdout.
* The 3Emotion/E3S record reports real multi-station 350-bar bus operation from
  operator logs, but only aggregate fill amount, duration, average flow and
  utilization indicators are available publicly.
* The DLR/FCH2RAIL article confirms reference-station and railway-vehicle
  measurements, while the repository exposes no synchronized machine-readable
  trace or reuse terms.
* The ZBT/MetHyTrucks sampling-intercomparison article reports real 35/70 MPa
  test-HRS experiments with logged dispenser and sink-tank channels. Its data
  availability statement offers the raw records by author request, but no
  public machine-readable archive or reuse terms were found. A request draft
  is retained in `research/ZBT_METHYTRUCKS_DATA_REQUEST_DRAFT.md`.
* The CIP 35/70 MPa dispenser study links T3/T4 “CSV” downloads, but direct
  inspection shows they are endpoint summary-table rows; the synchronized
  pressure/temperature/flow histories remain figure-only.

These sources are useful for operating-range and provenance context, but none
meets the frozen eligibility rule for an untouched station-to-vehicle
pressure/temperature/mass-flow holdout. The detailed record is
`research/hrs_public_data_recheck_2026_10_04.json`; the independent full-loop
gate therefore remains open.

## 2026-10-04 Proust residual-structure diagnostic

The frozen Proust 90 MPa local-release result remains negative (0/3 joint
series screens). A post-access diagnostic shows that the fixed global discharge
coefficient of 0.8 underpredicts the nominal 1 mm series while overpredicting
the 2 mm and 3 mm series. The corresponding median local coefficients are
approximately 1.07, 0.69 and 0.62. This pattern is consistent with unresolved
effective aperture, valve-opening and supply-line-loss effects, but it is not a
license to fit diameter-specific coefficients to the holdout. The diagnostic is
stored in
`research/proust_release_postaccess_residual_diagnostic_2026_10_04.json` and
does not change the failed gate.

## 2026-10-04 Schefer transient and pressure residual diagnostic

The two independent Schefer holdouts were rerun from the frozen evaluators.
For the 2006 mass-flow trace, the model's peak is 60.67 g/s versus 68.38 g/s
measured, while the predicted half-peak time is 9.58 s versus 13.35 s. The
model therefore decays too quickly even though its normalized RMSE passes; a
simple aperture multiplier cannot correct both effects. For the 2007 pressure
trace, the initial pressure is reproduced and the half-pressure time is within
6.5%, but the early sub-second drop is not captured and the pointwise median
error is 27.5%.

These patterns point to omitted valve-opening dynamics, line inventory and
distributed resistance rather than a justified global parameter correction.
The post-access diagnostic is stored in
`research/schefer_release_postaccess_residual_diagnostic_2026_10_04.json`; both
validation gates remain failed.

## 2026-10-04 PRESLHY table-domain repair diagnostic

The original PRESLHY E3.1 result retained six high/deep-expansion integration
failures caused by the choked-point search leaving the tabulated isentrope
domain. A bounded fallback was added to the restriction model: it searches for
the lowest admissible pressure on the same tabulated isentrope and never
extrapolates. A post-access replay then produced 16/22 joint passes (72.7%),
up from 11/22 (50.0%).

Because the repair was made after the original numerical outcomes were read,
the 72.7% result is explicitly exploratory and does not reopen the failed
PRESLHY gate. The repaired implementation must be frozen and evaluated on a
new untouched campaign. Full details are in
`research/preslhy_table_boundary_repair_diagnostic_2026_10_04.json`.

## 2026-10-04 GTI California station performance report follow-up

The public [GTI Hydrogen Station Performance Evaluation final report](https://doi.org/10.2172/1824631)
documents a custom data-acquisition campaign deployed at five California
hydrogen stations over approximately four years. The report lists the
high-value channels needed for a controlled-access check, including vehicle
starting pressure and temperature, ending vehicle pressure, mass dispensed,
compressor flow, storage-bank pressure, station temperatures, fill mode and
maintenance context. The public OSTI artifact is only a nine-page report PDF;
its retrieved SHA-256 is recorded in
`research/gti_hydrogen_station_public_data_recheck_2026_10_04.json`.

No machine-readable logger export, channel dictionary, calibration/uncertainty
package or raw-data reuse terms were found in the public record. The source is
therefore classified as **REQUEST_DATA_HIGH_VALUE_REAL_STATION_CANDIDATE** and
does not close the independent full-loop gate. A data request should seek a
de-identified station-by-fill export with common timestamps, vehicle or
receptacle pressure and temperature, mass flow or transferred mass,
storage/cascade state, protocol mode, quality flags, aborted-fill labels and
permission to publish derived metrics. Any approved files must be hashed and
quarantined before numerical outcomes are inspected.


## 2026-10-04 Cal State LA and SunHydro follow-up

The follow-up register now includes two credible acquisition routes that remain outside the numerical holdout gate:

- Cal State LA HRFF cascade/directly-pressurized experiments (DOI [10.3390/en16155749](https://doi.org/10.3390/en16155749)) provide three real heavy-duty events and endpoint/energy comparisons. The public article has no synchronized logger export or reuse terms. The request draft is [`research/CALSTATE_CASCADE_EXPERIMENT_DATA_REQUEST_DRAFT.md`](CALSTATE_CASCADE_EXPERIMENT_DATA_REQUEST_DRAFT.md).
- DOE SunHydro reports ([final report](https://www.osti.gov/servlets/purl/1783792), [2015 AMR](https://www.hydrogen.energy.gov/docs/hydrogenprogramlibraries/pdfs/review15/tv020_moulthrop_2015_o.pdf)) document real station data exported to the NREL Hydrogen Secure Data Center. The HSDC overview ([NREL](https://www.nrel.gov/docs/fy12osti/54860.pdf)) states detailed partner data are controlled; public aggregate products are not synchronized station-to-vehicle raw traces. The request draft is [`research/SUNHYDRO_DATA_REQUEST_DRAFT.md`](SUNHYDRO_DATA_REQUEST_DRAFT.md).

These additions improve provenance and acquisition coverage only. The independent full-loop gate remains open until a de-identified synchronized export, immutable hash, written reuse terms and frozen no-fitting scoring protocol are available.

## 2026-10-04 Figshare API file-level recheck

The public Figshare API was queried for hydrogen refuelling, fueling-station,
dispenser, vehicle-fueling, pressure/temperature/flow and tank-filling terms.
The most plausible station-performance record exposes one PDF and is marked
**All rights reserved**; it does not expose a synchronized logger archive or
reuse terms. Other inspected hits were a residential CFD thesis, cryogenic
spray work and a numerical explosion paper with no downloadable data files.

The exact API responses and file-level classifications are frozen in
[`research/figshare_h2_hrs_recheck_2026_10_04.json`](figshare_h2_hrs_recheck_2026_10_04.json).
None contains the required licensed station-to-vehicle pressure, mass-flow and
preferably temperature channels on a common time base with initial conditions
and protocol metadata. This discovery recheck therefore does not add a new
independent holdout or change the full-loop gate.

The 2020 Chinese 35/70 MPa dispenser performance article was separately
checked at file level. Its four linked CSV ZIPs contain only initial/final
summary tables, while the article reports a 70 MPa fill endpoint (276 s,
5.08 kg, 81.6 MPa, 65.8 °C and 36 g/s peak). Since no synchronized raw trace
or explicit reuse licence is supplied, this remains contextual evidence and
not a full-loop holdout. The file hashes and decision are recorded in
[`research/chinese_hrs_performance_article_recheck_2026_10_04.json`](chinese_hrs_performance_article_recheck_2026_10_04.json).

The Cal State LA HRFF public-data route was also inspected. The 2017 paper
states that a raw per-fill data set was used, and the 2021 paper describes a
larger back-to-back fueling data set, but neither public artifact exposes a
synchronized logger archive or written reuse terms. This is now a documented
high-value data-request lead, not a holdout. Details are in
[`research/calstate_la_public_data_leads_2026_10_04.json`](calstate_la_public_data_leads_2026_10_04.json).
The 2017 PDF itself was inspected and contains no embedded files or external
links; the cited raw dataset therefore requires a custodian export.

## 2026-10-04 Additional primary-source full-loop search refresh

An additional search checked primary pages and public manuscripts for five
frequently cited routes:

* The NREL HITRF liner-temperature experiment (Kuroki et al., DOI
  [10.1002/ente.202300239](https://doi.org/10.1002/ente.202300239)) reports a
  108 L vehicle surrogate, a 6.3 to 73.0 MPa fill over 186 s and multiple
  temperature channels. The public OSTI manuscript states that research data
  are not shared, so the source remains a tank-thermal data-request lead.
* The [National Fuel Cell Technology Evaluation Center](https://www.nlr.gov/hydrogen/nfctec)
  confirms that detailed partner station data are stored in a secured center
  and that public products are aggregated. It is a credible custodian route,
  not an open raw holdout.
* The official [H2FillS page](https://www.nrel.gov/hydrogen/h2fills) documents
  full-station simulation and empirical fueling validation, but the package is
  registration-gated and no independent measured archive is exposed on the
  public page.
* Ramea et al. (DOI
  [10.1016/j.ijhydene.2019.05.053](https://doi.org/10.1016/j.ijhydene.2019.05.053))
  states that an hourly California station-capacity dataset was released. No
  working downloadable archive was located in this recheck; even if recovered,
  hourly capacity lacks vehicle pressure, temperature and mass-flow channels.
* The [NIST Transient Flow Facility](https://www.nist.gov/programs-projects/transient-flow-facility)
  provides a high-value metrology request route for dispenser transients, but
  its public page does not publish a synchronized station-to-vehicle logger
  export.

The file-level classifications and claim boundaries are frozen in
`research/public_full_loop_search_refresh_2026_10_04.json`. None of these
sources satisfies the untouched full-loop eligibility rule, so the numerical
gate remains open and no IJHE-level validation claim is permitted.

## 2026-10-04 MC Default source-boundary identifiability diagnostic

The frozen MC Default holdout also exposes `source_pressure_3` endpoints, but
the public protocol does not identify the connected storage volume, bank
dispatch, regulator behavior or source-channel temperature. To separate that
boundary uncertainty from the vehicle model, the diagnostic
[`scripts/diagnose_mc_default_source_boundary.py`](../scripts/diagnose_mc_default_source_boundary.py)
was run against all eight frozen cases. It uses only the tabulated hydrogen
density relation, a 298.15 K isothermal mass balance and binary pressure
inversion; it does not fit a volume, modify the production model or reopen the
holdout.

The resulting artifact is
[`research/mc_default_source_boundary_identifiability_2026_10_04.json`](mc_default_source_boundary_identifiability_2026_10_04.json).
The observed source-pressure drops are 2.255--4.914 MPa for 3.984--8.738 kg
transferred. If that channel were a single 0.35 m³ bank starting at 90 MPa,
the same simplified estimate would predict 30.734--58.621 MPa drops. Under the
conditional isothermal interpretation, the observed endpoints imply effective
constant volumes of 2.737--8.697 m³. These values are diagnostics, not fitted
parameters: the channel may represent a larger connected inventory, regulated
upstream boundary, multiple-bank dispatch or different thermal behavior.

This finding explains why the current full-loop comparison cannot identify an
internal bank state from the public protocol alone. It does not rescue the
failed external screen. A future protocol must either provide measured source
pressure/temperature as a declared boundary trace or obtain bank topology and
valve-state logs before scoring internal-bank pressure.

The corresponding vehicle-side sensitivity was run with the frozen vehicle and
dispenser parameters, the published `source_pressure_3_mpa` trace as the
upstream boundary, the measured inlet-temperature profile and the published
protocol pressure reference. The result is recorded in
[`research/mc_default_frozen_boundary_vehicle_diagnostic_2026_10_04.json`](mc_default_frozen_boundary_vehicle_diagnostic_2026_10_04.json).
Only 1 of 8 already-consumed cases passed; aggregate pressure RMSE was 5.850
MPa, temperature RMSE 17.029 °C and SOC RMSE 7.370 percentage points. This
shows that the source-boundary mismatch is a genuine confounder but not the
sole cause of the full-loop discrepancy. Because the run uses outcome-known
traces and a physics-only 200 °C controller limit, it remains a development
diagnostic and does not change the external-validation or goal-completion
decision.

## 2026-10-04 H2Protocol upstream-pressure profile screen

The H2Protocol workbooks expose a `Psupply` channel in addition to the
vehicle-side pressure, temperature, SOC and mass-flow channels. The baseline
J2601 runner deliberately uses a constant 90 MPa upstream boundary, so a
small, outcome-known screen was added to test whether that declared boundary
is responsible for part of the residual. The runner is
[`scripts/run_h2protocol_source_boundary_screen.py`](../scripts/run_h2protocol_source_boundary_screen.py)
and the machine-readable result is
[`research/h2protocol_source_boundary_screen_2026_10_04.json`](h2protocol_source_boundary_screen_2026_10_04.json).

For three already-consumed cases (H2P-L01, H2P-L06 and H2P-L10), forcing the
published `Psupply` trace reduced mean pressure RMSE from 21.28 MPa to 4.16
MPa and produced two screening passes under the declared physics-only
temperature-stop sensitivity. This is evidence that the upstream boundary is
material; it is not a new independent holdout, because the same H2Protocol
source family is already present in the frozen development and MC evaluation.
The result therefore does not change the external-validation gate or permit
an IJHE-level full-loop claim. A future independent archive must include the
same source-pressure and source-temperature boundary channels, or the station
bank topology and valve-state log needed to reconstruct them.

## 2026-10-05 public-data follow-up recheck

The follow-up search inspected four additional public routes and preserved
their exclusion decisions in
[`research/public_full_loop_search_recheck_2026_10_05.json`](public_full_loop_search_recheck_2026_10_05.json):

* Mendeley Data DOI `10.17632/mnjs94yzfc.1` is openly licensed, but its
  description identifies model and simulation outputs rather than measured
  station observations.
* The European H2-Stations export API is CC BY 4.0 and useful for station
  context, availability, usage, storage and pricing, but it does not expose
  synchronized pressure-temperature-mass-flow fueling traces.
* The University of Texas report DOI `10.26153/tsw/64797` is an open
  technical report about California deployment lessons, without a
  machine-readable station logger archive.
* The public ZBT HRS-Modell page describes a simulator and developer-side
  validation, not an independently released measured holdout.

None meets the frozen full-loop eligibility rule. These sources are retained
as contextual or acquisition leads only; no gate is promoted and no model
parameter is changed.

## 2026-10-05 real-station operational benchmark recheck

The Cal State LA HRFF multi-year study (DOI
`10.1016/j.ijhydene.2023.04.084`) and the UCI NFCRC early-commercial-operation
study (DOI `10.1016/j.ijhydene.2020.08.251`) are genuine field-operation
sources and are stronger face-validity references than a simulator-only
dataset. The Cal State LA paper describes more than 4,500 refuelling events,
8,800 kg dispensed, five SQL logging databases and separate storage,
compressor, dispensing and station reports. The UCI paper reports multi-year
station performance and fill profiles. Neither public record releases the
individual synchronized pressure-temperature-mass-flow rows needed for the
full-loop holdout.

NREL's retail composite products and the European H2-Stations API add useful
population-level operating context, but remain aggregate or availability/
usage/storage products. They cannot replace a vehicle-side logger. The
source-by-source decision, observed fields and reuse boundary are frozen in
[`research/public_operational_benchmark_recheck_2026_10_05.json`](public_operational_benchmark_recheck_2026_10_05.json).

The Chinese field study [10.19799/j.cnki.2095-4239.2020.0049](https://doi.org/10.19799/j.cnki.2095-4239.2020.0049)
adds two real 35/70 MPa dispenser tests. Its public page exposes small table
CSV files and reports vehicle pressure, temperature, mass, elapsed time and a
70 MPa peak flow of 36 g/s. It does not expose the synchronized raw trace or an
explicit reuse licence, so it is recorded as a table-only face-validity and
data-request lead rather than a full-loop holdout.

The Cal State LA HRFF comparison [10.3390/en16155749](https://doi.org/10.3390/en16155749)
adds three real experiments contrasting booster-driven and cascade refueling.
The paper reports pressure, mass flow, nozzle temperature and chiller-power
trends, including a 5 s leak-check pause and a 1.6 kg comparison window. The
public article provides figures and aggregate values, but not a reusable
synchronized logger archive, so it remains a figure-only data-request lead.

The FCH2RAIL demonstrator study [10.1016/j.ijhydene.2025.04.040](https://doi.org/10.1016/j.ijhydene.2025.04.040)
is a particularly relevant IJHE precedent: the project recorded train-module
pressure/temperature together with dispenser pressure, temperature and mass
flow. The open paper shows an exemplary synchronized refueling trace, but no
raw row archive or reuse terms are released with it. It is therefore retained
as an independent face-validity and acquisition lead, not a full-loop holdout.

This recheck adds a prioritized data-request route without changing the
production model or treating field summaries as validation. Until a custodian
provides a de-identified synchronized export with reuse permission, the
full-loop external gate and the full IJHE objective remain open.

## 2026-10-05 ELVHYS consequence archive file audit

The [ELVHYS 4.2 Dataverse record](https://dataverse.no/dataset.xhtml?persistentId=doi:10.18710/JXJP0H) (DOI [10.18710/JXJP0H](https://doi.org/10.18710/JXJP0H)) was rechecked at the API and file level. It declares CC0 1.0 and exposes 198 files for 48 cryogenic-hydrogen transfer-connection-space tests. The archive has synchronized concentration, release/nozzle pressure, enclosure pressure, temperature, ventilation and ignition/overpressure measurements, so it is useful consequence-component evidence. A sample manifest, headers, byte counts and hashes are retained in [`elvhys_dataverse_metadata_audit_2026_10_05.json`](elvhys_dataverse_metadata_audit_2026_10_05.json).

The metadata CSV dates the experiments 5–28 November 2025, while the README says “Autumn 2024”. The discrepancy is recorded for custodian clarification. The source remains **component-only**: it is cryogenic transfer-space evidence, not a gaseous H70 station-to-vehicle fueling archive, and therefore does not change the full-loop gate or goal-completion rule.

## 2026-10-05 KGS real-station data access recheck

The KGS-linked thermofluidic study reports six real HRS fueling scenarios with vehicle pressure, vehicle temperature and mass flow. The published article is [10.1007/s11814-025-00551-9](https://doi.org/10.1007/s11814-025-00551-9), with open preprint [10.21203/rs.3.rs-6248350/v1](https://doi.org/10.21203/rs.3.rs-6248350/v1). Its cited Google Drive code folder redirected an anonymous request to Google sign-in and yielded no files. The exact access result is recorded in [`kgs_hrs_code_access_recheck_2026_10_05.json`](kgs_hrs_code_access_recheck_2026_10_05.json).

This is a high-value real-station acquisition lead, but not a public raw holdout. The six synchronized scenarios, channel dictionary, calibration metadata, protocol states and written reuse terms still need to be obtained and frozen before numerical validation.

The UPC/Digital.CSIC supplementary artifact for the on-site HRS modelling paper
(DOI [10.1016/j.ijhydene.2023.08.192](https://doi.org/10.1016/j.ijhydene.2023.08.192))
was also checked. It is openly reachable and useful for comparing operating
strategy diagrams and modelled compressor/energy plots, but it is a simulation
supplement rather than a measured station logger archive. It therefore remains
explicitly excluded from the physical holdout and cannot be used for parameter
fitting. The exclusion is recorded alongside the five-candidate recheck in
[`public_operational_benchmark_recheck_2026_10_05.json`](public_operational_benchmark_recheck_2026_10_05.json).


## 2026-10-05 Air Liquide HRS volume-estimation experiment recheck

The open-access Hydrogen Safety article [10.58895/hysafe.59](https://doi.org/10.58895/hysafe.59) reports fourteen real refueling tests at the Air Liquide Innovation Campus Delaware: eight tests on a 243.6 L/700 bar Type IV tank and six on a 1520 L/250 bar Type IV tank. The paper describes dispenser pressure/temperature, mass flow, tank pressure and tank-temperature measurements, so it is a high-value physical face-validity and acquisition lead.

The public PDF was downloaded and hash recorded in [`research/hysafe59_data_access_recheck_2026_10_05.json`](hysafe59_data_access_recheck_2026_10_05.json). Its data-availability statement says that the data are available only within the manuscript and associated figures and that no additional external datasets are publicly available. Therefore it is not an eligible machine-readable synchronized holdout; request the logger export and written reuse terms before any confirmatory use.

## 2026-10-05 Ramea capacity archive recovered

A file-level inspection located the public [Ramea hydrogen-station capacity repository](https://github.com/kramea/h2_station_capacity_data), associated with [DOI 10.1016/j.ijhydene.2019.05.053](https://doi.org/10.1016/j.ijhydene.2019.05.053). It contains 2,563 CSV files for 36 California stations from 2018-09-27 through 2018-12-18, with `Time`, `H35`, and `H70` capacity indicators at approximately 30-minute intervals. The repository has no explicit license field and no vehicle/receptacle pressure, temperature, mass-flow or protocol trace. It is therefore recorded as aggregate capacity/demand context only in [`ramea_station_capacity_repository_boundary_2026_10_05.json`](ramea_station_capacity_repository_boundary_2026_10_05.json); the independent full-loop validation gate remains open.

## 2026-10-05 NBSDC Winter Olympics HRS access recheck

The National Basic Science Data Center (NBSDC) catalog was rechecked through
its public metadata and file-tree APIs for CSTR
`16666.11.nbsdc.aI3fJrzX`. The catalog still exposes three operational
workbooks—transaction data, dispenser/nozzle data and compressor data—with a
declared approval-required sharing range. Direct probes of all three workbook
IDs returned the portal's application-required response; no raw row was
inspected. The current response bodies, file names, sizes and hashes are
recorded in
[`research/nbsdc_winter_olympics_access_recheck_2026_10_05.json`](nbsdc_winter_olympics_access_recheck_2026_10_05.json).

This is a stronger, current acquisition lead because the file inventory and
access boundary are independently reproducible, but it is not an open
validation holdout. The full-loop gate stays closed until the custodian grants
access, provides the channel dictionary and time-base/calibration metadata,
and confirms reuse terms for derived results and journal publication.

## 2026-10-05 DataverseNO hydrogen-explosion consequence archives

Two newly released DataverseNO records are openly reusable under CC0 1.0, and
one earlier CC BY 4.0 record was rechecked at the same API, providing useful
independent consequence-component evidence:

* [10.18710/WSKBIJ](https://doi.org/10.18710/WSKBIJ) contains 2024–2025
  large-scale open-atmosphere delayed-ignition releases. The API manifest has
  59 files: 52 text traces, six high-speed-camera/archive files and a summary
  workbook. The README identifies reservoir and upstream pressure, mass flow
  for experiments 1–27, four transient explosion-pressure sensors and camera
  trigger synchronisation. Ambient weather was not documented.
* [10.18710/X044QK](https://doi.org/10.18710/X044QK) contains 40 laboratory
  delayed-ignition jet experiments. The API manifest has 47 files: 39 large
  CSV traces, six video archives, a README and a summary workbook. The
  workbook reports pressure and mass-flow summaries, obstacle spacing and
  ignition delay; the README identifies four high-frequency pressure sensors
  and an upstream pressure transmitter.
* [10.23642/USN.17934047](https://doi.org/10.23642/USN.17934047) is the
  ignited-release companion archive (CC BY 4.0). Its file-handling guide and
  a hash-checked sample MAT file expose synchronized SIGMA time, mass flow,
  Coriolis pressure, four thermocouples and GEN3i overpressure channels. The
  sample is a channel/time-base smoke test only; it is not a model comparison.

The file counts, CC0 declarations, summary-workbook hashes and coverage are
fixed in
[`research/dataverse_hydrogen_explosion_dataset_inventory_2026_10_05.json`](dataverse_hydrogen_explosion_dataset_inventory_2026_10_05.json),
with a human-readable report in
[`research/DATAVERSE_HYDROGEN_EXPLOSION_DATASET_INVENTORY_2026_10_05.md`](DATAVERSE_HYDROGEN_EXPLOSION_DATASET_INVENTORY_2026_10_05.md).
Neither record is a synchronized gaseous-H70 station-to-vehicle fueling loop;
the inventory is not a model comparison and cannot close the full-loop gate or
the SAGA effectiveness gate. A consequence-model protocol must be frozen
before raw traces are used for any confirmatory score.

## 2026-10-05 Grune/Zenodo archive access recheck

The complete seven-file archive for [10.5281/zenodo.4668554](https://doi.org/10.5281/zenodo.4668554)
was rechecked against the Zenodo API byte counts and MD5 identities. The five
XLSX files are spatial concentration/flow-field summaries, the PDF is source
documentation, and the ZIP is an Inventor CAD project. No file contains a
trace-specific measured reservoir-pressure time series or a half-pressure
crossing. The negative result and file hashes are retained in
[`grune_2014_archive_access_recheck_2026_10_05.json`](grune_2014_archive_access_recheck_2026_10_05.json)
and [`GRUNE_2014_ARCHIVE_ACCESS_RECHECK_2026_10_05.md`](GRUNE_2014_ARCHIVE_ACCESS_RECHECK_2026_10_05.md).
The Grune pressure-decay gate therefore remains pending and no validation
claim or model parameter was changed.
