"""Reproducible aggregate comparison and hypothetical density/window sensitivity.

No measured density, time alignment, policy inference, or raw workbook publishing.
Run as python -m scripts.compare_ab_log --workbook /private/file.xlsx, or --check.
"""
import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from scripts.review_ab_log import read_cells, review_cells, CONFIRMED_SOURCE_SHA256

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'results/real_voyage/hanbada_comparison_inputs.json'
OUTPUT = ROOT / 'results/real_voyage/hanbada_comparison.json'
WEB = ROOT / 'web/ocean-lab/public/data/hanbada-comparison.json'
DENSITIES = ('0.800', '0.825', '0.850', '0.875', '0.900')
ENGINES = {'ME': ('T', ('AA', 'AD')), 'GE': ('U', ('AB', 'AF')), 'Boiler': ('V', ('AC', 'AH'))}
WINDOWS = (('days_01_31', 8, 68), ('days_06_31', 18, 68), ('days_06_30', 18, 66))


def quantity(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('Invalid quantity') from exc
    if not result.is_finite() or result < 0:
        raise ValueError('Quantity must be finite and nonnegative')
    return result


def extract(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != CONFIRMED_SOURCE_SHA256:
        raise ValueError('Provider context applies only to the confirmed workbook hash')
    sheets = read_cells(path)
    review = review_cells(sheets, digest)

    def selected(sheet, columns, first, last):
        values = []
        for column in columns:
            for row in range(first, last + 1):
                cell = sheets[sheet].get(f'{column}{row}', {})
                if cell.get('formula'):
                    raise ValueError('Cached formula is not an observed quantity')
                value = cell.get('value', '').strip()
                if value:
                    values.append(quantity(value))
        if not values:
            raise ValueError('Selected range has no numeric observations')
        return {'sum': str(sum(values)), 'numeric_count': len(values)}

    mass = {engine: selected('AB-LOG', columns, 10, 18) for engine, (_, columns) in ENGINES.items()}
    windows = []
    for label, first, last in WINDOWS:
        windows.append({'id': label, 'range': f'B FOAM!T{first}:V{last}',
                        'engines': {engine: selected('B FOAM', [column], first, last)
                                    for engine, (column, _) in ENGINES.items()}})
    return {'schema': 'hanbada-comparison-inputs/v1', 'source_sha256': digest,
            'units': {'summary': 'M/T', 'daily': 'kL'},
            'opening_rob': review['opening_rob'], 'closing_rob': review['closing_rob'],
            'consumption': review['consumption'], 'summary_engines': mass, 'windows': windows}


def compare(inputs):
    if inputs['source_sha256'] != CONFIRMED_SOURCE_SHA256:
        raise ValueError('Unconfirmed source identity')
    if inputs['units'] != {'summary': 'M/T', 'daily': 'kL'}:
        raise ValueError('Unexpected units')
    target = quantity(inputs['consumption'])
    if target == 0:
        raise ValueError('Positive summary consumption required')
    masses = {e: quantity(inputs['summary_engines'][e]['sum']) for e in ENGINES}
    if [w['id'] for w in inputs['windows']] != [w[0] for w in WINDOWS]:
        raise ValueError('Window contract differs')
    windows, scenarios = [], []
    for window in inputs['windows']:
        volumes = {e: quantity(window['engines'][e]['sum']) for e in ENGINES}
        total = sum(volumes.values())
        if total <= 0:
            raise ValueError('Positive selected volume required')
        windows.append({'id': window['id'], 'range': window['range'],
                        'volume_kl': str(total), 'engine_volumes_kl': {e: str(v) for e, v in volumes.items()},
                        'density_required_to_match_t_per_kl': str(target / total),
                        'engine_implied_ratios_t_per_kl': {e: str(masses[e] / v) if v else None for e, v in volumes.items()},
                        'aligned_voyage_period': False})
        for density_text in DENSITIES:
            density = quantity(density_text)
            converted = total * density
            residual = converted - target
            scenarios.append({'window': window['id'], 'assumed_density_t_per_kl': density_text,
                              'hypothetical_mass_t': str(converted), 'residual_t': str(residual),
                              'residual_percent': str(100 * residual / target),
                              'assumption_only': True})
    first, second, third = [quantity(w['volume_kl']) for w in windows]
    return {'schema': 'hanbada-comparison/v1', 'source_sha256': inputs['source_sha256'],
            'summary_mass_t': str(target), 'summary_engine_masses_t': {e: str(v) for e, v in masses.items()},
            'summary_engine_sum_residual_t': str(sum(masses.values()) - target),
            'rob_identity_residual_t': str(quantity(inputs['opening_rob']) - quantity(inputs['closing_rob']) - target),
            'volume_window_differences_kl': {'days_01_05_selected': str(first - second), 'day_31_selected': str(second - third)},
            'windows': windows, 'density_scenarios': scenarios,
            'density_grid_basis': 'analyst_selected_arithmetic_scenarios_not_observed_or_physically_validated_range',
            'common_density_assumption': 'one hypothetical density for all selected engines and days; no temperature correction',
            'measured_density': None, 'sheet1_used': False, 'model_training': False,
            'policy_validation': False, 'real_savings_validation': False,
            'status': 'aggregate_comparison_and_sensitivity_only',
            'limits': ['Windows select labeled day rows, not verified voyage timestamps',
                       'Blank cells excluded, never treated as observed zeros',
                       'Density required to match is a fitted ratio, not measured density or validation',
                       'Summary consumption is ROB-derived; matching is not independent validation',
                       'Fuel density, volume reference conditions and exact time alignment remain missing']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--workbook', type=Path)
    group.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.workbook:
        inputs = extract(args.workbook)
        result = compare(inputs)
        for path, data in [(INPUT, inputs), (OUTPUT, result), (WEB, result)]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
        print('Generated aggregate inputs, comparison and web report; original workbook unchanged')
    else:
        result = compare(json.loads(INPUT.read_text()))
        for path in (OUTPUT, WEB):
            if json.loads(path.read_text()) != result:
                raise SystemExit(f'FAIL: stale comparison artifact: {path.name}')
        print('PASS: 3 selected windows and 15 hypothetical density scenarios reproduce exactly')


if __name__ == '__main__':
    main()
