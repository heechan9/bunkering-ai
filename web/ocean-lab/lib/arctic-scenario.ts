import {FUEL_TOLERANCE} from './scenario-review';

/** Isolated synthetic stress experiment. Never reads or changes replay/model data. */
export const ARCTIC_VERSION = 'arctic-inspired-synthetic-v1';
export const ARCTIC_BASE_REVISION = '603aac953eb512746557a187fc32e55b6b4342f5';
export const ARCTIC_PRESETS = ['normal', 'delay-fuel', 'supply-unavailable'] as const;
export type ArcticPreset = typeof ARCTIC_PRESETS[number];
export const COMMON_FIELDS = ['initialFuel','price','fx','baseConsumption','travelHours','bunkerWorkHours','arrivalDeadlineHours'] as const;
export type CommonField = typeof COMMON_FIELDS[number];
export type Supply = 'available' | 'unavailable' | 'unknown';
export type ArcticForm = {
  preset: ArcticPreset;
  common: Record<CommonField,string>;
  legs: [{consumptionMultiplier:string;delayHours:string;supply:Supply},{consumptionMultiplier:string;delayHours:string;supply:Supply}];
};
export type ArcticInputs = {
  common: Record<CommonField,number|null>;
  legs: {consumptionMultiplier:number|null;delayHours:number|null;supply:Supply}[];
};
export function arcticPreset(preset:ArcticPreset, common?:ArcticForm['common']): ArcticForm {
  const stress=preset!=='normal';
  return {preset,common:common?{...common}:{initialFuel:'30',price:'500',fx:'1300',baseConsumption:'5',travelHours:'12',bunkerWorkHours:'4',arrivalDeadlineHours:'40'},
    legs:[{consumptionMultiplier:stress?'2':'1',delayHours:stress?'6':'0',supply:'available'},
      {consumptionMultiplier:stress?'2':'1',delayHours:stress?'6':'0',supply:preset==='supply-unavailable'?'unavailable':'available'}]};
}
const numeric=(value:string|undefined):number|null=>value==null||value.trim()===''?null:Number(value);
export function parseArctic(form:ArcticForm):ArcticInputs {
  const common=Object.fromEntries(COMMON_FIELDS.map(field=>[field,numeric(form.common[field])])) as ArcticInputs['common'];
  // UI fuel points use a 100-point tank; the engine and SCI use normalized fuel.
  for(const field of ['initialFuel','baseConsumption'] as const) if(common[field]!==null) common[field]/=100;
  return {common,legs:form.legs.map(leg=>({consumptionMultiplier:numeric(leg.consumptionMultiplier),delayHours:numeric(leg.delayHours),supply:leg.supply}))};
}
export type ArcticReason='missing_input'|'invalid_input'|'unknown_supply'|'unavailable_supply'|'fuel_shortage'|'reserve_breach'|'arrival_deadline'|'arithmetic';
export type ArcticStep={
  leg:number;buy:boolean;supply:Supply;openingFuel:number;amount:number|null;departureFuel:number|null;
  consumption:number|null;arrivalFuel:number|null;workHours:number|null;travelHours:number;delayHours:number;
  departureHours:number|null;arrivalHours:number|null;
};
export type ArcticCandidate={
  id:string;actions:boolean[];status:'feasible'|'infeasible'|'incomplete'|'invalid';reasons:ArcticReason[];
  steps:ArcticStep[];purchaseSCI:number|null;purchasedFuel:number|null;consumedFuel:number|null;finalFuel:number|null;arrivalHours:number|null;
  inventoryAdjustedSCI:number|null;comparableSCI:number|null;rank:number|null;
};
export type ArcticReview={
  inputStatus:'known'|'incomplete'|'invalid';missing:string[];invalid:string[];unitValue:number|null;
  candidates:ArcticCandidate[];eligibleCount:number;tied:boolean;
};
const paths=[[false,false],[false,true],[true,false],[true,true]];
const CAPACITY=1, TARGET=.95, REFILL=.9, RESERVE=.15;
// Roundoff allowance only (eight ULP-scale epsilons), not operational grace time.
export const deadlineExceeded=(elapsed:number,deadline:number)=>elapsed-deadline>8*Number.EPSILON*Math.max(1,Math.abs(elapsed),Math.abs(deadline));

function validate(input:ArcticInputs) {
  const missing:string[]=[],invalid:string[]=[];
  for(const field of COMMON_FIELDS) {
    const value=input.common[field];
    if(value==null) missing.push(field);
    else if(typeof value!=='number'||!Number.isFinite(value)||value<0||(['price','fx'].includes(field)&&value<=0)||(field==='initialFuel'&&value>CAPACITY)) invalid.push(field);
  }
  if(input.legs.length!==2) invalid.push('legs');
  input.legs.forEach((leg,i)=>{
    for(const field of ['consumptionMultiplier','delayHours'] as const) {
      const value=leg[field],key=`leg${i+1}.${field}`;
      if(value==null) missing.push(key);
      else if(typeof value!=='number'||!Number.isFinite(value)||value<0) invalid.push(key);
    }
    if(!['available','unavailable','unknown'].includes(leg.supply)) invalid.push(`leg${i+1}.supply`);
  });
  return {missing,invalid};
}
export function reviewArctic(input:ArcticInputs):ArcticReview {
  const {missing,invalid}=validate(input),inputStatus=invalid.length?'invalid':missing.length?'incomplete':'known';
  const price=input.common.price,fx=input.common.fx;
  const product=price!==null&&fx!==null?price*fx:NaN;
  const unitValue=Number.isFinite(product)&&product>0?product:null;
  const candidates:ArcticCandidate[]=paths.map(actions=>{
    const result:ArcticCandidate={id:actions.map(buy=>buy?'buy':'wait').join('-'),actions:[...actions],status:'feasible',reasons:[],steps:[],
      purchaseSCI:null,purchasedFuel:null,consumedFuel:null,finalFuel:null,arrivalHours:null,inventoryAdjustedSCI:null,comparableSCI:null,rank:null};
    if(inputStatus!=='known') {
      result.status=inputStatus==='invalid'?'invalid':'incomplete';
      result.reasons=[...(missing.length?['missing_input' as const]:[]),...(invalid.length?['invalid_input' as const]:[])];
      return result;
    }
    if(unitValue===null) return {...result,status:'invalid',reasons:['arithmetic']};
    const c=input.common;
    let fuel=c.initialFuel!,elapsed=0,purchased=0,consumed=0,cost=0;
    const reasons=new Set<ArcticReason>();
    for(let i=0;i<2;i++) {
      const leg=input.legs[i],buy=actions[i],openingFuel=fuel;
      // Unknown supply stops the path; do not silently substitute unavailable or zero.
      if(buy&&leg.supply==='unknown') {
        reasons.add('unknown_supply');
        result.steps.push({leg:i+1,buy,supply:leg.supply,openingFuel,amount:null,departureFuel:null,consumption:null,arrivalFuel:null,
          workHours:null,travelHours:c.travelHours!,delayHours:leg.delayHours!,departureHours:null,arrivalHours:null});
        break;
      }
      if(buy&&leg.supply==='unavailable') reasons.add('unavailable_supply');
      const amount=buy&&leg.supply==='available'?Math.min(REFILL,Math.max(0,TARGET-fuel)):0;
      const workHours=buy?c.bunkerWorkHours!:0;
      const departureFuel=fuel+amount,consumption=c.baseConsumption!*leg.consumptionMultiplier!;
      const departureHours=elapsed+workHours,arrivalHours=departureHours+c.travelHours!+leg.delayHours!;
      const arrivalFuel=departureFuel-consumption;
      const nextCost=cost+amount*unitValue,nextPurchased=purchased+amount,nextConsumed=consumed+consumption;
      if(![departureFuel,consumption,departureHours,arrivalHours,arrivalFuel,nextCost,nextPurchased,nextConsumed].every(Number.isFinite)) {
        reasons.add('arithmetic'); break;
      }
      result.steps.push({leg:i+1,buy,supply:leg.supply,openingFuel,amount,departureFuel,consumption,arrivalFuel,workHours,
        travelHours:c.travelHours!,delayHours:leg.delayHours!,departureHours,arrivalHours});
      fuel=arrivalFuel;elapsed=arrivalHours;cost=nextCost;purchased=nextPurchased;consumed=nextConsumed;
      if(fuel < -FUEL_TOLERANCE) reasons.add('fuel_shortage');
      if(fuel < RESERVE-FUEL_TOLERANCE) reasons.add('reserve_breach');
      if(deadlineExceeded(elapsed,c.arrivalDeadlineHours!)) reasons.add('arrival_deadline');
      // A later purchase must not repair a physically exhausted earlier leg.
      if(fuel<0) break;
    }
    // A computed negative endpoint is a projection, not a reached arrival, even on the final leg.
    const complete=result.steps.length===2&&result.steps.every(step=>step.arrivalFuel!==null&&step.arrivalFuel>=0)&&!reasons.has('arithmetic');
    // A roundoff-sized negative still stops execution and cannot receive a rank.
    if(!complete&&!reasons.has('unknown_supply')&&!reasons.has('arithmetic')) reasons.add('fuel_shortage');
    if(complete) {
      const adjusted=cost+(c.initialFuel!-fuel)*unitValue;
      if(!Number.isFinite(adjusted)) reasons.add('arithmetic');
      else Object.assign(result,{purchaseSCI:cost,purchasedFuel:purchased,consumedFuel:consumed,finalFuel:fuel,arrivalHours:elapsed,inventoryAdjustedSCI:adjusted});
    }
    result.reasons=[...reasons];
    result.status=reasons.has('arithmetic')?'invalid':[...reasons].some(reason=>reason!=='unknown_supply')?'infeasible':reasons.has('unknown_supply')?'incomplete':'feasible';
    if(result.status==='feasible'&&complete) result.comparableSCI=result.inventoryAdjustedSCI;
    return result;
  });
  const eligible=candidates.filter(candidate=>candidate.comparableSCI!==null).sort((a,b)=>a.comparableSCI!-b.comparableSCI!);
  const tolerance=Math.max(1,unitValue??1)*FUEL_TOLERANCE;
  eligible.forEach((candidate,i)=>{candidate.rank=i&&Math.abs(candidate.comparableSCI!-eligible[i-1].comparableSCI!)<=tolerance?eligible[i-1].rank:i+1;});
  return {inputStatus,missing,invalid,unitValue,candidates,eligibleCount:eligible.length,tied:eligible.length>1&&eligible.every(candidate=>candidate.rank===1)};
}
export function arcticExport(form:ArcticForm,generatedAt:string) {
  const input=parseArctic(form);
  const defaultPreset=arcticPreset(form.preset);
  return {schemaVersion:1,reviewVersion:ARCTIC_VERSION,implementationBaseRevision:ARCTIC_BASE_REVISION,generatedAt,
    scope:'Two abstract legs inspired by Arctic uncertainty. Synthetic sensitivity exercise only; no actual Arctic route, navigation, safety, compliance, economic or policy-performance validation.',
    provenance:{allInputs:'synthetic_assumption; edited values remain unverified',preset:form.preset,modifiedFromDefaultPreset:JSON.stringify(form)!==JSON.stringify(defaultPreset),realPortOrIceData:false,usesSavedReplay:false,usesDQN:false},
    units:{rawFuel:'100-point tank',parsedFuel:'normalized by dividing raw fuel by 100',time:'hours from departure-origin zero',cost:'SCI, not currency'},
    assumptions:{tankCapacity:CAPACITY,refillTarget:TARGET,requestedRefill:REFILL,minimumArrivalFuel:RESERVE,fuelTolerance:FUEL_TOLERANCE,timeRoundoffTolerance:'8 * Number.EPSILON * max(1, abs(arrival), abs(deadline)); not operational grace',
      sequence:'Buy or wait at A; sail leg 1; buy or wait at abstract intermediate B; sail leg 2. No purchase at destination.',
      time:'Sum work for each Buy, base travel and exogenous delay. Unavailable Buy remains excluded and has zero delivery but fixed attempted work. Final deadline is inclusive.',
      fuel:'Consumption per leg = common base consumption × per-leg multiplier; independent of elapsed time. No separate idle/wait fuel burn.',
      market:'One common price and FX for all candidates and both initial/terminal inventory valuations; no fees or other costs.',
      incomplete:'Unknown numeric input holds every path; unknown supply holds only paths that attempt Buy there. Exhaustion on either leg prevents completed-horizon totals; negative step endpoints are projections, not achieved arrivals. All incomplete/invalid/infeasible paths are unranked.',
      limits:'No route geometry, ice, season, ship class, icebreaker, regulations, actual supply, recovery, alternate ports or operational validation.'},
    accounting:'purchaseSCI + (initialFuel - finalFuel) * price * FX; equals consumed fuel * price * FX for completed paths at these fixed prices. A true tie is not economic superiority.',
    rawInputs:structuredClone(form),inputs:input,result:reviewArctic(input)};
}
