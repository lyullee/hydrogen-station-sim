# Grune 2014 secondary figure route — 2026-10-12

The original Grune 2014 route retained a 51-point main-plot extraction whose visible curve ended before the half-pressure crossing. A separate public ICHS 2011 paper by the same authors contains the same 4 mm, 200 bar, 0.37 dm3 case and a vector-rendered inset covering 0–0.5 s. The route was frozen before writing the derived coordinates, and the red `4 mm valve` vector path was extracted without changing the locked model or thresholds.

The derived trace has 319 points and exposes a half-pressure time of 0.068176 s. The locked station model predicts 0.020939 s. The resulting screens are NRMSE 18.625%, median absolute percentage error 84.599% and half-time error 69.286%; all three screens fail, so the figure-derived diagnostic does not support a validation claim.

This route is retained as a completeness diagnostic. It is not promoted to the primary gate because the source is a secondary figure reproduction rather than a rights-cleared machine-readable logger archive. The original 51-point result remains unchanged. No runtime parameter, threshold, manuscript claim or production model was changed.

Evidence:

- Protocol: `research/grune_2014_secondary_public_figure_protocol_2026_10_12.json`
- Derived coordinates: `data/public_validation/derived/grune_2014_ichs2011_inset_vector.csv`
- Result: `research/grune_2014_secondary_public_figure_result_2026_10_12.json`
- Integrity test: `tests/test_grune_2014_secondary_public_figure.py`
- Public source: https://conference.ing.unipi.it/ichs2011/papers/133.pdf
