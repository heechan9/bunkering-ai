export type Coordinates = [number, number];
export type Region = {
  title: string; en: string; badge: string; connection: string;
  description: string; center: Coordinates; bounds: [number, number, number, number];
  labels: [string, number, number, string][]; focus: Coordinates; source: string; note: string;
};
export type Flight = { region: string };
export type WorldLand = {type:'Feature'; properties:Record<string,unknown>|null; geometry:{type:'MultiPolygon'; coordinates:number[][][][]}};
export type Coastlines = { regions: Record<string, { polygons: Coordinates[][][] }> };
export type TerrainData = {
  region: string; bounds: [number, number, number, number]; width: number; height: number;
  elevations: number[]; land: number[];
};
export type ExportVessel = (() => Promise<boolean>) | null;
export type Policy = 'double_dqn' | 'safe_stock' | 'price_reactive' | 'fixed_fueling';
export const metricKeys = ['success_rate','raw_violation_episode_rate','tolerance_1e_12_violation_episode_rate','episode_sci_mean','bunker_amount_mean','bunkering_count_mean','final_fuel_mean'] as const;
export type Metric = typeof metricKeys[number];
export type Summary = { policy: Policy; cases: number } & Record<Metric, number>;
export type Trace = [number, number, number, number, number][];
export type ReplayData = { runs: Record<string, Record<string, Trace>>; summary: Summary[]; caseSeeds: number[] };
export type RawReplayData = Omit<ReplayData, 'summary'> & {summary: ({policy:Policy;cases:number|string}&Record<Metric,number|string>)[]};
const replayColumns = ['fuel_after','bunker_amount','realized_consumption','step_sci','reward','safety_violation','decision_price','decision_fx','price_advantage_reward','safety_reward','operational_reward'];
const replayRuns = ['fixed_fueling','price_reactive','safe_stock','dqn_42','dqn_1042','dqn_2042','dqn_3042'];
function invalidReplay(field: string): never { throw new Error(`Invalid replay data: ${field}`); }
function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}
function summaryNumber(value: unknown, field: string): number {
  // Do not turn missing values, booleans or blank CSV cells into zero.
  if (typeof value !== 'number' && (typeof value !== 'string' || !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(value.trim()))) invalidReplay(field);
  const number = Number(value);
  if (!Number.isFinite(number)) invalidReplay(field);
  return number;
}
/** Validate the fixed baseline display contract, not scientific truth or real-vessel safety. */
export function normalizeReplay(data: unknown): ReplayData {
  if (!isRecord(data) || data.schema !== 'ocean-lab-replay/v1' || data.maxSteps !== 30) invalidReplay('schema');
  if (!Array.isArray(data.columns) || data.columns.length !== replayColumns.length || data.columns.some((key, i) => key !== replayColumns[i])) invalidReplay('columns');
  const seeds = data.caseSeeds;
  if (!Array.isArray(seeds) || seeds.length !== 100 || new Set(seeds).size !== 100 || seeds.some(seed => !Number.isInteger(seed) || seed < 42 || seed > 141)) invalidReplay('caseSeeds');
  const runs = data.runs;
  if (!isRecord(runs)) invalidReplay('runs');
  for (const key of replayRuns) {
    const run = runs[key];
    if (!isRecord(run)) invalidReplay(`runs.${key}`);
    for (const seed of seeds) {
      const trace = run[String(seed)];
      // Early exhaustion is a valid saved result; do not require 30 rows.
      if (!Array.isArray(trace) || trace.length < 1 || trace.length > 30) invalidReplay(`runs.${key}.${seed}`);
      for (const row of trace) {
        if (!Array.isArray(row) || row.length !== replayColumns.length || row.some(value => typeof value !== 'number' || !Number.isFinite(value))) invalidReplay(`runs.${key}.${seed}.row`);
      }
    }
  }
  if (!Array.isArray(data.summary) || data.summary.length !== replayRuns.length) invalidReplay('summary');
  const seen = new Set<string>();
  const summary = data.summary.map(row => {
    if (!isRecord(row)) invalidReplay('summary.row');
    const key = row.policy === 'double_dqn' && typeof row.checkpoint === 'string'
      ? row.checkpoint.replace(/^dqn_seed_/, 'dqn_')
      : row.checkpoint === 'not_applicable' ? row.policy : null;
    if (typeof key !== 'string' || !replayRuns.includes(key) || seen.has(key)) invalidReplay('summary.coverage');
    // A DQN checkpoint must not be relabeled as a rule policy (or vice versa).
    if ((key.startsWith('dqn_') && row.policy !== 'double_dqn') || (!key.startsWith('dqn_') && row.policy !== key)) invalidReplay('summary.policy');
    seen.add(key);
    const cases = summaryNumber(row.cases, 'summary.cases');
    if (cases !== seeds.length) invalidReplay('summary.cases');
    const metrics = Object.fromEntries(metricKeys.map(metric => {
      const value = summaryNumber(row[metric], `summary.${metric}`);
      if (value < 0 || (metric.endsWith('_rate') && value > 1)) invalidReplay(`summary.${metric}`);
      return [metric, value];
    })) as Record<Metric, number>;
    return {...row, policy: row.policy as Policy, cases, ...metrics};
  });
  return {...data, runs: runs as ReplayData['runs'], caseSeeds: seeds, summary};
}
export type ReplaySelection = {policy: Policy; checkpoint: string; caseSeed: number; step: number};
export function isReplaySelection(value: unknown): value is ReplaySelection {
  if (!value || typeof value !== 'object') return false;
  const v = value as Record<string, unknown>;
  return typeof v.policy === 'string' && ['double_dqn','safe_stock','price_reactive','fixed_fueling'].includes(v.policy)
    && typeof v.checkpoint === 'string' && ['42','1042','2042','3042'].includes(v.checkpoint)
    && typeof v.caseSeed === 'number' && Number.isInteger(v.caseSeed) && v.caseSeed >= 42 && v.caseSeed <= 141
    && typeof v.step === 'number' && Number.isInteger(v.step) && v.step >= 0 && v.step <= 30;
}
export type ModelContext = {registerTool: (tool: {name: string; description: string; inputSchema: object;
  annotations?: {readOnlyHint: boolean}; execute: (value: unknown) => unknown}, options: {signal: AbortSignal}) => unknown};
