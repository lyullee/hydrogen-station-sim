# HyTunnel two-zone transport diagnostic (2026-10-11)

This is a post-outcome development diagnostic. It does not replace the frozen
HyTunnel holdout result, change the readiness gate, or alter production model
parameters.

## Question

The frozen model treats the 60.8 m³ enclosure as one well-mixed control volume.
The public experiment describes a release 5 m from the ventilation wall in a
40 ft container. This diagnostic tests whether adding one geometry-declared
source-to-vent zone materially improves the sensor-array mean response without
fitting to the measured concentration curves.

## Model boundary

- Source-zone fraction: `5.0 / 12.192 = 0.4101`, derived from the published
  source-to-vent-wall distance and 40 ft enclosure length.
- Source-zone volume: 24.94 m³; bulk-zone volume: 35.86 m³.
- The measured ventilation flow transports gas from the source zone to the bulk
  zone and from the bulk zone to exhaust.
- Both zones start at the measured sensor-array mean at the first retained
  post-release sample.
- No case-specific fitting, time shift, sensor selection, manual crop,
  threshold change, or runtime parameter update is used.

## Result

The two-zone mechanism does **not** improve the frozen aggregate endpoint:

| model | passing cases | pass fraction | mean NRMSE (% of measured peak) | mean peak error |
|---|---:|---:|---:|---:|
| frozen well-mixed | 6 / 18 | 0.333 | 57.09 | 57.53% |
| geometry-declared two-zone | 4 / 18 | 0.222 | 66.01 | 70.25% |

The diagnostic is therefore retained as a negative model-form result. A single
source-to-bulk transport state is insufficient to represent the measured
release regimes, especially the long blowdown cases. The result supports the
existing conclusion that buoyant plume structure, detector position, enclosure
walls and the 3.86 m discharge-line transient must be represented before using
this dataset for consequence-distance or detector-placement claims.

## Reproducibility

- Code: `src/h2station/hytunnel_two_zone_diagnostic.py`
- Runner: `scripts/run_hytunnel_two_zone_diagnostic.py`
- Artifact: `research/hytunnel_two_zone_diagnostic_2026_10_11.json`
- Public dataset DOI: [10.23642/USN.14405903](https://doi.org/10.23642/USN.14405903)
- Frozen comparison: `research/hytunnel_carpark_holdout_result_2026_10_08.json`

The raw MAT rows remain outside the repository. This artifact is not evidence
of outdoor hydrogen-refuelling-station dispersion, detector certification,
site safety distance, or complete station-to-vehicle validation.
