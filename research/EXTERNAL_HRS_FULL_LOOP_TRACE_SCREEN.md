# External HRS full-loop trace screen

`scripts/validate_external_hrs_full_loop.py` is the numerical-input gate for a
rights-cleared, de-identified station-to-vehicle logger package. It is run
after `intake_external_hrs_bundle.py`, `validate_external_hrs_manifest.py`,
and `validate_external_hrs_trace.py`.

The CSV must use the same monotonic clock for every channel. In addition to the
base vehicle pressure/temperature and mass-flow contract, it must contain:

* station or dispenser absolute pressure and delivered-gas temperature;
* cascade source absolute pressure and selected-bank state; and
* simultaneous low-, medium-, and high-bank absolute pressures for a
  cascade-resolved full-loop result;
* compressor and precooler states; and
* leak-check, vent, fault, and ESD states.

Canonical column names are accepted, along with the aliases in the validator.
If a custodian uses different names, add a de-identified `column_map` to the
metadata declaration. The map is a semantic mapping only; it must not contain
site, company, equipment serial or manufacturer identifiers.

The screen checks channel presence, finite values, missingness, strictly
increasing time, maximum time gap, and the frozen pressure/temperature ranges.
It also requires the pressure used by the base trace screen to be an
independently named vehicle/receptacle boundary or to be explicitly mapped to
that boundary in the custodian declaration. A generic pressure column cannot
be reused as both station and vehicle pressure, because that would create a
false full-loop claim without an independent receiving-side measurement.
It does not impute, resample, smooth, fit, or calculate model errors. A
`FULL_LOOP_TRACE_READY_FOR_EVALUATION` result means that a separately frozen
evaluator may be run with cascade-dispatch and recharge evidence. A valid
trace without the three-bank triplet is labelled
`STATION_TO_VEHICLE_TRACE_READY_PARTIAL_CASCADE`; it can support only a
selected-bank station-to-vehicle evaluation. Neither outcome closes
`full_loop_external_validation`, proves field safety, or permits an IJHE claim
by itself.

Example invocation after the byte-level manifest and declaration are available:

```text
python scripts/validate_external_hrs_full_loop.py \
  --trace <quarantine>/event.csv \
  --manifest <quarantine>/manifest.json \
  --declaration <quarantine>/declaration.json \
  --bundle-root <quarantine> \
  --output <quarantine>/full_loop_screen.json
```

The output contains only de-identified column names, aggregate ranges and
input hashes. Raw rows remain in the quarantined location and are not added to
the repository.
