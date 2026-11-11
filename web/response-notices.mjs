// Display-only dismissal. No process, alarm, or actuator state is changed.
export function createResponseNotices(){
  let scope, current=[], dismissed=new Set();
  return {
    read(job, labels){
      if(job!==scope){scope=job;dismissed.clear();}
      current=[...labels];
      const present=new Set(current);
      for(const label of dismissed)if(!present.has(label))dismissed.delete(label);
      return current.filter(label=>!dismissed.has(label));
    },
    dismiss(){dismissed=new Set(current);},
    reset(){scope=undefined;current=[];dismissed.clear();},
  };
}
