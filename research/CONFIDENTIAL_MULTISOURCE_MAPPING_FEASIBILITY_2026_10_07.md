# Controlled multi-source mapping feasibility

The controlled workbook review found one co-located candidate with multiple
subsystem worksheets. The review itself remains outside the repository because
it contains source paths, worksheet names, and headers. No measurement row was
read during the feasibility screen.

The candidate does not yet meet the canonical full-loop contract. At header
level, vehicle pressure, temperature, delivery temperature, and a precooler
state have plausible candidates; mass flow, station/cascade pressure, bank
selection, compressor, leak-check, vent, fault, and ESD state do not have an
unambiguous candidate. This must not be repaired by inference or by copying a
state from another event.

The data can still support a controlled partial-channel assessment after a
custodian-approved mapping. A synchronized station-to-vehicle validation event
requires an explicit mapping and attestation for every missing canonical role,
confirmed common time basis, units, state meanings, and an untouched outcome
window. See [the multi-source controlled intake procedure](CONTROLLED_MULTISOURCE_FULL_LOOP_INTAKE.md).
