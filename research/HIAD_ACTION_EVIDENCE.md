# HIAD incident-action evidence summary

This artifact derives a small, traceable action taxonomy from the 34
hydrogen-refuelling-station records in the public HIAD 2.2 workbook. It keeps
event identifiers, metadata and controlled action categories, while omitting
the original emergency prose, lessons and corrective-measure text.

The summary is intended to support evidence-grounded response selection and
coverage checks. It is **not** a blinded SAGA evaluation set: it is not used
to generate the holdout responses or expert ratings. The categories are
keyword-derived indicators of what a source record mentions, not judgments
that the historical action was adequate or safe.

The source workbook says that HIAD is intended for public use. Raw descriptions
remain outside this derived artifact; any redistribution of source prose or
new publication use must still be checked against the source terms and cited
to the [JRC HIAD record](https://minerva.jrc.ec.europa.eu/en/shorturl/capri/hiadpt).

## Reproduction

```powershell
$env:PYTHONPATH='src'
.venv\Scripts\python.exe scripts/build_hiad_action_evidence.py
```

The output records the workbook SHA-256, category-pattern version, per-event
field-presence flags and category counts. It does not alter the independent
full-loop physics gate or the pending expert-effectiveness gate.
