# H2SAFE full-scale indoor surrogate-release intake

## Purpose

This record evaluates whether the public H2SAFE package can be used as an
independent source of evidence for the safety digital twin. It separates a
reproducible data-intake result from numerical calibration or full-station
validation.

## Source and integrity

- Dataset: *Dataset for H2SAFE – Controlled Gas Releases and Sensor-Response
  for Indoor Hydrogen Safety*
- DOI: `10.7799/17118570`
- Catalogue: <https://data.nlr.gov/submissions/330>
- Downloaded archive SHA-256:
  `f1b8bf747b7787f00152ec416940c80a143ea044fc18ee8a69ac9da204d9158e`
- Accompanying HVAC/readme SHA-256:
  `e99119f5f9aadac6e0bd8269b3fc7989a6026bc0a4c68221ea2a54b1eeee58bb`

The source catalogue permits use and copying subject to its notice-retention
and DOE/NLR/Alliance credit condition. The downloaded archive and document are
kept outside this repository; this repository contains only hashes, derived
schema checks, and the documented scope decision.

## What was verified

The frozen intake protocol preceded the download. The archive contains five
one-second concentration traces: one in the smaller laboratory with 24 sensor
coordinates and four in the larger laboratory with 37 coordinates. Every
sensor column present in every trace maps to a published coordinate. The
official document also provides nozzle geometry/orientation, nominal release
conditions, ventilation information, and a source location.

The machine-readable result is
`research/h2safe_indoor_release_intake_2026_10_07.json`, produced by
`scripts/analyze_h2safe_indoor_release_intake.py` using the ignored external
archive. It proves the reproducibility of source identity, structural parsing,
coordinate mapping, and missing-value handling.

## What it does not establish

The experiment uses helium as a nonflammable hydrogen surrogate. The CSV
headers do not state a concentration unit, and the released archive/document
does not explicitly state that trace time zero equals release onset. Therefore
this evidence is **not** used to:

- convert helium readings into hydrogen vol%,
- modify the virtual detector concentration coefficient, alarm threshold, trip
  threshold, or persistence setting,
- validate a station-specific detector layout, ESD response, outdoor
  dispersion, hazard distance, thermal effect, or explosion consequence,
- validate a station-to-vehicle filling loop.

The LLM evidence manifest exposes this source only as bounded full-scale
indoor sensor/geometry/HVAC context, with these restrictions included. Its
compact live prompt deliberately omits it because it supplies no decision-time
parameter and would otherwise displace live process and impact inputs.

## Next evidence needed

For a numerical detector-response comparison, obtain from the data custodian a
written concentration-unit definition, trace-to-release clock alignment,
sensor calibration/response information, and confirmation of whether a
hydrogen-equivalent transformation is scientifically intended. Any new
comparison must use a predeclared holdout experiment and must not tune the
station model against its outcome.
