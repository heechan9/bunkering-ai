/** Deterministic explanation only. No policy/Q values or future replay rows. */
export type Reading = { value: number | null; step: number | null; kind: 'record' | 'assumption' | 'missing'; timestamp: string | null };
export type DecisionSnapshot = { step: number; remaining: number; fuel: Reading; price: Reading; fx: Reading; previousPrice: Reading };
const reading = (value: unknown, step: number): Reading => typeof value === 'number' && Number.isFinite(value)
  ? {value, step, kind:'record', timestamp:null} : {value:null,step:null,kind:'missing',timestamp:null};
export function decisionSnapshot(trace: readonly (readonly number[])[], completed: number): DecisionSnapshot | null {
  if (!Number.isInteger(completed) || completed < 0 || completed >= trace.length || completed >= 30) return null;
  // This row's price/FX are PRE-action observations at this decision boundary.
  // Never use its action, outcome or any later row in candidate calculations.
  return {step:completed,remaining:30-completed,fuel:reading(completed ? trace[completed-1]?.[0] : 1,completed),
    price:reading(trace[completed]?.[6],completed),fx:reading(trace[completed]?.[7],completed),
    previousPrice:reading(completed ? trace[completed-1]?.[6] : undefined,completed-1)};
}
export function readingAge(item: Reading, step: number): number | null {
  return item.step === null || item.step > step ? null : step-item.step;
}
export type Transition = {buy:boolean;fuelBefore:number;fuelAfter:number;amount:number;cost:number;unmet:number;reserveViolation:boolean;rawViolation:boolean;depleted:boolean};
export function purchaseTransition(fuel:number, price:number, fx:number, buy:boolean): Transition {
  if (![fuel,price,fx].every(Number.isFinite) || fuel<0 || fuel>1 || price<=0 || fx<=0) throw new Error('Invalid decision inputs');
  const before=Math.max(0,fuel-.05), amount=buy?Math.min(.9,Math.max(0,.95-before)):0;
  const fuelAfter=Math.min(.95,before+amount);
  return {buy,fuelBefore:fuel,fuelAfter,amount,cost:amount*price*fx,unmet:Math.max(0,.05-fuel),reserveViolation:fuelAfter<.15-1e-12,rawViolation:fuelAfter<.15,depleted:fuelAfter<=0};
}
export type Candidate = {actions:boolean[];steps:Transition[];cost:number;amount:number;finalFuel:number;stopped:boolean};
export function comparePurchases(s:DecisionSnapshot): Candidate[] {
  const values=[s.fuel,s.price,s.fx];
  if(values.some(r=>r.value===null||r.kind!=='record'||r.step!==s.step)||s.remaining<1) return [];
  const fuel=s.fuel.value!,price=s.price.value!,fx=s.fx.value!;
  if(![fuel,price,fx].every(Number.isFinite)||fuel<0||fuel>1||price<=0||fx<=0) return [];
  const paths=s.remaining>=2?[[false,false],[false,true],[true,false],[true,true]]:[[false],[true]];
  return paths.map(actions=>{
    const steps:Transition[]=[];let current=fuel;
    for(const buy of actions){const r=purchaseTransition(current,price,fx,buy);steps.push(r);current=r.fuelAfter;if(r.depleted)break;}
    return {actions,steps,cost:steps.reduce((a,r)=>a+r.cost,0),amount:steps.reduce((a,r)=>a+r.amount,0),finalFuel:current,stopped:steps.some(r=>r.depleted)};
  });
}
