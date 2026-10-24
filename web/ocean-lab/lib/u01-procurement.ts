import fixture from '../public/data/u01-procurement.json';

// Separate t/USD contract. Never import the normalized replay/SCI calculators.
export const u01 = fixture;
export type Violation = {port: string; kind: 'reserve'|'capacity'|'supply'|'terminal'};
export type LedgerRow = {port: string; arrival: number; purchase: number; departure: number; consumption: number; nextArrival: number; cost: number};
export type Candidate = {validInput: boolean; feasible: boolean; rows: LedgerRow[]; violations: Violation[]; rawCost: number|null; comparableCost: number|null; terminal: number|null};
export const defaultQuantities = ['20','40'] as const;
const tolerance = 1e-6; // Source contract: max(1e-6 t, 1e-8 * 100 t).

function quantity(text: string): number|null {
  // No blanks-as-zero, exponents, Infinity or silent coercion of malformed input.
  if (!/^(?:0|[1-9]\d*)(?:\.\d{1,3})?$/.test(text)) return null;
  const n = Number(text);
  return Number.isFinite(n) && n <= u01.input.capacity ? n : null;
}

export function checkU01(values: readonly string[]): Candidate {
  if (values.length !== 2) return {validInput:false,feasible:false,rows:[],violations:[],rawCost:null,comparableCost:null,terminal:null};
  const quantities = values.map(quantity);
  if (quantities.some(q=>q===null)) return {validInput:false,feasible:false,rows:[],violations:[],rawCost:null,comparableCost:null,terminal:null};
  let inventory = u01.input.initial;
  let cost = 0;
  const violations: Violation[] = [];
  const rows: LedgerRow[] = [];
  quantities.forEach((value,i)=>{
    const purchase = value!;
    const arrival = inventory;
    const departure = arrival + purchase;
    const nextArrival = departure - u01.input.d[i];
    const rowCost = purchase * u01.input.p[i];
    if (purchase > u01.input.supply[i] + tolerance) violations.push({port:u01.ports[i],kind:'supply'});
    if (departure > u01.input.capacity + tolerance) violations.push({port:u01.ports[i],kind:'capacity'});
    // Audit arrival BEFORE the next port's purchase; failures accumulate permanently.
    if (nextArrival < u01.input.reserve[i] - tolerance) violations.push({port:u01.ports[i+1],kind:'reserve'});
    rows.push({port:u01.ports[i],arrival,purchase,departure,consumption:u01.input.d[i],nextArrival,cost:rowCost});
    inventory = nextArrival;
    cost += rowCost;
  });
  if (Math.abs(inventory-u01.input.terminal)>tolerance) violations.push({port:'C',kind:'terminal'});
  return {validInput:true,feasible:violations.length===0,rows,violations,rawCost:cost,comparableCost:violations.length===0?cost:null,terminal:inventory};
}

export function u01Step(candidate: Candidate,step: number) {
  if (!candidate.validInput || !Number.isInteger(step) || step<0 || step>2) return null;
  if (step===0) return {port:'A',fuel:u01.input.initial,spent:0};
  return {port:u01.ports[step],fuel:candidate.rows[step-1].nextArrival,spent:candidate.rows.slice(0,step).reduce((sum,r)=>sum+r.cost,0)};
}
