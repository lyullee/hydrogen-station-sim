// Keep the largest calculated sampling extent visible for the life of one release.
// A zero/missing update is not evidence that the earlier affected area vanished.
export function reconcileRiskRanges(previous, cases, nowMs, graceMs=3000){
  const next=new Map(),seen=new Set();
  for(const row of cases){
    if(!row?.id)continue;
    seen.add(row.id);
    const thermalBlast=Number(row.consequence?.sampled_effect_radius_m)||0;
    const flammablePlume=Number(row.consequence?.flammable_plume_streamline_distance_m)||0;
    const radius=Math.max(thermalBlast,flammablePlume);
    const prior=previous.get(row.id);
    if(Number.isFinite(radius)&&radius>0){
      const peak=row.actual?Math.max(radius,prior?.radius||0):radius;
      next.set(row.id,{...row,consequence:peak>radius&&prior?prior.consequence:row.consequence,
        radius:peak,currentRadius:radius,lastPresentMs:nowMs,
        displayState:peak>radius?'PEAK_HELD':'CURRENT'});
    }else if(row.actual&&prior){
      next.set(row.id,{...prior,currentRadius:0,lastPresentMs:nowMs,displayState:'PEAK_HELD'});
    }
  }
  for(const [id,prior] of previous){
    if(seen.has(id)||!prior.actual||nowMs-prior.lastPresentMs>graceMs)continue;
    next.set(id,{...prior,displayState:'RECENTLY_ENDED'});
  }
  return next;
}
