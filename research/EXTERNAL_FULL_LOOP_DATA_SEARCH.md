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
| NREL H2FillS | Official page says the model was validated with empirical fueling datasets. | **Not available.** The empirical validation traces are not offered as a public download on the product page. Simulator output would not be independent experimental evidence. |
| NREL 2024 HITRF reliability/fueling report | Table 4 gives sample HITRF fill summaries with timestamp, amount, rate, start/end pressure, dispensing temperature and dispensing pressure. | **Report table only.** The PDF does not provide a common-time-base raw trace, so it is useful field context and a lead for a data request, not an untouched full-loop validation set. |
| DOE/NREL H2IQ Hour 2024 HD fast-flow experiment | 3/12/2024 HITRF test reports 73 kg in 423.5 s, 358.9 s fueling time, 172.3 g/s average, 483.33 g/s peak, 5.5→74.6 MPa, APRR 9.9 MPa/min under SAE J2601-5 MCF-HF-G H70 FM300 T40. | **Plot/summary only.** The presentation contains charts and aggregate endpoints but no machine-readable common-time-base trace; use for face-validity and operating-range checks only. |
| NREL HITRF 36 L experiment, Kuroki et al., DOI 10.1002/ente.202300239 | Open article describes a HITRF fill from 6.3 to 73.0 MPa in 186 s with inlet pressure, receptacle-exit temperature, internal hydrogen temperature and liner measurements. | **Request data.** The paper's data-availability statement says research data are not shared; figures and boundary conditions alone cannot close the time-series gate. |
| NREL/NatLabRockies HDTADA | Public repository contains the analysis-tool installers and licence. | **Not available.** No sample raw fueling traces are distributed in the repository. |
| NREL retail-station composite data products | Public aggregate statistics and histograms for station operation. | **Context only.** No fill-level pressure/temperature/flow time series. |
| NIST Transient Flow Facility | Official page documents 100 ms or faster pressure, temperature and transient-flow measurement capability. | **Request data.** No public experiment archive was identified from the project page. |
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
| FCH2RAIL reference HRS and rail vehicle, Wieser et al., DOI 10.1016/j.ijhydene.2025.04.040 | Open-access paper uses real HRS and vehicle measurements for model validation and shows pressure, temperature and mass-flow behavior. | **Request data.** The DLR record exposes the paper PDF but no synchronized machine-readable measurement archive. |
| 3Emotion operational HRS data, Caponi et al., DOI 10.1051/e3sconf/202233406008 | Multi-year operator logs from four 350-bar bus stations, reported as fill amount, duration, average flow, utilization and availability. | **Aggregate context only.** No synchronized pressure, temperature and mass-flow trace is public. |
| 3Emotion four-year operational analysis, Caponi et al., DOI 10.1016/j.ijhydene.2022.10.093 | Peer-reviewed analysis of four years of operator logbooks for five 350-bar stations and 34 buses; reports 14.62 kg/fill and 10.28 min overall means plus demand, utilization and availability. | **Aggregate operating-range benchmark only.** The article does not expose synchronized pressure/temperature/flow files or a machine-readable supplementary archive. |
| HYTRANSFER public GasTeF filling-campaign report | Public report describes 13 filling and 5 emptying tests and 18 recorded-data files with pressure, temperature, gas-path and flow measurements. | **Request files.** The public PDF does not expose the 18 machine-readable files or reuse terms; request them before treating the campaign as an untouched holdout. |
| Beijing Winter Olympics HRS Operational Data List, CSTR 16666.11.nbsdc.aI3fJrzX | National Basic Science Data Center metadata reports 2022 HRS data with dispenser monitoring, fueling records and compressor monitoring; four files, 10.22 MB. | **Access request.** The machine-readable record is marked “approval required” and the file-tree endpoint returns no files without authorization. It is a high-value candidate, not an available holdout. |
| Hungarian HRS digital-twin validation, Hasulyó, DOI 10.32604/ee.2026.081099 | Open-access paper reports operational pressure, temperature, mass-flow and refueling comparisons from an existing Hungarian HRS. | **Request data.** The paper's data-availability statement says supporting data are unavailable because of participant consent and legal restrictions. |

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
6. Send the NREL HITRF/NFCTEC request in
   `research/NREL_HITRF_DATA_REQUEST_DRAFT.md` for de-identified full-station
   traces or an approved access route. NREL's public composite products remain
   aggregate context only.
7. Send the Hungarian HRS request in
   `research/HUNGARIAN_HRS_DATA_REQUEST_DRAFT.md` to the study author or data
   custodian, subject to their consent and legal restrictions.
8. Send the NBSDC request in `research/NBSDC_HRS_DATA_REQUEST_DRAFT.md` to the
   National Basic Science Data Center/Tsinghua data custodian. Request the four
   files named by the catalog, field dictionaries, timestamps, units, quality
   flags, de-identification terms and permission to publish derived metrics.
9. On receipt, hash and quarantine the files before opening outcomes; freeze
   case eligibility and the corrected model commit in a new protocol manifest.
10. Evaluate the frozen model once. Retain every eligible failure and do not use
   the new outcomes for tuning.
11. If CARB, JRC, Cal State LA, Empa, FCH2RAIL, NREL HITRF, the Hungarian HRS study and
   NBSDC cannot release the traces, make an equivalent
   request to NIST. Do not substitute graph digitisation for raw data in the
   primary full-loop claim.

## Current conclusion

No newly located public source currently satisfies the full-loop eligibility
rule. The gate therefore remains **PENDING/FAIL**, and no broad station-model
validation claim is permitted. This search record prevents unavailable plots or
aggregate products from being silently relabelled as independent validation.

The machine-readable counterpart is
`research/external_full_loop_data_search.json`; its `review_log_2026_10_03`
records the URLs and the same access decisions used by the readiness audit.
