# Confidential lifecycle-counter summary

An owner-controlled lifecycle logger was summarized in place. Only aggregate
counter statistics are published; raw rows, source tags, operator/site
identity, and exact source dates remain restricted.

The two documented generic counters increase 1,183 and 851 times in the
selected window. The maximum sampled single increment for either counter is
two. The counters are defined by the data owner as full-bank recharge counts;
they are not operating-hour measurements. The aggregate is therefore suitable
for station operating-history context and a future aging-state experiment, but
it is not a degradation law or a failure-rate estimate.

The current simulator does not silently convert these counts into a capacity,
heat-transfer, leak, or relief-threshold change. A cycle-aware model must first
freeze the physical relationship and validate it on a later untouched window.
