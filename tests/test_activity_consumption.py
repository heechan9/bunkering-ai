import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('activity', Path(__file__).parents[1] / 'scripts/review_activity_consumption.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def run(tmp_path, rows):
    path = tmp_path / 'input.csv'
    path.write_text(','.join(m.FIELDS) + '\n' + rows)
    return m.review(path)


def test_weighted_rate_and_unit_separation(tmp_path):
    r = run(tmp_path, 'a,transit,2,4,t,log1\nb,transit,8,8,t,log2\nc,transit,1,9,kL,log3\n')
    assert r['groups'][0]['consumption_per_hour'] == 1.2
    assert r['groups'][1]['consumption_per_hour'] == 9


def test_missing_and_mixed_not_assigned_rates(tmp_path):
    r = run(tmp_path, 'a,mixed,24,8,t,log1\nb,unknown,,3,t,log2\nc,berthed,2,,t,log3\n')
    assert all(g['consumption_per_hour'] is None for g in r['groups'])
    assert r['groups'][2]['missing_consumption_records'] == 1


@pytest.mark.parametrize('row', ['a,transit,0,2,t,log', 'a,transit,2,nan,t,log',
    'a,transit,-1,2,t,log', 'a,transit,1,2,kg,log', 'a,transit,1,2,t,',
    'a,transit,1,2,t,log\na,transit,1,2,t,log', 'a,transit,1,-2,t,log'])
def test_invalid_records_rejected(tmp_path, row):
    with pytest.raises(ValueError):
        run(tmp_path, row)
