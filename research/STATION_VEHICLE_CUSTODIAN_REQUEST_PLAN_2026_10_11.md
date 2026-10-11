# Station-to-vehicle custodian request plan

This is a prepared request plan only. No message is sent automatically.

## Priority custodians

1. NREL HITRF/NFCTEC: de-identified light- and heavy-duty fueling traces
   underlying the public demonstrations and H2IQ charts.
2. The NBS data-centre custodian for the 70 MPa hydrogenation-port test
   collection: request the machine-readable files, access terms and a channel
   dictionary through the approved registration route.
3. JRC/GasTeF or the original test custodians: request the raw reference
   fast-fill traces described by JRC76380.
4. The custodians of the published 35/70 MPa dispenser experiments and recent
   Type-IV HRS campaigns: request the original logger export rather than
   digitized figures.

## Minimum admissible package

The package is eligible only if it contains at least three independent events
with a common elapsed-time or timestamp axis and units for:

- station/controller or storage-bank state and pressure;
- dispenser, hose, nozzle or receptacle pressure and temperature;
- vehicle tank pressure, gas temperature, delivered mass or cumulative mass;
- protocol phase, target pressure, temperature category and vehicle capacity;
- quality flags, aborted fills, alarms, ESD/interlock states and clock rules.

The custodian must state whether the de-identified rows and derived error
metrics may be published. A figure, aggregate statistic, simulation output or
file that requires an account but has no documented reuse terms is retained as
context or a request lead only.

## Intake controls

Before opening outcomes, the project will record the source identifier,
custodian permission, file hashes, units and channel mapping, freeze the
scoring protocol and declare the model commit. The split will be by event, not
by randomly sampled rows. Missing station-controller or vehicle-side channels
will keep the package outside the full-loop gate.

The current scope remains station-side/component validation until an admissible
package is received. No runtime parameter is changed from a summary report or
digitized figure.
