# Grune 2014 pressure-decay holdout protocol

This protocol was frozen before opening or digitizing numerical coordinates
from the measured Figure 2 pressure curve in Grune et al. (2014).

The test transfers the already implemented, well-mixed adiabatic HEOS hydrogen
source model to a KIT apparatus with a 0.37 L reservoir, nominal 20 MPa initial
pressure and 4 mm release path. The model uses the project's pre-existing
`Cd = 0.8`; no case fitting, time shift or dynamic time warping is permitted.

The three required screens are:

- initial-pressure-normalized RMSE no greater than 10%;
- median absolute percentage error no greater than 15% while measured pressure
  remains at least 10% of its initial value;
- half-pressure-time relative error no greater than 20%.

All three screens must pass. At least 15 unique measured points are required.
Runtime failures and inadequate digitization remain in the record.

Known before freeze: the bibliographic record and prose description state that
Figure 2 compares measured and calculated pressure decay for a 4 mm nozzle and
200 bar initial reservoir pressure, and the article qualitatively states that a
Saint-Venant--Wantzel relation with a linear nozzle form factor describes the
decay. The actual curve coordinates and this project's predictions were not
viewed. This prior qualitative claim is disclosed and prevents describing the
test as fully blinded.

This experiment can support only a bounded source pressure-decay claim. It
cannot validate ignition, pressure load, heat release, dispersion, a 70--90 MPa
storage system, a fuelling controller or a station safety distance.
