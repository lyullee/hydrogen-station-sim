# Hydrogen-blend dispersion trend holdout

## Outcome

The prospectively declared trend screen **did not pass**. The three blend
fraction files produced upper-tail responses of 4.0, 5.0 and 4.0, while the
three release-volume files all produced 4.0. Consequently neither group met
the locked requirements for a strictly increasing response, Spearman rank of
at least 0.8 and an endpoint ratio greater than 1.0.

This negative result is retained. No column was selected after viewing the
outcomes and no acceptance threshold was relaxed.

## Execution disclosure

The first run stopped before calculating a statistic because the files are
UTF-16, tab-delimited and headerless. A format-only parser repair added UTF-16
decoding and numeric first-row detection. The case list, response statistic,
fallback column rule and acceptance thresholds remained unchanged. The result
is therefore labelled `PROSPECTIVE_ENDPOINTS_POST_ACCESS_FORMAT_REPAIR`, not a
byte-identical fully prospective execution.

## Interpretation

The archive is useful as an openly licensed example of hydrogen-blend release
measurements, but its unlabelled columns and a repeated upper response level
make this frozen aggregate statistic unsuitable for quantitative validation.
The outcome neither validates nor invalidates absolute hydrogen concentration,
outdoor station dispersion, detector placement, ESD effectiveness or
consequence distance.

## Reproduction

The raw archive is intentionally untracked. Download version 2 from the source
record and run:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\run_hydrogen_blend_dispersion_holdout.py `
  --archive <downloaded-archive.zip>
```

- Dataset: https://doi.org/10.17632/x8zkds4fyn.2
- Frozen protocol: `research/hydrogen_blend_dispersion_holdout_protocol_2026_10_08.json`
- Format amendment: `research/hydrogen_blend_dispersion_format_amendment_2026_10_08.json`
- Archived result: `research/hydrogen_blend_dispersion_holdout_result_2026_10_08.json`
