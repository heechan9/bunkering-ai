"""Audit UPA CSVs without changing records or assuming vessel identity/units."""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd


def audit(path):
    raw = path.read_bytes()
    for encoding in ('utf-8-sig', 'cp949'):
        try:
            frame = pd.read_csv(path, encoding=encoding, dtype=str)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError('Unsupported encoding')
    def summarize(f):
        out = {'rows': len(f), 'year_counts': f['입항년도'].value_counts().sort_index().to_dict(), 'periods': {}}
        for start, end in [('예정시작일', '예정종료일'), ('배정일', '배정종료일')]:
            if start not in f or end not in f:
                continue
            a = pd.to_datetime(f[start], format='%Y-%m-%d', errors='coerce')
            b = pd.to_datetime(f[end], format='%Y-%m-%d', errors='coerce')
            days = (b-a).dt.days
            valid = days[days >= 0]
            out['periods'][start + '/' + end] = {
                'negative_rows': int((days < 0).sum()),
                'nonnegative_rows': len(valid),
                'nonnegative_median_calendar_days': float(valid.median()),
                'nonnegative_mean_calendar_days': float(valid.mean()),
                'zero_day_rows': int((days == 0).sum())}
        return out
    dates = {}
    for col in [c for c in frame if c.endswith('일')]:
        t = pd.to_datetime(frame[col], format='%Y-%m-%d', errors='coerce')
        dates[col] = {'missing': int(frame[col].isna().sum()), 'invalid_nonmissing': int((frame[col].notna() & t.isna()).sum()), 'min': str(t.min().date()), 'max': str(t.max().date())}
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'encoding': encoding,
            'columns': frame.columns.tolist(), 'duplicate_excess_rows': int(frame.duplicated().sum()),
            'year_voyage_combinations': len(frame[['입항년도','입항항차']].drop_duplicates()),
            'date_audit': dates, 'all_records': summarize(frame),
            'identical_rows_collapsed_sensitivity_only': summarize(frame.drop_duplicates()),
            'interpretation': 'Collapsed rows are a sensitivity comparison, not confirmed erroneous duplicates. Date differences are calendar days, not measured waiting or pumping hours. No vessel linkage or fuel savings inferred.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--application', type=Path, required=True)
    parser.add_argument('--allocation', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps({'application': audit(args.application), 'allocation': audit(args.allocation)}, ensure_ascii=False, indent=2))
