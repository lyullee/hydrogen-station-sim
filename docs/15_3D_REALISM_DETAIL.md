# 3D station realism detail pass

Date: 2026-09-19

## Scope

Visual-only enhancement of the existing Three.js station. Physics, API and live-series contracts are unchanged. Dimensions and fittings are illustrative, not approved construction or manufacturer CAD.

## Materials and environment

- Locally generated reflection environment processed through PMREM.
- Deterministic asphalt and concrete grain textures, anisotropic filtering.
- Metallic fittings, rubber hoses, glazing and canopy light strips.
- No network requests or additional Python dependencies at runtime.

## Equipment detail

- Cascade storage: neck flanges, instanced bolt heads, hand valves, individual manifold branches, saddles, anchor plates and illustrative pressure dials.
- Dispenser: card reader, keypad, receipt slot, emergency-stop surround, access-panel seams, coupling and vehicle-connected hose.
- Vehicle: windshield, rear glazing, roof trim, grille, wheel shoulders, brake discs, fasteners, panel joints, inlet and wiper.
- Compressor: motor cooling fins, illustrative three-stage heads and intercoolers, service doors and control labels.
- Chiller: coil fins, refrigeration vessel and piping, rotating fans and concentric protective guards.
- Trailer: tube restraints, manifold, valves, landing legs, mudguards and tractor trim.
- Site: column anchoring, canopy soffit joints and drains, curbs, drainage grates, paving joints, protection posts and entrance totem.

## Interaction

- New equipment-interior button hides compressor shell/roof and chiller shell.
- Closer orbit zoom permits inspection of fittings.
- Added equipment detail participates in equipment selection; hidden covers are excluded from picking.
- Existing live status and flow animation remain connected to simulation results.

## Important boundaries

- Pressure-dial needle positions are decorative, not instrument measurements. Live numeric measurements remain in the equipment information card.
- Fan animation is visual and does not represent calculated fan RPM.
- Internal compressor/refrigeration geometry illustrates function, not actual machine geometry.
- Visible manifold and connection geometry does not add simulation nodes or safety functions.
- No tests, browser execution or performance validation were run for this task.

## Primary references

- H2Tools gaseous and liquid hydrogen fueling stations: https://h2tools.org/bestpractices/gaseous-gh2-and-liquid-hydrogen-lh2-fueling-stations
- H2FIRST reference station design: https://h2tools.org/sites/default/files/fcto_h2first_reference_station_design_report_april2015_0.pdf
- Nel DI001 H70 dispenser technical specification (visual context only): https://nelhydrogen.com/wp-content/uploads/2019/11/DI001-Technical-specification.pdf
