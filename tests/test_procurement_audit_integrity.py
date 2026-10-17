"""Adversarial artifact tests, using immutable inputs without rerunning an optimizer."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from research.procurement_baseline.audit_results import AuditError, audit_artifacts, recompute_summary


@pytest.fixture(scope='module')
def original():
    root = Path(__file__).resolve().parents[1] / 'research/procurement_baseline'
    result = []
    with zipfile.ZipFile(root / 'provenance/reviewed_bundle.zip') as archive:
        for filename in ('cases.json', 'results.json', 'summary.json', 'spec.json'):
            members = [name for name in archive.namelist() if name.endswith('/' + filename)
                       and 'original' not in name and 'independent' not in name]
            assert len(members) == 1
            result.append(json.loads(archive.read(members[0])))
    return result


@pytest.fixture
def data(original):
    return copy.deepcopy(original)


def test_original_passes(original):
    report = audit_artifacts(*original)
    assert report['status'] == 'PASS'
    assert report['checks']['ledgers'] > 360
    assert report['summary'] == original[2]


def numeric_paths(value, path=()):
    for key, item in value.items():
        if isinstance(item, dict):
            yield from numeric_paths(item, path + (key,))
        elif type(item) in (int, float):
            yield path + (key,)


def test_every_numeric_summary_field_is_checked(original):
    for path in numeric_paths(original[2]):
        data = copy.deepcopy(original)
        target = data[2]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] += 10
        with pytest.raises(AuditError, match='summary'):
            audit_artifacts(*data)


@pytest.mark.parametrize('change', ['missing', 'extra', 'bool', 'nan', 'infinity'])
def test_summary_schema_and_types(data, change):
    target = data[2]['ALL']['policies']['minimum_required']
    if change == 'missing':
        del target['optimal_match_n']
    elif change == 'extra':
        target['unverified_metric'] = 99
    else:
        target['common_cost_weighted_difference_pct'] = {
            'bool': True, 'nan': float('nan'), 'infinity': float('inf')}[change]
    with pytest.raises(AuditError):
        audit_artifacts(*data)


def test_zero_denominator_summary_is_null():
    rows = [dict(block='test', reference={'status': 'INFEASIBLE'},
                 policies={p: {'status': 'POLICY_FAILURE'} for p in
                           ('minimum_required', 'next_cheaper', 'departure_concentrated')})]
    metrics = recompute_summary(rows)['ALL']['policies']['minimum_required']
    assert metrics['pairwise_cost_weighted_difference_pct'] is None
    assert metrics['common_cost_weighted_difference_pct'] is None


def test_missing_all_vectors_cannot_pass(data):
    for row in data[1]:
        for result in [row['reference'], *row['policies'].values()]:
            result.pop('q_t', None)
    with pytest.raises(AuditError):
        audit_artifacts(*data)


@pytest.mark.parametrize('method', ['reference', 'minimum_required'])
@pytest.mark.parametrize('field', ['q_t', 'z', 'ledger'])
@pytest.mark.parametrize('change', ['missing', 'short', 'extra'])
def test_solution_completeness(data, method, field, change):
    row = next(r for r in data[1] if r['reference']['status'] == 'OPTIMAL')
    result = row['reference'] if method == 'reference' else row['policies'][method]
    target = result['audit'] if field == 'ledger' else result
    if change == 'missing':
        del target[field]
    elif change == 'short':
        target[field].pop()
    else:
        target[field].append(copy.deepcopy(target[field][-1]))
    with pytest.raises(AuditError):
        audit_artifacts(*data)


@pytest.mark.parametrize('field', ['q_t', 'z', 'objective_usd', 'ledger', 'total_usd', 'terminal_t', 'mass_residual_t'])
@pytest.mark.parametrize('value', [True, float('nan'), float('inf'), '0'])
def test_numeric_evidence_rejects_invalid_types(data, field, value):
    result = next(r['reference'] for r in data[1] if r['reference']['status'] == 'OPTIMAL')
    if field in ('q_t', 'z'):
        result[field][0] = value
    elif field == 'ledger':
        result['audit']['ledger'][0]['q_t'] = value
    elif field == 'objective_usd':
        result[field] = value
    else:
        result['audit'][field] = value
    with pytest.raises(AuditError):
        audit_artifacts(*data)


@pytest.mark.parametrize('field', ['call_index', 'I_before_t', 'q_t', 'D_after_t', 'consumption_t',
                                   'I_next_t', 'reserve_t', 'z', 'fuel_cost_usd',
                                   'variable_fee_usd', 'fixed_fee_usd', 'total_usd'])
def test_every_ledger_field_checked(data, field):
    result = next(r['reference'] for r in data[1] if r['reference']['status'] == 'OPTIMAL')
    result['audit']['ledger'][0][field] += 1
    with pytest.raises(AuditError):
        audit_artifacts(*data)


@pytest.mark.parametrize('change', ['block', 'policy_missing', 'policy_extra', 'status', 'case_bool', 'audit_valid', 'errors'])
def test_membership_and_metadata(data, change):
    row = data[1][0]
    if change == 'block':
        row['block'] = 'monetary_fees'
    elif change == 'policy_missing':
        row['policies'].pop('minimum_required')
    elif change == 'policy_extra':
        row['policies']['unexpected'] = row['policies']['minimum_required']
    elif change == 'status':
        row['policies']['minimum_required']['status'] = 'UNRECOGNIZED'
    elif change == 'case_bool':
        data[0][0]['case']['d'][0] = True
    elif change == 'audit_valid':
        row['policies']['minimum_required']['audit']['valid'] = 1
    else:
        row['policies']['minimum_required']['audit']['errors'].append('fabricated')
    with pytest.raises(AuditError):
        audit_artifacts(*data)


def test_failure_policy_still_requires_solution(data):
    result = next(r['policies']['minimum_required'] for r in data[1]
                  if r['policies']['minimum_required']['status'] == 'POLICY_FAILURE')
    for key in ('q_t', 'z', 'audit'):
        result.pop(key)
    with pytest.raises(AuditError):
        audit_artifacts(*data)


def test_optimized_cli_rejects_false_metrics(data, tmp_path):
    data[2]['ALL']['policies']['minimum_required'].update(
        common_cost_weighted_difference_pct=99.999, optimal_match_n=1000000)
    for filename, value in zip(('cases.json', 'results.json', 'summary.json', 'spec.json'), data):
        (tmp_path / filename).write_text(json.dumps(value), encoding='utf-8')
    output = tmp_path / 'audit'
    run = subprocess.run([sys.executable, '-O', '-m', 'research.procurement_baseline.audit_results',
                          '--input-dir', str(tmp_path), '--output-dir', str(output)],
                         capture_output=True, text=True)
    assert run.returncode != 0
    assert 'AuditError' in run.stderr
    assert not (output / 'independent_checks.json').exists()


@pytest.mark.parametrize('status', ['INFEASIBLE', 'LIMIT_REACHED', 'SOLVER_ERROR', 'AUDIT_FAILED'])
def test_reference_status_cannot_contradict_valid_solution(data, status):
    row = next(r for r in data[1] if r['reference']['status'] == 'OPTIMAL')
    row['reference']['status'] = status
    data[2] = recompute_summary(data[1])
    with pytest.raises(AuditError):
        audit_artifacts(*data)


@pytest.mark.parametrize('attack', ['B1', 'B2', 'B3', 'B4', 'B5'])
def test_cross_artifact_attacks_with_recomputed_summary(data, attack):
    row = next(r for r in data[1] if r['case_id'] == 'monetary_fees_003')
    if attack in ('B1', 'B2'):
        row['reference'] = {'status': 'LIMIT_REACHED' if attack == 'B1' else 'INFEASIBLE',
                            'message': 'time limit'}
    elif attack == 'B3':
        row['reference']['status'] = 'REFERENCE_CONTRADICTION'
    elif attack == 'B4':
        row['policies']['minimum_required'].update(status='POLICY_FAILURE', reasons=['fabricated'])
    else:
        policy = row['policies']['next_cheaper']
        for key in ('q_t', 'z', 'audit'):
            row['reference'][key] = copy.deepcopy(policy[key])
        row['reference']['objective_usd'] = policy['audit']['total_usd']
        assert row['reference']['objective_usd'] - row['raw_reference']['objective_usd'] == 1070
    data[2] = recompute_summary(data[1])
    with pytest.raises(AuditError):
        audit_artifacts(*data)


@pytest.mark.parametrize('raw_status', ['LIMIT_REACHED', 'INFEASIBLE', 'SOLVER_ERROR', 'LEXICOGRAPHIC_FAILED'])
def test_legitimate_raw_failure_contradiction(data, raw_status):
    row = next(r for r in data[1] if r['reference']['status'] == 'OPTIMAL')
    raw = {'status': raw_status, 'message': 'recorded solver failure'}
    if raw_status == 'LEXICOGRAPHIC_FAILED':
        raw.update(primary_status='OPTIMAL', secondary_status='LIMIT_REACHED')
    row['raw_reference'] = raw
    row['reference'] = dict(raw, status='REFERENCE_CONTRADICTION')
    data[2] = recompute_summary(data[1])
    assert audit_artifacts(*data)['status'] == 'PASS'


def test_legitimate_objective_contradiction(data):
    row = next(r for r in data[1] if r['case_id'] == 'monetary_fees_003')
    policy = row['policies']['next_cheaper']
    for key in ('q_t', 'z', 'audit'):
        row['raw_reference'][key] = copy.deepcopy(policy[key])
    row['raw_reference']['objective_usd'] = policy['audit']['total_usd']
    row['reference'] = dict(row['raw_reference'], status='REFERENCE_CONTRADICTION')
    data[2] = recompute_summary(data[1])
    assert audit_artifacts(*data)['status'] == 'PASS'


@pytest.mark.parametrize('change', ['missing_raw', 'missing_enum', 'raw_extra', 'enum_extra',
                                   'count_bool', 'count_zero', 'patterns', 'best_missing',
                                   'best_shape', 'best_nonfinite', 'best_objective',
                                   'best_infeasible', 'infeasible_best'])
def test_raw_and_enumeration_schema(data, change):
    row = next(r for r in data[1] if r['reference']['status'] == 'OPTIMAL')
    enum = row['independent_stop_enumeration']
    if change == 'missing_raw':
        del row['raw_reference']
    elif change == 'missing_enum':
        del row['independent_stop_enumeration']
    elif change == 'raw_extra':
        row['raw_reference']['unexpected'] = 1
    elif change == 'enum_extra':
        enum['unexpected'] = 1
    elif change == 'count_bool':
        enum['feasible_patterns'] = True
    elif change == 'count_zero':
        enum['feasible_patterns'] = 0
    elif change == 'patterns':
        enum['patterns'] += 1
    elif change == 'best_missing':
        enum['best'] = None
    elif change == 'best_shape':
        enum['best']['q_t'].pop()
    elif change == 'best_nonfinite':
        enum['best']['q_t'][0] = float('nan')
    elif change == 'best_objective':
        enum['best']['objective_usd'] += 1
    elif change == 'best_infeasible':
        enum['best']['q_t'][0] += 1
    else:
        enum['status'] = 'INFEASIBLE'
        enum['feasible_patterns'] = 0
    with pytest.raises(AuditError):
        audit_artifacts(*data)


def test_audit_does_not_run_optimizers(original, monkeypatch):
    from research.procurement_baseline import benchmark, procurement
    def forbidden(*args, **kwargs):
        raise AssertionError('audit must not invoke an optimizer')
    for module, names in [(benchmark, ('solve', 'enumerate_stops')),
                          (procurement, ('solve', 'enumerate_stops', 'linprog', 'milp'))]:
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    assert audit_artifacts(*original)['status'] == 'PASS'


def test_enumeration_unused_enabled_stop_is_valid(data):
    # Enumeration masks permit q=0, z=1 when minimum and fixed fee are zero.
    for item, row in zip(data[0], data[1]):
        if row['block'] != 'zero_fees_unlimited' or row['reference']['status'] != 'OPTIMAL':
            continue
        best = row['independent_stop_enumeration']['best']
        for i, qty in enumerate(best['q_t']):
            if qty == 0 and item['case']['available'][i] and best['z'][i] == 0:
                best['z'][i] = 1
                assert audit_artifacts(*data)['status'] == 'PASS'
                return
    pytest.fail('fixture needs an unused available zero-fee stop')


def test_forging_raw_and_reference_still_checks_enumeration(data):
    row = next(r for r in data[1] if r['case_id'] == 'monetary_fees_003')
    policy = row['policies']['next_cheaper']
    for key in ('q_t', 'z', 'audit'):
        row['raw_reference'][key] = copy.deepcopy(policy[key])
    row['raw_reference']['objective_usd'] = policy['audit']['total_usd']
    row['reference'] = copy.deepcopy(row['raw_reference'])
    data[2] = recompute_summary(data[1])
    with pytest.raises(AuditError, match='reference provenance.status'):
        audit_artifacts(*data)


def test_oversized_integer_is_structured_audit_error(data):
    row = next(r for r in data[1] if r['reference']['status'] == 'OPTIMAL')
    row['raw_reference']['q_t'][0] = 10 ** 400
    with pytest.raises(AuditError, match='finite representable number'):
        audit_artifacts(*data)


def test_nonfinite_raw_audit_failed_is_intentionally_unauditable(data):
    row = next(r for r in data[1] if r['reference']['status'] == 'OPTIMAL')
    raw = row['raw_reference']
    raw['status'] = 'AUDIT_FAILED'
    raw['q_t'][0] = float('nan')
    raw['audit'] = {'valid': False, 'errors': ['nonfinite solution']}
    row['reference'] = dict(raw, status='REFERENCE_CONTRADICTION')
    data[2] = recompute_summary(data[1])
    with pytest.raises(AuditError, match='finite number required'):
        audit_artifacts(*data)
