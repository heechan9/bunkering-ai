import copy
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import pytest
from research.procurement_baseline.generate_report import build_report


def example():
    return {'ALL': {'n': 3, 'reference_status': {'OPTIMAL': 2, 'INFEASIBLE': 1},
                    'common_feasible_n': 1, 'policies': {'next_cheaper': {'feasible_n': 2}}}}


def test_changed_counts_and_missing_proof():
    report = build_report(example())
    assert 'Cases: 3.' in report and '1/3' in report
    assert 'UNVERIFIED' in report and '120' not in report and '86' not in report
    assert 'feasible_n' in report


@pytest.mark.parametrize('summary', [{}, {'ALL': {}}, {'ALL': {'n': 0}}])
def test_missing_or_invalid_summary(summary):
    with pytest.raises((KeyError, ValueError)):
        build_report(summary)


def test_audit_failure_and_mismatch():
    summary = example()
    for evidence in ({'status': 'FAIL', 'summary': summary}, {'status': 'PASS', 'summary': {}}):
        with pytest.raises(ValueError, match='Audit failed'):
            build_report(summary, evidence)
    report = build_report(summary, {'status': 'PASS', 'summary': copy.deepcopy(summary)})
    assert 'audit: PASS' in report
    assert 'does not independently certify' in report


def test_missing_cli_input_does_not_create_report(tmp_path):
    result = subprocess.run([sys.executable, '-W', 'error', '-m',
                             'research.procurement_baseline.generate_report',
                             '--input-dir', str(tmp_path)], capture_output=True, text=True)
    assert result.returncode != 0
    assert not (tmp_path / 'REPORT_KO.md').exists()


def test_audit_cli_has_no_resource_warnings(tmp_path):
    root = Path(__file__).resolve().parents[1] / 'research/procurement_baseline'
    source = tmp_path / 'input'
    source.mkdir()
    with zipfile.ZipFile(root / 'provenance/reviewed_bundle.zip') as archive:
        for filename in ('cases.json', 'results.json', 'summary.json', 'spec.json'):
            members = [name for name in archive.namelist() if name.endswith('/' + filename)
                       and 'original' not in name and 'independent' not in name]
            assert len(members) == 1, members
            (source / filename).write_bytes(archive.read(members[0]))
    result = subprocess.run([sys.executable, '-X', 'dev', '-W', 'error', '-m',
                             'research.procurement_baseline.audit_results',
                             '--input-dir', str(source), '--output-dir', str(tmp_path / 'audit')],
                            capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    assert 'ResourceWarning' not in result.stderr
    assert 'Exception ignored' not in result.stderr
    summary = json.loads((source / 'summary.json').read_text(encoding='utf-8'))
    evidence = json.loads((tmp_path / 'audit/independent_checks.json').read_text(encoding='utf-8'))
    report = build_report(summary, evidence)
    assert 'Cases: 120.' in report and '75/120' in report
    assert 'audit: PASS' in report


@pytest.mark.parametrize('kind', ['missing_audit', 'failed_audit', 'changed_summary'])
def test_report_cli_rejects_unusable_evidence(tmp_path, kind):
    summary = example()
    (tmp_path / 'summary.json').write_text(json.dumps(summary), encoding='utf-8')
    audit = {'status': 'FAIL' if kind == 'failed_audit' else 'PASS', 'summary': example()}
    if kind == 'changed_summary':
        audit['summary']['ALL']['common_feasible_n'] = 0
    evidence = tmp_path / 'audit.json'
    if kind != 'missing_audit':
        evidence.write_text(json.dumps(audit), encoding='utf-8')
    result = subprocess.run([sys.executable, '-W', 'error', '-m',
                             'research.procurement_baseline.generate_report',
                             '--input-dir', str(tmp_path), '--audit', str(evidence)],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert not (tmp_path / 'REPORT_KO.md').exists()
