# Confidential station lifecycle/pressure alignment holdout

This retained negative result tests whether a frozen pressure-completion
detector represents the owner-defined medium/high storage-bank lifecycle
counters. The protocol, implementation hashes, chronological 70/30 split,
pressure thresholds and event-matching rules were frozen before the full joint
alignment result was inspected. No threshold was refitted after the holdout
failed.

The evaluation read 29,361,281 pressure rows and 26,839,420 counter rows from
12 pressure and 12 counter files after excluding one exact duplicate payload.
The holdout contained 2,025 pressure-completion events and 9,325 counter events.
Within the frozen plus-or-minus 300-second window, 1,828 events matched. This
gave 90.27% pressure-event precision but only 19.60% counter-event recall. The
median absolute time offset of matched events was 26 seconds. Calibration
counter recall was similarly low at 17.06%, and medium-bank recall shifted by
18.34 percentage points between calibration and holdout. Two negative
chronological counter steps also failed the counter-monotonicity eligibility
screen.

The high precision shows that a representative bank pressure reaching 99% of
the attested nominal full pressure often occurs near a counter increment. The
low recall shows that most counter increments do not correspond to that event
definition. A plausible physical interpretation is that the owner counter
tracks vessel-level or controller-specific completion criteria that are more
granular than the representative bank pressure. This interpretation is a
hypothesis, not a recovered counter definition.

The result therefore does **not** corroborate a lifecycle or recharge-event
detector. It does not support a degradation rate, compressor capacity, storage
geometry, vehicle filling, full-loop validation, independent-site transfer,
safety limits or field certification. Runtime parameters and defaults remain
unchanged. The result is retained because it prevents the digital twin and its
LLM layer from treating a convenient pressure threshold as validated lifecycle
semantics.

Only aggregate, privacy-bounded statistics are published. Source identifiers,
paths, filenames, headers, raw rows, timestamps, calendar dates, site/company/
location/manufacturer information and per-file hashes remain unpublished.
