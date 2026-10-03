"""Apply activity review to existing public aggregates, without inventing labels."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('activity', ROOT / 'scripts/review_activity_consumption.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def main():
    source = ROOT / 'results/real_voyage/hanbada_review.json'
    raw = source.read_bytes()
    data = json.loads(raw)
    out = Path(__file__).parent
    outputs = []
    for name, value, unit, field in [
        ('rob_mass', data['consumption'], 't', 'consumption'),
        ('daily_volume', data['daily_selected_sum'], 'kL', 'daily'),
    ]:
        path = out / f'hanbada_{name}_input.csv'
        with path.open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(m.FIELDS)
            writer.writerow([name, 'unknown', '', value, unit,
                f'results/real_voyage/hanbada_review.json;{data["evidence"][field]}'])
        result = m.review(path)
        result['aggregate_source_sha256'] = hashlib.sha256(raw).hexdigest()
        result['workbook_sha256_from_existing_review'] = data['source_sha256']
        result['source_scope'] = 'existing_public_aggregate_not_original_workbook_reexecution'
        result['interpretation'] = ('ROB difference; not independently measured consumption' if name == 'rob_mass'
                                    else 'Selected populated volume cells; completeness and period alignment unresolved')
        result['policy_training_eligible'] = False
        target = out / f'hanbada_{name}_review.json'
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        outputs.append(result)
    assert all(g['consumption_per_hour'] is None for r in outputs for g in r['groups'])
    assert all(not r['policy_training_eligible'] for r in outputs)
    print('2 public aggregates reviewed separately; 0 activity-specific rates; training held')


if __name__ == '__main__':
    main()
