import {comparePurchases, type Candidate, type DecisionSnapshot} from './purchase-comparison';

/** Separate fixed synthetic review. Never changes replay actions or official evaluation. */
export const REVIEW_VERSION = 'fixed-scenario-v1';
export const SOURCE_REVISION = '7884e9749ec3e497b9d495ec4e62e4466c625f8a';
export const FUEL_TOLERANCE = 1e-9; // docs/technical/safety_accounting.md
export const STEP_HOURS = 24;
export const TIME_FIELDS = ['baselineDeparture', 'cargoEnd', 'bunkerReady', 'preparation', 'transfer', 'cleanup', 'departureReadiness', 'deadline'] as const;
export type TimeField = typeof TIME_FIELDS[number];
export type TimingInputs = Record<TimeField, number | null>;
export type TimingForm = Record<TimeField, string>;
export type Preset = 'normal' | 'deadline' | 'missing';
export function scenarioPreset(preset: Preset): TimingForm {
  return {baselineDeparture:'12', cargoEnd:'10', bunkerReady:preset === 'deadline' ? '8' : '0', preparation:'1', transfer:preset === 'missing' ? '' : '8', cleanup:'1', departureReadiness:preset === 'missing' ? '' : '2', deadline:'14'};
}
export function parseTiming(form: TimingForm): TimingInputs {
  return Object.fromEntries(TIME_FIELDS.map(key => [key, form[key] == null || form[key].trim() === '' ? null : Number(form[key])])) as TimingInputs;
}
export type TimeCheck = {
  status: 'known' | 'incomplete' | 'invalid'; missing: TimeField[]; invalid: TimeField[];
  bunkerEnd: number | null; departure: number | null; extraHours: number | null;
};
/** Hours from the same local call origin; readiness follows ALL cargo/bunker work.
 * Port of research/port_call_time/model.py existing_call, with readiness mandatory.
 * No-buy uses the counterfactual departure (which already includes readiness).
 */
export function callTiming(input: TimingInputs, buy: boolean): TimeCheck {
  const fields: readonly TimeField[] = buy ? TIME_FIELDS : ['baselineDeparture', 'deadline'];
  const missing = fields.filter(key => input[key] == null);
  const invalid = fields.filter(key => input[key] != null && (!Number.isFinite(input[key]) || input[key]! < 0));
  const empty = {missing, invalid, bunkerEnd:null, departure:null, extraHours:null};
  if (invalid.length) return {status:'invalid', ...empty};
  if (missing.length) return {status:'incomplete', ...empty};
  if (!buy) return {status:'known', ...empty, departure:input.baselineDeparture!, extraHours:0};
  const bunkerEnd = input.bunkerReady! + input.preparation! + input.transfer! + input.cleanup!;
  const departure = Math.max(input.baselineDeparture!, Math.max(input.cargoEnd!, bunkerEnd) + input.departureReadiness!);
  if (![bunkerEnd, departure].every(Number.isFinite)) return {status:'invalid', ...empty, invalid:['bunkerReady','preparation','transfer','cleanup','departureReadiness']};
  return {status:'known', ...empty, bunkerEnd, departure, extraHours:departure-input.baselineDeparture!};
}
export type Reason = 'fuel_shortage' | 'reserve_breach' | 'capacity' | 'depleted' | 'deadline' | 'missing_time' | 'invalid_time' | 'arithmetic';
export type ReviewedStep = {
  decision: number; buy: boolean; fuelBeforeRefill: number; fuelAfter: number; amount: number;
  timing: TimeCheck; departureHours: number | null; deadlineHours: number | null; onTime: boolean | null;
};
export type ReviewedCandidate = {
  id: string; actions: boolean[]; status: 'feasible' | 'infeasible' | 'incomplete' | 'invalid'; reasons: Reason[];
  steps: ReviewedStep[]; purchaseSCI: number; purchasedFuel: number; finalFuel: number;
  inventoryAdjustedSCI: number | null; comparableSCI: number | null; rank: number | null;
};
export type ScenarioReview = {
  status: 'reviewed' | 'unavailable'; decision: number | null; horizon: number; unitValue: number | null;
  candidates: ReviewedCandidate[]; eligibleCount: number; tied: boolean;
};

function reviewCandidate(candidate: Candidate, snapshot: DecisionSnapshot, input: TimingInputs, unitValue: number): ReviewedCandidate {
  const reasons = new Set<Reason>();
  let delay: number | null = 0;
  const steps = candidate.steps.map((step, i): ReviewedStep => {
    // Audit the raw pre-refill state: a later refill cannot repair an earlier violation.
    const fuelBeforeRefill = step.fuelBefore - .05;
    if (fuelBeforeRefill < -FUEL_TOLERANCE) reasons.add('fuel_shortage');
    if (fuelBeforeRefill < .15-FUEL_TOLERANCE) reasons.add('reserve_breach');
    if (step.fuelBefore < -FUEL_TOLERANCE || step.fuelBefore > 1+FUEL_TOLERANCE || step.fuelAfter > .95+FUEL_TOLERANCE || step.amount < 0 || step.amount > .9+FUEL_TOLERANCE) reasons.add('capacity');
    const timing = callTiming(input, step.buy);
    if (timing.status === 'invalid') reasons.add('invalid_time');
    if (timing.status === 'incomplete') reasons.add('missing_time');
    const priorDelay = delay;
    delay = delay === null || timing.extraHours === null ? null : delay + timing.extraHours;
    const departureHours = priorDelay === null || timing.departure === null ? null : i*STEP_HOURS + priorDelay + timing.departure;
    const deadlineHours = input.deadline !== null && Number.isFinite(input.deadline) && input.deadline >= 0 ? i*STEP_HOURS + input.deadline : null;
    const arithmetic = [delay, departureHours, deadlineHours].some(value => value !== null && !Number.isFinite(value));
    if (arithmetic) reasons.add('arithmetic');
    const onTime = arithmetic || departureHours === null || deadlineHours === null ? null : departureHours <= deadlineHours;
    if (onTime === false) reasons.add('deadline');
    return {decision:snapshot.step+i+1, buy:step.buy, fuelBeforeRefill, fuelAfter:step.fuelAfter, amount:step.amount, timing,
      departureHours:arithmetic ? null : departureHours, deadlineHours:arithmetic ? null : deadlineHours, onTime};
  });
  if (candidate.stopped || candidate.steps.length !== candidate.actions.length) reasons.add('depleted');
  // The same assumed current market value prices both inventories. No future rows.
  const inventoryAdjustedSCI = candidate.cost + (snapshot.fuel.value! - candidate.finalFuel)*unitValue;
  if (![candidate.cost, inventoryAdjustedSCI].every(Number.isFinite)) reasons.add('arithmetic');
  const status = reasons.has('arithmetic') || reasons.has('invalid_time') ? 'invalid'
    : [...reasons].some(reason => !['missing_time'].includes(reason)) ? 'infeasible'
    : reasons.has('missing_time') ? 'incomplete' : 'feasible';
  return {id:candidate.actions.map(buy => buy ? 'buy' : 'wait').join('-'), actions:candidate.actions, status, reasons:[...reasons], steps,
    purchaseSCI:candidate.cost, purchasedFuel:candidate.amount, finalFuel:candidate.finalFuel,
    inventoryAdjustedSCI:Number.isFinite(inventoryAdjustedSCI) ? inventoryAdjustedSCI : null,
    comparableSCI:status === 'feasible' ? inventoryAdjustedSCI : null, rank:null};
}

export function reviewScenario(snapshot: DecisionSnapshot | null, input: TimingInputs): ScenarioReview {
  const empty: ScenarioReview = {status:'unavailable', decision:snapshot ? snapshot.step+1 : null, horizon:0, unitValue:null, candidates:[], eligibleCount:0, tied:false};
  if (!snapshot || !Number.isInteger(snapshot.step) || snapshot.step < 0 || snapshot.step >= 30 || !Number.isInteger(snapshot.remaining) || snapshot.remaining !== 30-snapshot.step) return empty;
  const unitValue = snapshot.price.value! * snapshot.fx.value!;
  if (!Number.isFinite(unitValue) || unitValue <= 0) return empty;
  const candidates = comparePurchases(snapshot).map(candidate => reviewCandidate(candidate, snapshot, input, unitValue));
  if (!candidates.length) return empty;
  const eligible = candidates.filter(candidate => candidate.comparableSCI !== null).sort((a,b) => a.comparableSCI!-b.comparableSCI!);
  // Floating-point noise must not manufacture a winner under the fixed-price assumptions.
  const tolerance = Math.max(1, unitValue)*FUEL_TOLERANCE;
  eligible.forEach((candidate, i) => {candidate.rank = i && Math.abs(candidate.comparableSCI!-eligible[i-1].comparableSCI!) <= tolerance ? eligible[i-1].rank : i+1;});
  return {status:'reviewed', decision:snapshot.step+1, horizon:Math.min(2,snapshot.remaining), unitValue, candidates,
    eligibleCount:eligible.length, tied:eligible.length > 1 && eligible.every(candidate => candidate.rank === 1)};
}

export type ReviewSelection = {policy: string; checkpoint: string; caseSeed: number};
export function scenarioExport(snapshot: DecisionSnapshot | null, form: TimingForm, generatedAt: string, replaySelection: ReviewSelection | null = null) {
  const input = parseTiming(form);
  return {
    schemaVersion:1, reviewVersion:REVIEW_VERSION, sourceRevision:SOURCE_REVISION, generatedAt,
    scope:'fixed synthetic one/two-step review; not a route optimizer, operational recommendation or policy evaluation',
    provenance:{marketAndFuel:'synthetic replay observations', timeInputs:'synthetic_assumption; user-edited values remain unverified'},
    units:{fuel:'normalized (UI displays ×100); initial=1, capacity=1, refill target=0.95', cost:'SCI, not currency', time:'hours from review origin; step starts are 0 and 24'},
    assumptions:{consumptionPerStep:0.05, requestedRefill:0.9, refillTarget:0.95, tankCapacity:1, minimumPreRefillFuel:0.15, fuelTolerance:FUEL_TOLERANCE, stepHours:STEP_HOURS,
      market:'current price and FX held fixed; same unit value for opening and closing fuel',
      timing:'same existing-cargo-call template at each step; full fixed work durations for every buy, even a clipped refill; prior incremental delay carries forward without recovery',
      baseline:'no-bunkering departure already includes departure readiness',
      work:'cargoEnd includes bunkering interruption; bunkerReady includes access/waiting; cleanup excludes departure readiness; readiness follows all work',
      unmodeled:'quantity-dependent transfer, port supply, fuel grades, tides, pilots, berth allocation, downstream rescheduling and idle-time fuel use'},
    accounting:'purchaseSCI + (initialFuel - finalFuel) * currentPrice * currentFX; comparableSCI is null unless all modeled constraints pass',
    notice:'Equal adjusted SCI under these assumptions does not demonstrate economic superiority. Passing checks does not establish real-world feasibility.',
    replaySelection:replaySelection ? {...replaySelection} : null, snapshot, rawTimingInputs:{...form}, timingInputs:input, result:reviewScenario(snapshot,input),
  };
}
