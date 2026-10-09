# Data-scarcity validation strategy (2026-10-10)

Real hydrogen-refuelling datasets are difficult to obtain in the exact form
needed for an independent digital-twin claim. The limiting factor is not the
number of rows in the local archive. It is the absence of an attested,
common-time vehicle-side contract that can be used without exposing a site,
operator, manufacturer or date.

## What is already usable

The privacy-bounded local inventory contains 33 CSV files (4.749 GiB),
56,854,143 rows after duplicate removal, and 33 station-side files. It already
supports:

- 16,770 ordered high-bank pressure cycles and 11,770 paired medium/high
  pressure episodes;
- 1,418 short-horizon station-pressure forecast cases;
- 733 conditional recharge-flow episodes;
- station-side dynamic and longitudinal validation with the declared pressure
  semantics.

These records are used for station pressure/cascade behaviour, recharge
restart screening, trend displays and bounded operator guidance. They are not
silently promoted to vehicle or full-loop validation. The inventory found no
header-level vehicle/dispenser candidate, and vehicle-side channel attestation
remains zero.

The public HydDown archive now also contributes a bounded Type-I filling
thermal diagnostic: three common-time cases are reproduced with aggregate
temperature errors of 6.36, 9.94 and 11.75 K. The source arrays are not copied
into the repository. This evidence is available to the LLM for vessel thermal
comparisons, but it does not change runtime parameters or close the
station-to-vehicle gate.

The private local archive was rechecked on 2026-10-10 without retaining source
identity or measurements. It contains 33 readable measurement CSVs (about
4.749 GiB) and reproduces the committed station-side schema result: 12 bounded
time-overlap clusters, zero exact full-loop clusters and zero vehicle-fill
candidates. This confirms that the current limitation is channel provenance
and synchronization, not a lack of station-side rows. The de-identified audit
is recorded in
`research/local_private_archive_recheck_2026_10_10.json` and its companion
Markdown note.

## Public data can fill context, not every gate

Public NREL/DOE/NLR material provides valuable real operating ranges,
component traces, protocol information and aggregate fill distributions. The
public H2FillS/HDVS and DOE fast-flow material can support tank/hose and
high-flow plausibility checks. Aggregate station products can support rate,
duration, final-pressure and utilization sanity checks. They do not provide a
rights-cleared synchronized station/dispenser/vehicle logger cohort with
initial conditions, units, calibration uncertainty and reuse terms. The
repository therefore keeps the full-loop external-validation gate closed.

## Smallest useful next request

Do not wait for a large multi-year archive. Request three de-identified pilot
events first, each with:

1. common timestamp (or a documented offset);
2. dispenser/hose pressure and temperature;
3. vehicle or receiving-vessel pressure and temperature;
4. mass flow or transferred mass;
5. initial conditions, capacity and protocol/controller state;
6. normal/abnormal label provenance and data-reuse terms.

If the pilot passes the schema, units, time-base and rights checks, freeze a
prospective protocol and collect the minimum disjoint cohort needed for the
target claim. If it fails, retain the failure and continue using the station
side and consequence-component evidence already available.

## Claim boundary

The current system can make evidence-grounded station-side, component and
consequence statements. It cannot honestly claim complete station-to-vehicle
accuracy, accident frequency, certified safety distance or SAGA effectiveness
until an independent synchronized full-loop holdout and expert review exist.
This boundary is deliberate: it prevents a large private archive from being
mistaken for a validated channel contract and keeps unpublished operational
data out of the repository.
