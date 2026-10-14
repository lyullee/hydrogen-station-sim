import { consequenceDisplayGeometry, mergePeakGeometry } from './consequence-geometry.mjs';

// Keep the largest calculated sampling extent visible for the life of one release.
// A zero/missing update is not evidence that the earlier affected area vanished.
export function reconcileRiskRanges(previous, cases, nowMs, graceMs=3000){
  const next=new Map(),seen=new Set();
  for(const row of cases){
    if(!row?.id)continue;
    seen.add(row.id);
    const currentGeometry=consequenceDisplayGeometry(row.consequence);
    const radius=currentGeometry.maxDisplayDistanceM;
    const prior=previous.get(row.id);
    if(Number.isFinite(radius)&&radius>0){
      const geometry=row.actual
        ?mergePeakGeometry(prior?.geometry,currentGeometry):currentGeometry;
      next.set(row.id,{...row,geometry,currentGeometry,
        radius:geometry.maxDisplayDistanceM,currentRadius:radius,lastPresentMs:nowMs,
        displayState:geometry.heldFromPrevious?'PEAK_HELD':'CURRENT'});
    }else if(row.actual&&prior){
      next.set(row.id,{...prior,currentGeometry,currentRadius:0,lastPresentMs:nowMs,
        displayState:'PEAK_HELD'});
    }else if(row.hypothetical&&prior){
      // SAGA/HyRAM scenario results can arrive as a zero-distance placeholder
      // while a recalculation is in flight. Keep the last rendered geometry
      // only for the same short grace window; an actually absent hypothesis
      // still disappears immediately as before.
      next.set(row.id,{...prior,currentGeometry,currentRadius:0,lastPresentMs:nowMs,
        pendingRecalculation:true,displayState:'CALC_PENDING'});
    }
  }
  for(const [id,prior] of previous){
    if(seen.has(id)||(!prior.actual&&!prior.pendingRecalculation)||nowMs-prior.lastPresentMs>graceMs)continue;
    next.set(id,{...prior,displayState:'RECENTLY_ENDED'});
  }
  return next;
}
