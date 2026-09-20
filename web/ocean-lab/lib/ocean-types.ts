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
export function normalizeReplay(data: RawReplayData): ReplayData {
  return {...data, summary: data.summary.map(row => ({...row, cases: Number(row.cases),
    ...Object.fromEntries(metricKeys.map(key => [key, Number(row[key])])) as Record<Metric,number>}))};
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
