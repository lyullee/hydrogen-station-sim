# Full-loop HRS raw-data request package (2026-10-05)

The current audit cannot close `full_loop_external_validation` because the public
records reviewed so far expose plots, aggregates or component traces rather than
an independently reusable, synchronized station-to-vehicle logger archive. This
package is a ready-to-send request specification for a data custodian. It does
not assert that any custodian has granted access.

## Minimum dataset required

Request one or more complete refuelling events with a common timestamp or elapsed
time base and the following channels, in their native units:

* vehicle or receptacle pressure and temperature;
* station/dispenser pressure and delivered-gas temperature;
* mass flow and cumulative transferred mass;
* source/cascade-bank pressure and selected-bank or valve state;
* precooler outlet temperature and compressor/PCV state;
* start/stop, leak-check, vent, fault and ESD transitions;
* tank geometry and configuration: exact internal volume, vessel count, nominal
  working pressure, liner/shell type and gas-temperature sensor location;
* tank initial state, ambient conditions and protocol inputs;
* sensor calibration, sampling period, missing-value convention and uncertainty.

The event export must retain the original sample clock and a row-level event
identifier. Derived or manually digitised curves are insufficient for the primary
holdout.

## Two-stage intake that limits custodian burden

Request the material in two stages rather than asking for the full historian at
once:

1. **Schema pilot (one event or metadata-only):** confirm the generic role map,
   units, clock alignment, protocol phase, stop reason and ESD semantics. If one
   de-identified event is supplied, use it only to test channel joining and the
   quality screen; do not fit parameters or report a validation score from it.
2. **Frozen evaluation export (at least eight disjoint events):** after the
   model commit, inclusion rules and scoring code are frozen, provide the
   remaining events through the same controlled channel. Keep the raw rows with
   the custodian and return only event-level metrics, aggregate uncertainty and
   a reviewer hash/package.

This staged route is intentionally small: the current local archive already
supports station-side pressure, cascade and recharge checks, so the missing
information is the synchronized receiving-vessel boundary rather than a larger
station historian.

## Smaller first contribution when full access is difficult

If an eight-event frozen holdout cannot be released immediately, request a
three-event **minimum useful component bundle** first. It only needs a common
clock, station or dispenser pressure, delivered-gas or boundary temperature,
mass flow (or transferred mass), and protocol start/stop phase. Vehicle pressure
and temperature, selected-bank state, and precooler outlet temperature are
preferred but may follow in a second export.

This smaller bundle can support station-to-dispenser boundary replay, operating
range and protocol face-validity checks, and channel-quality screening. It must
not be presented as full station-to-vehicle validation, safety-distance
validation, SAGA-effectiveness evidence, or a basis for runtime parameter fitting
without a frozen protocol. The existing eight-event requirement remains in force
for the full-loop IJHE gate.

## Rights and provenance request

Ask the custodian to confirm in writing:

1. that the de-identified rows may be analysed and redistributed as derived
   metrics;
2. that the derived metrics may be included in an IJHE manuscript and deposited
   with reproducibility materials;
3. the source version, file hashes, data dictionary and calibration records; and
4. any restrictions on sharing raw rows with independent reviewers.

If raw redistribution is prohibited, request a custodian-run hash-locked
evaluation service or an embargoed reviewer package with the same scoring API.

## Candidate custodians and public lead records

| Custodian route | Public lead | Requested scope |
| --- | --- | --- |
| NLR/NREL HITRF | [HITRF programme](https://www.nrel.gov/hydrogen/hitrf-animation) | H70/H35 station, dispenser, protocol and vehicle logger rows |
| Cal State LA HRFF | [HRFF operation](https://www.calstatela.edu/ecst/h2station/operation) | Light-duty station event logs and vehicle pressure/temperature/mass flow |
| KGS/Oh study custodians | [Published study](https://doi.org/10.1007/s11814-025-00551-9) | Six real-HRS scenarios reported with vehicle pressure, temperature and mass flow |
| FCH2RAIL/DLR | [Repository record](https://elib.dlr.de/213625/) | Railway HRS and vehicle synchronized pressure, temperature and flow |
| JRC GasTeF | [JRC record](https://publications.jrc.ec.europa.eu/repository/handle/JRC76380) | Fast-fill tank and gas-path traces with calibration metadata |
| CARB/HyStEP | [In-use study](https://ww2.arb.ca.gov/sites/default/files/2024-12/Existing%20Light-Duty%20Hydrogen%20Refueling%20Stations%20In-Use%20Study%20Report%20ADA%20AL.pdf) | Station test logs and Appendix A workbook |
| PRHYDE/ZBT/Nikola | [PRHYDE project](https://lbst.de/prhyde/) | Instrumented heavy-duty fill logs and controller/protocol states |

## Evaluation procedure after access

Before opening numerical outcomes, freeze the inclusion criteria, channel map,
model commit and scoring code. Keep a custodian-independent checksum manifest.
Evaluate every eligible event with pressure, temperature and final-SOC errors,
coverage, stop reason and mass closure. Report event-level results and bootstrap
intervals; do not tune parameters on the holdout. A passing result must still be
reported as station-to-vehicle validation for the observed envelope, not as proof
of field-wide safety or autonomous emergency-response effectiveness.

The package is linked from the IJHE audit as an acquisition aid. It does not
change the current gate status or permit goal completion.
