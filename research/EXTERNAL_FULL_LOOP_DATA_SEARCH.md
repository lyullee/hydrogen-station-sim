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

The diagnostic output also computes an EOS-equivalent volume from the measured
mass, internal pressure and internal temperature. Across the seven tanks the
median is 0.24388 m³ versus 0.26780 m³ for the frozen effective-volume
assumption (ratio 0.91071). This is retained in
`data/public_validation/results/nrel_h2fills_hdvs_typeiv/validation.json` as
`geometry_diagnostic.status=diagnostic_only_no_parameter_update`. It explains
why a larger pressure error is plausible without silently fitting the external
screen; it is not a vessel-geometry identification or a validation pass.

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

The MetHyTrucks HySaM record is a genuine open raw-data lead, but its scope is
hydrogen sampling-system metrology rather than a vehicle refuelling event:
<https://zenodo.org/records/20590842>. The three CC BY 4.0 XLSX files have
sub-second time-of-day samples and pressure/temperature/flow-like channels, but
no vehicle or receptacle pressure, tank capacity, vehicle temperature, initial
state or refuelling-protocol metadata. It is therefore retained for signal
handling and calibration checks only and is not promoted to the HRS full-loop
holdout.

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
