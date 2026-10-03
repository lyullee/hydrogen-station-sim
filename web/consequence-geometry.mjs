// Translate deterministic consequence fields into an explicit display contract.
// Distances remain in metres.  Thermal/blast samples are radial screening
// distances; the 4 vol% dispersion result is a directional plume length.

const positive=value=>{
  const number=Number(value);
  return Number.isFinite(number)&&number>0?number:0;
};

const finite=value=>{
  const number=Number(value);
  return Number.isFinite(number)?number:0;
};

function halfSpan(extent){
  if(!Array.isArray(extent)||extent.length<2)return 0;
  const values=extent.map(Number).filter(Number.isFinite);
  return values.length>=2?Math.max(...values)-Math.min(...values):0;
}

export function consequenceDisplayGeometry(consequence={}){
  const thermalBlastRadiusM=positive(consequence.sampled_effect_radius_m);
  const flammablePlumeLengthM=positive(
    consequence.flammable_plume_streamline_distance_m
  );
  const xSpanM=halfSpan(consequence.flammable_plume_x_extent_m);
  const ySpanM=halfSpan(consequence.flammable_plume_y_extent_m);
  // HyRAM contour arrays describe the plume in its local axial/radial plane.
  // The radial span is used only for visual thickness; the reported centerline
  // distance remains the authoritative downrange measure.
  const flammablePlumeHalfWidthM=Math.max(
    .05,
    Math.min(flammablePlumeLengthM*.45, ySpanM/2 || xSpanM*.08 || flammablePlumeLengthM*.08),
  );
  const releaseAngleRad=finite(consequence.release_angle_rad);
  return {
    thermalBlastRadiusM,
    flammablePlumeLengthM,
    flammablePlumeHalfWidthM:flammablePlumeLengthM?flammablePlumeHalfWidthM:0,
    releaseAngleRad,
    hasRadialEffect:thermalBlastRadiusM>0,
    hasFlammablePlume:flammablePlumeLengthM>0,
    maxDisplayDistanceM:Math.max(thermalBlastRadiusM,flammablePlumeLengthM),
  };
}

export function mergePeakGeometry(previous,current){
  if(!previous)return {...current};
  const radialFromPrevious=previous.thermalBlastRadiusM>current.thermalBlastRadiusM;
  const plumeFromPrevious=previous.flammablePlumeLengthM>current.flammablePlumeLengthM;
  const thermalBlastRadiusM=Math.max(
    previous.thermalBlastRadiusM,current.thermalBlastRadiusM,
  );
  const flammablePlumeLengthM=Math.max(
    previous.flammablePlumeLengthM,current.flammablePlumeLengthM,
  );
  return {
    thermalBlastRadiusM,
    flammablePlumeLengthM,
    flammablePlumeHalfWidthM:plumeFromPrevious
      ? previous.flammablePlumeHalfWidthM : current.flammablePlumeHalfWidthM,
    releaseAngleRad:plumeFromPrevious
      ? previous.releaseAngleRad : current.releaseAngleRad,
    hasRadialEffect:thermalBlastRadiusM>0,
    hasFlammablePlume:flammablePlumeLengthM>0,
    maxDisplayDistanceM:Math.max(thermalBlastRadiusM,flammablePlumeLengthM),
    heldFromPrevious:radialFromPrevious||plumeFromPrevious,
  };
}
