"""CSV structure must fail closed before DictReader-style value overwrites."""
import csv
import hashlib
import json
from pathlib import Path
import pytest
from scripts.report_matched_safety import REQUIRED_COLUMNS, read_safety_csv
from evaluation.matched_safety import matched_safety_report


def write_csv(tmp_path, header, rows):
    path=tmp_path/'audit.csv'
    with path.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.writer(handle); writer.writerow(header); writer.writerows(rows)
    return path


def columns():
    return sorted(REQUIRED_COLUMNS)


@pytest.mark.parametrize('kind', ['duplicate','missing','unknown','empty_name','surplus','truncated','blank_record'])
def test_rejects_ambiguous_structure(tmp_path,kind):
    header=columns();row=['0']*len(header)
    if kind=='duplicate':header.append(header[0]);row.append('different')
    if kind=='missing':header.pop();row.pop()
    if kind=='unknown':header.append('unrecognized');row.append('0')
    if kind=='empty_name':header[0]=''
    if kind=='surplus':row.append('extra')
    if kind=='truncated':row.pop()
    if kind=='blank_record':row=[]
    with pytest.raises(ValueError):read_safety_csv(write_csv(tmp_path,header,[row]))


def test_empty_file_and_unclosed_quote(tmp_path):
    path=tmp_path/'audit.csv';path.write_text('')
    with pytest.raises(ValueError,match='header'):read_safety_csv(path)
    path.write_text(','.join(columns())+'\n"unterminated')
    with pytest.raises(ValueError,match='Malformed CSV'):read_safety_csv(path)


def test_valid_csv_preserves_blank_zero_and_quoted_fields(tmp_path):
    header=columns(); row=['0']*len(header)
    row[header.index('safe_arrival_adjusted_sci')]=''
    row[header.index('policy')]='quoted, policy'
    record=read_safety_csv(write_csv(tmp_path,header,[row]))[0]
    assert record['purchase_sci']=='0'
    assert record['safe_arrival_adjusted_sci']==''
    assert record['policy']=='quoted, policy'


def test_bom_and_reordered_columns_supported(tmp_path):
    header=columns()[::-1];path=write_csv(tmp_path,header,[['0']*len(header)])
    path.write_bytes(b'\xef\xbb\xbf'+path.read_bytes())
    assert set(read_safety_csv(path)[0])==REQUIRED_COLUMNS


def test_stored_report_reproduces_from_source():
    root=Path(__file__).resolve().parents[1]
    source=root/'results/diagnostics/safety_accounting'
    if not source.exists():source=root/'inputs'  # Partial review checkout.
    report=matched_safety_report(read_safety_csv(source/'episodes.csv'),json.loads((source/'manifest.json').read_text()))
    stored=json.loads((root/'web/ocean-lab/public/data/matched-safety-report.json').read_text())
    assert report=={k:v for k,v in stored.items() if k!='input_sha256'}
    assert stored['input_sha256']=={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in ('episodes.csv','manifest.json')}


@pytest.mark.parametrize('kind',['duplicate','surplus'])
def test_cli_writes_no_report_for_malformed_csv(tmp_path,monkeypatch,kind):
    from scripts.report_matched_safety import main
    header=columns();row=['0']*len(header)
    if kind=='duplicate':header.append(header[0]);row.append('1')
    else:row.append('extra')
    path=write_csv(tmp_path,header,[row]);manifest=tmp_path/'manifest.json';manifest.write_text('{}')
    output=tmp_path/'output'
    monkeypatch.setattr('sys.argv',['report_matched_safety.py','--episodes',str(path),'--manifest',str(manifest),'--output-dir',str(output)])
    with pytest.raises(ValueError):main()
    assert not output.exists()
