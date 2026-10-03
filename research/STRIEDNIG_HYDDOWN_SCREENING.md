# Striednig tank-filling data found in HydDown

Screened: **2026-10-03**

## Finding

The public [HydDown repository](https://github.com/andr1976/HydDown) contains
three validation YAML files with embedded time and gas-mean-temperature
measurement arrays for Type I steel-tank hydrogen filling experiments reported
by Striednig et al. in the *International Journal of Hydrogen Energy*, DOI
[10.1016/j.ijhydene.2014.03.028](https://doi.org/10.1016/j.ijhydene.2014.03.028).
The repository is MIT-licensed at commit
`1040d758b819533451086baa5cf2a47b4292a22f`.

The source manual describes a 0.0235 m³ Type I steel tank, a 350 bar upstream
reservoir and an electronically controlled dispenser. The three embedded cases
use nominal 5, 10 and 30 MPa/min pressurisation conditions and contain 17, 23
and 29 time/temperature pairs respectively. The YAML also records model
boundary fields such as initial, back and end pressure and the orifice
diameter.

## Evidence boundary

This is useful independent physical evidence for the tank thermal filling
submodel. It is **not** an HRS full-loop dataset: the committed YAMLs do not
contain measured pressure or mass-flow arrays, station cascade states,
compressor/precooler signals, dispenser metering or controller events. The
model boundary fields must not be relabelled as measurements.

The repository license covers HydDown, but the original measurements are a
secondary transcription of the published article. Their independent
redistribution rights and provenance have not been established. This project
therefore records source commit and file hashes only and does not copy the
arrays into the repository.

## Reproducibility record

The machine-readable screening record is
`research/striednig_hyddown_screening.json`. It preserves the source commit,
file digests, case counts, temperature ranges and the exact claim boundary.
The data can be used for a new, pre-registered tank-thermal holdout only after
the provenance and reuse terms are confirmed. Any resulting test must remain
separate from the consumed Powertech full-loop material.
