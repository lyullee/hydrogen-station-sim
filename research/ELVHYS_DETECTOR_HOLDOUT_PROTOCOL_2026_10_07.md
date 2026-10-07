# ELVHYS measured-signal HAZOP holdout protocol

This protocol freezes a 12-test replay before downloading the selected outcome
files from the public HSE/DataverseNO ELVHYS 4.2 dataset (DOI
`10.18710/JXJP0H`, CC0 1.0). Previously inspected tests 3, 24, 29–31 and 45
are excluded. The selected set spans both nominal pressures, four small-leak
diameters, active and passive ventilation, and horizontal and vertical release
orientations.

Release onset is found independently from the nozzle-pressure channel. Each
concentration head is corrected by its pre-release median, then the maximum of
the published 16-head grid is replayed as one measured gas signal through the
unchanged `GD-0101` HAZOP rules. The primary screen requires zero missed or
unexpected threshold events, trigger timing within one 20 Hz sample, and an
available staged `gas_release` response with public accident precedents.

This is an integration validation of measured-signal ingestion, persistence,
severity and response routing. It is not evidence for detector placement,
dispersion or concentration prediction, H70 transfer, ESD effectiveness,
consequence distance, or the complete station-to-vehicle model. All failures
remain in the result and no case, threshold, time shift or baseline rule may be
changed after the selected measurements are opened.
