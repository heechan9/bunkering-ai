"""Render actual summary values; verification requires matching audit evidence."""
import argparse
import json
from pathlib import Path


def build_report(summary, audit=None):
    overall = summary['ALL']
    n = overall['n']
    if not isinstance(n, int) or n <= 0:
        raise ValueError('ALL.n must be a positive integer')
    status = overall['reference_status']
    if sum(status.values()) != n:
        raise ValueError('Reference status counts must sum to ALL.n')
    if audit is not None and (audit.get('status') != 'PASS' or audit.get('summary') != summary):
        raise ValueError('Audit failed or does not match the input summary')
    lines = ['# Synthetic procurement comparison', '',
             'Synthetic STATIC_KNOWN development data with identical full information; '
             'not unused holdout evidence, AI superiority, or realized vessel savings.', '',
             f"Cases: {n}. Reference status: {status}. "
             f"All-policy common feasible: {overall['common_feasible_n']}/{n}.", '',
             ('Independent ledger/summary audit: PASS (matching supplied audit evidence). '
              'This report does not independently certify stop-pattern enumeration.'
              if audit is not None else
              'Verification: UNVERIFIED. No independent audit evidence supplied; '
              'summary values alone do not establish ledger or enumeration agreement.'), '',
             '## Reported aggregates']
    for block, values in summary.items():
        lines += ['', f'### {block}',
                  f"Cases: {values['n']}; reference status: {values['reference_status']}; "
                  f"common feasible: {values['common_feasible_n']}."]
        for policy, data in values['policies'].items():
            lines += ['', f'#### {policy}', '', '| Metric | Reported value |', '|---|---:|']
            for metric, value in data.items():
                lines.append(f'| {metric} | {json.dumps(value, ensure_ascii=False)} |')
    lines += ['', '## Interpretation and evidence',
              'Cost-weighted difference = sum(rule cost - optimum cost) / sum(rule cost) * 100. '
              'Pairwise and all-policy common denominators differ; compare them separately.',
              'Feasible rules being no cheaper than a constrained optimum is expected by construction. '
              'Failed policies are not repaired and failed-ledger costs are excluded from feasible aggregates.',
              'The historical solver counterexample and presolve workaround are documented in '
              'PATCH_NOTES_KO.md and the unchanged reviewed ZIP. They are not a diagnosis of this input run.',
              'This simplified fixed-route, single-grade benchmark does not evaluate forecasts, '
              'route optimization, contracts, quality, tax, credit, or causal operational savings.',
              'Run benchmark and audit_results into new directories; preserve cases.json, results.json, '
              'summary.json, spec.json and environment.json alongside the audit.']
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--audit', type=Path, help='Optional independent_checks.json for this summary')
    args = parser.parse_args()
    output = args.output or args.input_dir / 'REPORT_KO.md'
    if output.exists():
        raise FileExistsError('Report exists; choose a new report path')
    summary = json.loads((args.input_dir / 'summary.json').read_text(encoding='utf-8'))
    audit = json.loads(args.audit.read_text(encoding='utf-8')) if args.audit else None
    report = build_report(summary, audit)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        stream.write(report)


if __name__ == '__main__':
    main()
