# Grüne 2014 pressure-time data request draft

This is a draft only. It is not an authorization to contact the authors or KIT and it contains no private station information.

## Subject
Request for a rights-cleared machine-readable pressure trace for the 4 mm, 200 bar hydrogen-release experiment

## Recipient
Corresponding authors of Grüne et al., *Experimental study of ignited unsteady hydrogen releases from a high pressure reservoir*, DOI [10.1016/j.ijhydene.2013.08.076](https://doi.org/10.1016/j.ijhydene.2013.08.076), or the KITopen data custodian for KITopen record [110097219](https://publikationen.bibliothek.kit.edu/110097219).

## Request

We are preparing a reproducibility-bounded validation of a hydrogen source-depletion model. We would like to request, if available, the original machine-readable reservoir pressure-time export for the 4 mm nozzle, approximately 200 bar initial-pressure, 0.37 dm3 vessel case shown in Figure 2.

Please provide:

1. pressure and time columns, including the pressure basis (absolute or gauge) and units;
2. sampling interval, acquisition start/stop definition, valve-opening or release trigger timing, and any zero-time correction;
3. the vessel volume, initial temperature, nozzle/valve geometry and any line or extension volume used for the trace;
4. the identity of the measured curve if multiple valve/rupture-disc curves are present;
5. calibration or uncertainty information and any missing-value conventions; and
6. written permission to use derived coordinates and aggregate error metrics in an open research article and accompanying reproducibility record, with the source DOI cited.

A de-identified CSV or a small table is sufficient; the full station configuration is not requested. If the raw trace cannot be redistributed, a custodian-hosted read-only export or a rights-cleared derived table with the complete discharge endpoint would also be useful.

## Reproducibility boundary

The validation protocol is frozen in `research/grune_2014_holdout_protocol.json`. We will not change the model parameters, endpoints or thresholds after receiving the trace. The file will be quarantined, hashed, and checked before any numerical outcome is used. The trace would be used only for the stated vessel pressure-decay component screen; it would not be used to claim station control, ignition, dispersion, radiation, safety distance or full-loop fueling validation.

## Current public-source result

The accessible article and conference reproduction provide apparatus metadata and a complete figure-derived diagnostic curve, but no rights-cleared machine-readable raw trace. The figure-derived diagnostic remains post-access evidence and does not close the independent Grüne 2014 gate.
