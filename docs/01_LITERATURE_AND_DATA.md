# Literature and Open-Data Baseline

This is a living evidence register. A model should not be promoted from
experimental to validated until its equation set, parameter source, applicable
range, and comparison data are recorded here.

## Station architecture and standards

1. ISO 19880-1:2020, *Gaseous hydrogen - Fuelling stations - Part 1: General
   requirements*. The standard identifies delivery/production, compression,
   pumps/vaporizers, buffer storage, precooling, and dispensing as principal
   station elements. <https://www.iso.org/standard/71940.html>
2. SAE J2601, *Fueling Protocols for Light Duty Gaseous Hydrogen Surface
   Vehicles*. This is the controlling reference for light-duty fueling protocol
   behavior. The standard is not redistributed here; implementation must use a
   lawfully obtained copy and track the exact revision.
   <https://www.sae.org/standards/content/j2601_202005/>

## Existing dynamic station simulators

1. NREL/NLR H2FillS is a transient thermodynamic model of station-to-vehicle
   filling. Version 3 includes a partial station model, batch processing, and
   pressure-ramp optimization. It is the primary validation-oriented reference,
   but its executable license and registration requirements mean it is not a
   source-code dependency. <https://www.nrel.gov/hydrogen/h2fills>
2. Kuroki et al. (2021), *Thermodynamic Modeling of Hydrogen Fueling Process
   from High Pressure Storage Tanks to Vehicle Tank*, International Journal of
   Hydrogen Energy 46, 22004-22017. This is the main published H2FillS model
   reference. <https://doi.org/10.1016/j.ijhydene.2021.04.037>
3. MathWorks, *Hydrogen Refueling Station*. The public example uses 200 bar
   supply storage, a three-stage intercooled compressor, and 450/650/950 bar
   cascade banks, then a reduction valve, -40 C precooler, hose, and vehicle.
   It is used as a topology and control-decomposition reference only.
   <https://www.mathworks.com/help/hydro/ug/hydrogen-refueling-station.html>
4. DTU-TES, *Hydrogen-Fuelling-Station*. This public Modelica/Dymola library uses
   CoolProp through ExternalMedia and provides a useful object-oriented station
   decomposition. <https://github.com/DTU-TES/Hydrogen-Fuelling-Station>
5. Rothuizen et al. (2013), *Optimization of hydrogen vehicle refueling via
   dynamic simulation*. The work reports that cascade staging reduces modeled
   cooling and compression energy and identifies vehicle-side pressure loss as
   an important determinant of flow. <https://doi.org/10.1016/j.ijhydene.2013.01.161>
6. Li et al. (2024), *Creation and validation of a dynamic simulation method for
   the whole process of a hydrogen refueling station*. The model covers storage
   to vehicle, compressor to vehicle, and compressor to station storage paths.
   <https://doi.org/10.1016/j.est.2024.110508>

## Tank thermodynamics and heat transfer

1. Xiao et al. (2024), *Thermodynamic and heat transfer models for refueling
   hydrogen vehicles: Formulation, validation and application*. It compares
   one-zone gas, two-zone gas/tank, and three-zone gas/liner/shell lumped models.
   <https://doi.org/10.1016/j.ijhydene.2023.06.081>
2. The first implementation in this repository is the two-zone gas/wall level.
   The parameter and state interfaces are intentionally compatible with a later
   gas/liner/shell model.
3. A 2025 high-aspect-ratio study shows that axial multi-zone treatment can be
   necessary for long heavy-duty tanks. This is an escalation criterion rather
   than a default for light-duty tanks.
   <https://doi.org/10.1016/j.ijhydene.2025.152513>

## Properties, numerics, and reusable engineering libraries

1. CoolProp supplies the hydrogen Helmholtz-energy equation of state and state
   properties. The documented hydrogen backend covers pressure far beyond the
   70/95 MPa station range. <https://coolprop.org/fluid_properties/fluids/Hydrogen.html>
2. CoolProp high-level and low-level state interfaces are the property source;
   no ideal-gas density replacement is used in vessel balances.
   <https://coolprop.org/coolprop/HighLevelAPI.html>
3. SciPy provides bounded optimization and `solve_ivp`; BDF or Radau is intended
   for the coupled fast-flow/slow-thermal system.
   <https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html>
4. `fluids` is reserved for documented pipe, fitting, compressible-flow, and
   control-valve correlations. <https://fluids.readthedocs.io/>
5. `ht` is reserved for heat-exchanger correlations and effectiveness-NTU
   extensions. <https://ht.readthedocs.io/>

## HyRAM+ interface review

The inspected package is HyRAM+ 6.1, published in September 2025.
<https://pypi.org/project/hyram/>

Relevant public entry points:

- `hyram.phys.api.create_fluid`
- `hyram.phys.api.compute_mass_flow`
- `hyram.phys.api.analyze_jet_plume`
- `hyram.phys.api.analyze_accumulation`
- `hyram.phys.api.jet_flame_analysis`
- `hyram.phys.api.compute_overpressure`
- `hyram.qra.analysis.conduct_analysis`

HyRAM+ provides validated release, plume, flame, overpressure, harm, and QRA
models. Its current technical reference and validation reports are linked from
Sandia. <https://energy.sandia.gov/programs/sustainable-transportation/hydrogen/hydrogen-safety-codes-and-standards/hyram/>

Integration rule:

- The process model owns instantaneous pressure, temperature, inventory, and
  operating mode.
- HyRAM receives an immutable state snapshot plus a leak scenario.
- Fast consequence metrics may be refreshed periodically.
- Full `conduct_analysis` QRA is a separate baseline/design calculation because
  component frequencies, ignition probabilities, occupancy, and demand counts
  are not instantaneous thermodynamic states.

## Open data

1. Korea Petroleum Quality & Distribution Authority hydrogen-station operations
   API includes station name, address, equipment type, dispenser type, and
   hydrogen supply method. It is useful for station inventory and configuration,
   not for identifying dynamic physics parameters.
   <https://www.data.go.kr/data/15133332/openapi.do>
2. The U.S. Alternative Fuel Stations API contains hydrogen station location,
   status, access, and vehicle-class fields. It does not expose second-by-second
   process telemetry. <https://developer.nlr.gov/docs/transportation/alt-fuel-stations-v1/>
3. The European H2-Stations export API supplies static station attributes,
   real-time availability, and events. A token is required for production use;
   a sandbox is available. <https://docs.h2-stations.eu/for-data-users/>
4. The European Hydrogen Observatory publishes downloadable station location and
   dispenser-type data. <https://observatory.clean-hydrogen.europa.eu/hydrogen-landscape/distribution-and-storage/hydrogen-refuelling-stations>

Conclusion: public station datasets are suitable for fleet maps, station
metadata, availability monitoring, and scenario priors. They are not sufficient
to calibrate tank heat transfer, valve coefficients, compressor maps, or dynamic
risk. Those require component specifications, commissioning traces, or dedicated
experiments.

## Piping, hoses, and valves

1. ISO 19880-3:2018 covers high-pressure hydrogen check, excess-flow, flow-control,
   breakaway, manual, pressure-safety, and shut-off valves used up to H70. The
   edition was confirmed current in 2024.
   <https://www.iso.org/standard/64754.html>
2. ISO 19880-5:2025 defines safety and test requirements for dispenser hose
   assemblies up to 70 MPa and from -40 C to 65 C. Its performance requirements
   inform component limits but do not supply a dynamic pressure-loss model.
   <https://www.iso.org/standard/87684.html>
3. Rothuizen et al. (2020), *Dynamic simulation of the effect of vehicle-side
   pressure loss of hydrogen fueling process*, validates a dynamic cascade model
   and shows vehicle-side pressure loss directly affects final tank temperature.
   <https://doi.org/10.1016/j.ijhydene.2020.01.071>
4. Elaoud and Hadj-Taieb (2009) derive one-dimensional transient mass, momentum,
   and energy equations for non-isothermal compressible hydrogen-containing gas
   pipelines. The equations define the later high-fidelity momentum-state option;
   they are more detailed than needed for every short station line.
   <https://doi.org/10.1016/j.ijhydene.2009.06.062>
5. The `fluids.compressible.isothermal_gas` implementation uses the complete
   isothermal gas-pipeline relation and accepts non-ideal average density. Its
   Darcy factor is obtained from `fluids.friction.friction_factor`.
   <https://fluids.readthedocs.io/fluids.compressible.html>
