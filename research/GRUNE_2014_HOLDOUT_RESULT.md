# Grune 2014 pressure-decay holdout result

This prospective numeric test is **ineligible** with the publicly accessible
publisher raster. It does not support or refute the source-model claim.

## Data sufficiency

- The official Figure 2 raster is 369×213 pixels.
- The red 4 mm valve trace is separable in the enlarged 0–0.01 s startup panel.
- 51 unique startup points were extracted with a conservative ±0.30 bar
  digitization interval.
- The full-duration inset overlays the calculated, valve-and-rupture-disc and
  valve traces at very low resolution.
- A trace-specific measured half-pressure time cannot be recovered without
  inferring through the other curves.

The minimum point count passed, but the required half-pressure endpoint could
not be observed. The protocol's all-three-endpoint decision therefore cannot be
evaluated.

## Descriptive startup result

For transparency, the locked model's startup comparison is retained:

- initial measured pressure: 199.843 bar absolute;
- initial predicted pressure: 199.778 bar absolute;
- initial-pressure-normalized RMSE: 11.11% (above the 10% screen);
- median absolute percentage error: 10.88% (inside the 15% screen).

These descriptive values do not convert the incomplete trace into an eligible
test. A higher-resolution measured trace or original logger data is required.
No parameter was changed after the protocol freeze, and the locked runner's
hash remains unchanged. The post-freeze archive wrapper only records
eligibility and converts non-finite missing endpoints to JSON `null`.

## Claim boundary

This attempted holdout concerns one 20 MPa, 0.37 L, 4 mm reservoir pressure
trace. It cannot validate ignition, pressure load, heat release, dispersion,
radiation, station control or safety distance.

## Machine-readable archive

`research/grune_2014_holdout_result.json` records the 51-point run with the
protocol and data hashes. The original frozen numerical runner remains
unchanged; `scripts/archive_grune_2014_holdout_result.py` adds eligibility
metadata and serializes unavailable timing endpoints as JSON `null`.

Reproduce the archive with:

```powershell
$env:PYTHONPATH = "src"
python scripts/archive_grune_2014_holdout_result.py
```
