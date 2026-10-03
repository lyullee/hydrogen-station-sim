# Schefer 2006 transient mass-flow holdout protocol

This protocol freezes the evaluator, inputs, endpoints and decision thresholds
before any numerical row from the HyRAM+ digitization of Schefer et al. Figure
3b is opened or any prediction is computed for that curve.

The target is a single independent Sandia/SRI experiment: two 49 L hydrogen
cylinders beginning at 15.513 MPa and 315.15 K, with a 3.175 mm controlling
manifold restriction and a downstream 7.94 mm by 7.6 m tube. The evaluator uses
a well-mixed adiabatic rigid-vessel balance, HEOS hydrogen properties, maximum
real-gas isentropic mass flux and the public HyRAM+ benchmark value `Cd=1.0`.
No parameter may be changed after the numerical curve is opened.

The three required screens are:

- mass-flow NRMSE no more than 15% of the measured peak;
- median absolute percentage error no more than 20% where measured flow is at
  least 10% of its peak; and
- half-peak crossing-time error no more than 20%.

At least 15 unique numerical points are required. All screens must pass. The
publisher-figure digitization, rather than the plotted fit, is the observation.
No extrapolated points enter the metrics.

The experiment's approximate total duration (about 100 s) was already visible
in secondary descriptions. This is disclosed because it weakens blinding of
the timing endpoint. The exact coordinates, peak, shape and model errors were
not accessed before this freeze. The result therefore will be described as an
endpoint-frozen external holdout with prior aggregate-duration knowledge, not
as a fully blinded prospective test.

The resulting claim is limited to one transient 15.5 MPa gaseous-hydrogen
mass-flow trace. It does not validate flame length, radiation, dispersion, the
downstream tube pressure field, 70–90 MPa storage, refuelling control or the
complete station loop.
