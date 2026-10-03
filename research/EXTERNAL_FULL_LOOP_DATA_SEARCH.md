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
3. Send equivalent non-publishing requests to JRC GasTeF, PRHYDE data custodians
   and the Cal State LA authors. The JRC draft is
   `research/JRC_GASTEF_DATA_REQUEST_DRAFT.md` and
   asks for the database described by the 2014 paper, including internal
   thermocouple, tank pressure, inlet pressure, inlet temperature, flow and
   test metadata, with permission to publish derived metrics.
4. On receipt, hash and quarantine the files before opening outcomes; freeze
   case eligibility and the corrected model commit in a new protocol manifest.
5. Evaluate the frozen model once. Retain every eligible failure and do not use
   the new outcomes for tuning.
6. If CARB, JRC and Cal State LA cannot release the traces, make an equivalent
   request to NIST. Do not substitute graph digitisation for raw data in the
   primary full-loop claim.

## Current conclusion

No newly located public source currently satisfies the full-loop eligibility
rule. The gate therefore remains **PENDING/FAIL**, and no broad station-model
validation claim is permitted. This search record prevents unavailable plots or
aggregate products from being silently relabelled as independent validation.
