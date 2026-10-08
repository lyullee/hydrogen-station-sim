# Draft request for Type III/IV aspect-ratio refuelling experiments

**Review the sender identity and institutional route before sending.**

Subject: Request for a blind subset of Type III/IV hydrogen-cylinder refuelling traces

Dear authors and data custodian,

I am preparing an independent validation study of a hydrogen-refuelling-station
safety digital twin. Your article, *Experimental investigation and
thermodynamic model improvement of the refueling process in type III and type
IV hydrogen storage cylinders* (DOI
<https://doi.org/10.1016/j.ijhydene.2026.156406>), reports experiments spanning
both vessel types and multiple aspect ratios. This is directly relevant to
testing whether a lumped thermal model transfers across liner materials and
vessel geometry.

Could you provide a de-identified machine-readable export, or identify the
approved data custodian, with the following fields where available:

- common elapsed time and sampling interval;
- tank pressure, inlet pressure and instantaneous mass flow or cumulative mass;
- inlet-gas, internal-gas, liner/wall and ambient temperatures;
- vessel type, internal volume, diameter, cylindrical length, wall layers and
  material heat capacities;
- inlet/nozzle diameter and orientation;
- initial conditions, target pressure, precooling condition, pressure ramp and
  stop reason; and
- sensor position, calibration, uncertainty, units and quality flags.

The public article already reveals aggregate model errors. To preserve an
independent test, please use a custodian-held split if unreported repeats are
available: release a calibration subset first, keep the blind case identifiers
and outcomes undisclosed, and release the disjoint holdout once we provide a
timestamped model commit and frozen scoring protocol. At least six blind cases
covering both Type III and Type IV vessels and more than one aspect-ratio class
would support a transfer test; fewer cases would remain useful as a bounded
diagnostic.

Please also state the reuse terms for derived error metrics, figures and an
open repository. We do not need manufacturer, operator or site identifiers.
Any files will be quarantined and hashed before numerical inspection, and all
eligible failures will be retained.

Sincerely,

*[name, affiliation, institutional email and project DOI to be supplied]*
