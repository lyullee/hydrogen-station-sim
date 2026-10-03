# Grune 2014 Figure 2 derived coordinates

`grune_2014_figure2.csv` contains the separable red **4 mm valve** startup
trace from Figure 2 of:

J. Grune, K. Sempert, M. Kuznetsov and T. Jordan, “Experimental study of
ignited unsteady hydrogen releases from a high pressure reservoir,”
*International Journal of Hydrogen Energy* 39 (2014) 6176–6183,
<https://doi.org/10.1016/j.ijhydene.2013.08.076>.

The source was the official Elsevier CDN raster
`1-s2.0-S0360319913020521-gr2.jpg`, SHA-256
`0c3d4ad6173749df7bec5b16f5f16041f940a93e969034597e2617efdDA3855c`
(case-insensitive hexadecimal). The publisher image is not redistributed.

The fixed extractor identifies red pixels only inside the monotonic startup
corridor and maps the printed axes using `(34 px, 0 s)`, `(359 px, 0.01 s)`,
`(31 px, 202 bar)` and `(184 px, 180 bar)`. Sampling every six horizontal
pixels produces 51 points. A conservative 0.30 bar reading uncertainty covers
about two vertical pixels.

The 369×213 image's full-duration inset has overlapping calculated,
valve-and-rupture-disc and valve traces. It is not possible to assign the
half-pressure crossing to the red valve trace without inference. The inset is
therefore excluded, the primary half-time endpoint is missing, and this
holdout is archived as **ineligible** rather than scored as a model failure.
