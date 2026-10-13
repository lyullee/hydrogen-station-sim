# Kouchi 2007 actual-hydrogen spatial holdout protocol

This record freezes the intake and decision rules **before the detailed numerical
figures or tables are opened** for Kouchi et al., *Dispersion Tests on
Concentration and its Fluctuations for 40MPa Pressurized Hydrogen* (ICHS 2007,
paper 1.1.54).

The candidate is the already frozen `pooled_spatial_rank_v1` geometry score. It
may be evaluated only if the official source provides at least ten actual-hydrogen
release cases, at least eight numerical observation points in each case, common
source/observation coordinates, and reproducible concentration values. Fewer
cases or observations produce `INELIGIBLE_NO_MODEL_EVALUATION`; points from
different releases must not be pooled to manufacture eligibility.

The four aggregate screens are unchanged from the parent protocol:

- median within-case Spearman rho at least 0.5;
- at least 60% of cases with rho at least 0.4;
- mean top-five recall of the observed top quartile at least 0.6; and
- the highest-scored observation in the observed top quartile in at least 70%
  of cases.

Every screen must pass. A failure is retained and cannot trigger coefficient,
coordinate, threshold, case, or runtime changes. A pass would support only
spatial rank transfer in this experiment; it would not validate concentrations,
detector setpoints, consequence distances, ESD performance, or station safety.

Before this freeze, only the official conference listing and public search
snippets were viewed. They exposed method-level facts but no complete numerical
sensor response table or rank result. The detailed PDF had not been opened or
downloaded.

The machine-readable protocol is
[`kouchi_2007_spatial_holdout_protocol_2026_10_13.json`](kouchi_2007_spatial_holdout_protocol_2026_10_13.json).
