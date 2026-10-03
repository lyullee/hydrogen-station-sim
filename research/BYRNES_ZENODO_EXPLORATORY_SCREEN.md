# Byrnes/HydDown Zenodo exploratory release screen

The open Zenodo archive `10.5281/zenodo.20728325` contains three hydrogen
blowdown validation YAML files from the HydDown reproducibility study. The
archive is CC BY 4.0 and was retrieved with SHA-256
`ed9db84e1b3301d18ff70e0ca392529bbde9d30ffa3acb9ef127d5f77f2882e5`.

The files were inspected before this screen was designed, so this result is
explicitly **post-access exploratory evidence**. It must not be promoted to a
prospective validation PASS. The screen uses the research-only CoolProp HEOS
non-adiabatic vessel model, maps vessel geometry and back pressure from each
YAML, uses no case-specific fitting, and retains the three cases.

The reproducible runner is `scripts/run_byrnes_zenodo_exploratory.py`; the
protocol and result are `research/byrnes_zenodo_exploratory_protocol.json` and
`research/byrnes_zenodo_exploratory_result.json`. The local raw archive remains
under the gitignored `data/public_validation/raw/` tree.

The exploratory run passes the pressure screen in all three cases and the
half-pressure screen in two of three cases. The combined fraction is therefore
2/3, and `claim_supported` is deliberately false. The data validate neither a
station-to-vehicle fueling loop nor dispersion, ignition, emergency response or
site separation distance.
