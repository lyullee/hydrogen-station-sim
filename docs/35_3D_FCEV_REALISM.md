# FCEV exterior and internal packaging remodel

## Primary references

- Toyota Global Newsroom, New Mirai launch: https://global.toyota/en/newsroom/toyota/33558148.html
- Toyota, New Mirai Press Information 2020: https://global.toyota/pages/news/images/2020/12/09/1200/20201209_01_02_en.pdf
- Toyota USA Newsroom, second-generation Mirai technical overview: https://pressroom.toyota.com/toyota-introduces-second-generation-mirai-fuel-cell-electric-vehicle-as-design-and-technology-flagship-sedan/
- U.S. Department of Energy, Type IV vessel layer reference: https://www.energy.gov/cmei/fuels/articles/safety-analysis-type-4-tanks-cng-vehicles

## Reference facts used

- Second-generation Mirai reference dimensions are 4,975 mm long, 1,885 mm wide, 1,470 mm high, with a 2,920 mm wheelbase.
- The public layout places the compact FC unit under the hood, motor and traction battery at the rear, and uses rear-wheel drive.
- Three 70 MPa tanks are described: one longitudinal tank in the center tunnel and two tanks under the rear floor.
- Toyota identifies resin liners and reinforced carbon-fiber resin exteriors. The DOE reference illustrates a Type IV liner, carbon reinforcement, protective layer and metallic polar boss.

## Visual implementation

- Added `web/fcev-vehicle.js` as a replacement visual under the existing vehicle transform.
- Wide-and-low sedan loft with separate lower body, windows, windscreen, panoramic roof, mirrors, door trim, flush handles, grille, two-level front lighting, full-width rear lamp and aerodynamic trim.
- Four detailed wheel assemblies with tyres, rims, hubs, brake discs/calipers and visible axles.
- Existing refuelling receptacle coordinate remains `[-1.45, 1.02, -1.005]` in vehicle-local coordinates so the previously corrected nozzle/hose endpoint is preserved.
- The existing `차량 탱크 투시` control also switches the replacement body to a translucent service view.
- Cutaway view includes three Type IV reference vessels, liner/carbon/boss visual layers, retaining bands, valves, pressure-reduction appearance and stainless hydrogen feed.
- Front integrated FC stack appearance includes repeated cells, end plates, PCU/boost converter, air compressor and cooling connection.
- Rear package includes traction motor/transaxle appearance, half-shafts, compact lithium-ion battery, high-voltage cables and cooling paths.
- Cabin context includes five seat positions, dashboard and steering wheel. Hydrogen sensor markers are visual references.

## Model boundary

- This is an unbranded, manually constructed visualization inspired by published second-generation Mirai packaging. It is not Toyota CAD and does not reproduce proprietary dimensions beyond the published vehicle envelope.
- Component dimensions and precise positions are illustrative. Public Toyota diagrams explicitly state that their shapes and layouts are illustrative.
- The three displayed tanks do not replace or divide the simulator's existing lumped Type IV vehicle tank. Pressure, temperature, SOC, filling protocol and heat-transfer calculations remain unchanged.
- FC electrochemistry, cell voltages, battery SOC, motor torque, coolant networks, hydrogen sensors, valves, TPRDs, crash structure and leak dispersion inside the vehicle are not separately simulated.
- The cross-section colors do not establish actual liner/composite thicknesses or structural capacity.
- No claim is made for crashworthiness, homologation, pressure-vessel certification, service clearances or exact production packaging.

## Validation

No tests, browser execution, syntax checks or post-edit visual inspection were performed for this change. Implementation completion is distinct from runtime validation.
