// U01-derived synthetic t / USD mission. No replay, model or geographic inputs.
export const missionVersion='u01-live-v1';
export type MissionInput={quantities:[number,number];prices:[number,number];supplyB:boolean};
export type MissionRow={port:string;arrival:number;requested:number;delivered:number;departure:number;required:number;consumed:number;nextArrival:number;cost:number;reached:boolean;skipped:boolean};
export type MissionResult={valid:boolean;feasible:boolean;rows:MissionRow[];violations:string[];total:number|null;comparableCost:number|null;terminal:number|null;reached:boolean};
export const initialMission:MissionInput={quantities:[20,40],prices:[600,400],supplyB:true};
export const missionLimits={capacity:100,initial:20,reserve:10,terminal:10,consumption:[30,40]};
const tolerance=1e-6;
export function calculateMission(input:MissionInput):MissionResult{
 const invalid:MissionResult={valid:false,feasible:false,rows:[],violations:[],total:null,comparableCost:null,terminal:null,reached:false};
 if(!input||!Array.isArray(input.quantities)||!Array.isArray(input.prices)||input.quantities.length!==2||input.prices.length!==2||typeof input.supplyB!=='boolean')return invalid;
 if(input.quantities.some(q=>!Number.isFinite(q)||q<0||q>100)||input.prices.some(p=>!Number.isFinite(p)||p<0||p>2000))return invalid;
 let inventory:number=20,total:number=0,reached:boolean=true;
 const rows:MissionRow[]=[],violations:string[]=[];
 for(let i=0;i<2;i++){
  const port=['A','B'][i],arrival=inventory,requested=input.quantities[i],required=missionLimits.consumption[i];
  const skipped:boolean=!reached;
  const supply=i===1&&!input.supplyB?0:100;
  const delivered:number=skipped?0:Math.min(requested,supply,Math.max(0,100-arrival));
  if(!skipped&&requested>supply+tolerance)violations.push(`${port}:supply`);
  if(!skipped&&arrival+requested>100+tolerance)violations.push(`${port}:capacity`);
  const departure:number=arrival+delivered;
  const consumed:number=skipped?0:Math.min(departure,required);
  const nextArrival:number=departure-consumed;
  reached=!skipped&&departure>=required-tolerance;
  if(!skipped&&!reached)violations.push(`${port}:stranded`);
  if(reached&&nextArrival<10-tolerance)violations.push(`${['B','C'][i]}:reserve`);
  const cost=delivered*input.prices[i];total+=cost;inventory=nextArrival;
  rows.push({port,arrival,requested,delivered,departure,required,consumed,nextArrival,cost,reached,skipped});
 }
 if(!reached||Math.abs(inventory-10)>tolerance)violations.push('C:terminal');
 const feasible=violations.length===0;
 return {valid:true,feasible,rows,violations,total,comparableCost:feasible?total:null,terminal:reached?inventory:null,reached};
}
export function missionFrame(result:MissionResult,stage:number){
 if(!result.valid||!Number.isInteger(stage)||stage<0||stage>4)return null;
 if(stage===0)return {fuel:20,spent:0,progress:0,at:'A',alert:false};
 const i=Math.floor((stage-1)/2),r=result.rows[i],arrival=stage%2===0;
 const progress=r.skipped?result.rows[0].consumed/30*0.5:arrival?(i+r.consumed/r.required)*0.5:i*0.5;
 return {fuel:arrival?r.nextArrival:r.departure,spent:result.rows.slice(0,i+1).reduce((s,row)=>s+row.cost,0),progress,at:r.skipped?'stopped':arrival?(r.reached?['B','C'][i]:'at sea'):r.port,alert:result.violations.length>0};
}
