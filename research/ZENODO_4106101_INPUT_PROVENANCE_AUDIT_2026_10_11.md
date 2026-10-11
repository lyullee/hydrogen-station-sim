# Zenodo 4106101 input provenance audit

The public record is [10.5281/zenodo.4106101](https://doi.org/10.5281/zenodo.4106101)
and its associated paper is [10.1016/j.ijhydene.2020.08.221](https://doi.org/10.1016/j.ijhydene.2020.08.221).

This audit separates source-documented inputs from values that the runner
supplies outside the Zenodo metadata. The metadata document contains the
14.9 m³ enclosure and all ten case-specific vent areas used by the runner;
their values match exactly. It does not contain a per-case initial or
ambient-temperature channel/table. The runner currently carries a fixed
`T0_K` map, so the result must not describe those temperatures as “case
metadata” without a separate, citable paper/supplement source.

No runtime parameter was changed and no case was retuned. The existing
seven-of-ten result remains an exploratory pressure-peaking screen. Until a
temperature boundary is independently archived with provenance, the screen
cannot be promoted to a confirmatory temperature-aware consequence
validation.

Machine-readable evidence: `research/zenodo_4106101_input_provenance_audit_2026_10_11.json`.

Reproduce:

```powershell
.venv\Scripts\python.exe scripts\audit_zenodo_4106101_input_provenance.py
```
