# Yang et al. 2024 actual-H₂ chamber data request (draft)

This is a **non-sending request draft**. It does not authorize contact, download, or use of any unpublished file. The paper is retained as boundary evidence until a custodian provides the raw package and reuse terms.

## Source

- Article: *Quantitative analysis of hydrogen leakage and diffusion processes based on real-time concentration measurement at different spatial positions in a customized chamber*
- DOI: [10.1016/j.ijhydene.2024.04.051](https://doi.org/10.1016/j.ijhydene.2024.04.051)
- Intended use: a narrowly scoped, independent actual-hydrogen spatial-detector holdout for the safety digital twin.

## Minimum package requested

1. Time-resolved hydrogen concentration for every sensor channel, with elapsed time from release start.
2. A sensor-coordinate crosswalk for all 26 locations, including sensor height and orientation.
3. Release source coordinates, leak-orifice diameter, upstream pressure/temperature, measured orifice mass/volume flow, release duration, and ventilation state.
4. Sampling interval, missing-value rules, calibration/uncertainty information, units and channel-quality flags.
5. Initial and ambient conditions, chamber geometry, and experiment/repetition identifiers needed to separate cases without exposing personal or site identifiers.
6. A file-level SHA-256 manifest and written permission for derived aggregate metrics to be published in an open repository and an IJHE manuscript.

## Frozen-use conditions

- The model candidate, sensor-ranking rule, case split and acceptance screens will be frozen before numerical rows are opened.
- No case-specific fitting, smoothing, time shifting, selective case removal or outcome-based sensor remapping will be allowed.
- Every eligible failure will be retained and reported.
- Raw rows, exact calendar dates, company/site identity, manufacturer details and personal information will not be copied into the repository.
- A custodian-run evaluation is acceptable when raw data cannot be transferred; the custodian must return the immutable input hash, protocol hash and aggregate per-case metrics.

## Claim boundary

A passing package could support only transfer of the spatial concentration/sensor-response component under the supplied chamber geometry and release conditions. It would not validate an HRS station controller, vehicle filling, ESD performance, site-specific consequence distance or SAGA human-effectiveness claim.

## Suggested message

> We are preparing an independent, unfitted evaluation of a hydrogen spatial-detector component. Could you provide the time-resolved concentration files, sensor-coordinate crosswalk, release metadata, calibration/quality fields and reuse terms for the experiments reported in DOI 10.1016/j.ijhydene.2024.04.051? We will freeze the model, case split and scoring protocol before opening numerical outcomes, retain all failures, and publish only de-identified aggregate metrics. A custodian-run evaluation with file and protocol hashes is also acceptable.
