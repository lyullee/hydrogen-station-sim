# Local wide equipment-log recheck (2026-10-09)

The local station collection contains an additional wide equipment-log slice
that is more informative than the narrow pressure/lifecycle summaries alone.
An in-memory screen found **8 files, 653,442 rows and 64 fields per row**.
The time axis is effectively one-second data (median gap 1 s, maximum observed
gap 3 s) with no timestamp parsing failures.

The logs contain two storage-pressure roles, three temperature roles, three
equipment-state roles, two flow-like candidates and one totalizer-like
candidate. The pressure and temperature roles were finite for the complete
screen. The screen also observed 261 compressor-load transitions and 13
cooling-run transitions. These counts show that the files contain real
station-equipment dynamics, not only static design values.

The flow-like fields are not promoted to a flow calibration because their units
and sign/totalizer semantics are not attested. The pressure reference (absolute
versus gauge), state meanings and calibration metadata also require custodian
confirmation. No vehicle or dispenser channel candidate was found in this
wide slice.

This is therefore immediately useful for station-equipment pressure,
temperature and controller-state continuity checks and for a measured-boundary
replay after attestation. It cannot close the station-to-vehicle full-loop
validation gate or justify accident frequency, safety-limit or consequence
distance claims.

Raw rows, tags, source paths, filenames, dates and site/manufacturer identity
are intentionally excluded. The machine-readable boundary is
[`local_wide_equipment_recheck_2026_10_09.json`](local_wide_equipment_recheck_2026_10_09.json).
