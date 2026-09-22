"""Read-only, template-specific AB-LOG review. Never infers supply or timestamps."""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile, BadZipFile

NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
LIMIT = 20 * 1024 * 1024


def read_cells(path: Path) -> dict:
    if path.stat().st_size > LIMIT:
        raise ValueError('Workbook exceeds 20 MB')
    with ZipFile(path) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)) or len(names) > 2000:
            raise ValueError('Duplicate or excessive ZIP entries')
        if sum(i.file_size for i in infos) > LIMIT:
            raise ValueError('Uncompressed workbook exceeds 20 MB')

        def xml(name):
            raw = archive.read(name)
            if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
                raise ValueError('XML entities are not accepted')
            return ET.fromstring(raw)

        strings = []
        if 'xl/sharedStrings.xml' in names:
            strings = [''.join(t.text or '' for t in e.findall('.//s:t', NS)) for e in xml('xl/sharedStrings.xml')]
        relationships = {e.get('Id'): e for e in xml('xl/_rels/workbook.xml.rels')}
        sheets = {}
        for sheet in xml('xl/workbook.xml').findall('s:sheets/s:sheet', NS):
            relation = relationships[sheet.get(REL)]
            if relation.get('TargetMode') == 'External':
                raise ValueError('External sheet relationship')
            target = relation.get('Target', '')
            name = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            if '..' in PurePosixPath(name).parts:
                raise ValueError('Unexpected sheet path')
            cells = {}
            for cell in xml(name).findall('.//s:sheetData/s:row/s:c', NS):
                address = cell.get('r')
                if address in cells:
                    raise ValueError('Duplicate cell')
                value = cell.find('s:v', NS)
                text = value.text if value is not None and value.text else ''
                if cell.get('t') == 's':
                    text = strings[int(text)]
                elif cell.get('t') == 'inlineStr':
                    text = ''.join(t.text or '' for t in cell.findall('.//s:t', NS))
                cells[address] = {'value': text, 'formula': cell.find('s:f', NS) is not None}
            sheets[sheet.get('name')] = cells
        return sheets


def review_cells(sheets: dict, sha256: str) -> dict:
    def raw(sheet, address):
        return sheets.get(sheet, {}).get(address, {}).get('value', '').strip()

    def number(sheet, address):
        cell = sheets.get(sheet, {}).get(address, {})
        if cell.get('formula'):
            raise ValueError(f'{sheet}!{address}: formula requires separate recalculation')
        value = raw(sheet, address)
        if not value:
            raise ValueError(f'{sheet}!{address}: missing quantity')
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError(f'{sheet}!{address}: invalid quantity') from exc
        if not number.is_finite() or number < 0:
            raise ValueError(f'{sheet}!{address}: quantity must be finite and nonnegative')
        return number

    for sheet, cell, expected in [
        ('AB-LOG', 'D4', 'HANBADA'), ('AB-LOG', 'S24', 'D.O(M/T)'),
        ('AB-LOG', 'O26', 'ROB'), ('AB-LOG', 'O41', 'ROB'),
        ('AB-LOG', 'O42', 'CONS'), ('AB-LOG', 'AA6', 'CONSUMPTION(M/T)'),
        ('AB-LOG', 'AA8', 'M/E'), ('AB-LOG', 'AB8', 'G/E'),
        ('AB-LOG', 'AC8', 'BLR'), ('AB-LOG', 'AD8', 'M/E'),
        ('AB-LOG', 'AF8', 'G/E'), ('AB-LOG', 'AH8', 'BLR'),
        ('B FOAM', 'T4', 'Consumption'), ('B FOAM', 'T5', 'M/E'),
        ('B FOAM', 'U5', 'G/E'), ('B FOAM', 'V5', 'Boiler')]:
        if re.sub(r'\s+', '', raw(sheet, cell)) != expected:
            raise ValueError(f'Template mismatch at {sheet}!{cell}')

    def total(sheet, columns, start, end):
        evidence = []
        for column in columns:
            for row in range(start, end + 1):
                address = f'{column}{row}'
                if raw(sheet, address) or sheets[sheet].get(address, {}).get('formula'):
                    evidence.append((address, number(sheet, address)))
        if not evidence:
            raise ValueError(f'{sheet}: no quantities in selected range')
        return sum((v for _, v in evidence), Decimal(0)), len(evidence)

    opening, closing, consumed = [number('AB-LOG', p) for p in ('S26', 'S41', 'S42')]
    aggregate, aggregate_count = total('AB-LOG', ['AA','AB','AC','AD','AF','AH'], 10, 18)
    daily, daily_count = total('B FOAM', ['T','U','V'], 8, 68)
    supply_cells = [f'S{i}' for i in range(27, 41) if raw('AB-LOG', f'S{i}') or sheets['AB-LOG'].get(f'S{i}', {}).get('formula')]
    date = raw('AB-LOG', 'X4')
    voyage = raw('AB-LOG', 'J4')
    if not date or not voyage:
        raise ValueError('Missing record date or voyage identifier')
    delta = opening - consumed - closing
    aggregate_delta = aggregate - consumed
    tol = Decimal('0.000001')  # numeric storage tolerance, never an operating limit
    return {
        'schema': 'hanbada-ab-log-review/v1', 'source_sha256': sha256,
        'record_date': date, 'voyage_id': voyage, 'unit': 'M/T',
        'status': 'review_pending', 'source_kind': 'provided_vessel_record',
        'reported_year': 2025, 'file_year': int(date[:4]) if date[:4].isdigit() else None,
        'year_confirmation': 'pending',
        'opening_rob': str(opening), 'closing_rob': str(closing), 'consumption': str(consumed),
        'supply': None, 'supply_record': 'blank' if not supply_cells else 'present_requires_review',
        'non_bunkering_basis': 'user_relay_of_provider_via_seunghyeon',
        'conditional_balance_residual': str(delta),
        'conditional_balance_status': 'consistent_if_no_supply' if not supply_cells and abs(delta) <= tol else 'review_required',
        'summary_consumption_sum': str(aggregate), 'summary_numeric_cells': aggregate_count,
        'summary_residual': str(aggregate_delta),
        'summary_status': 'internally_consistent' if abs(aggregate_delta) <= tol else 'review_required',
        'daily_selected_sum': str(daily), 'daily_numeric_cells': daily_count,
        'daily_comparison_status': 'held_period_unit_and_aggregation_unconfirmed',
        'numeric_storage_tolerance': str(tol),
        'evidence': {'opening':'AB-LOG!S26','closing':'AB-LOG!S41','consumption':'AB-LOG!S42',
                     'summary':'AB-LOG!AA10:AH18; columns AA,AB,AC,AD,AF,AH',
                     'daily':'B FOAM!T8:V68; populated numeric cells only; notes excluded'},
        'limits': ['No independent measurement validation', 'No real policy or savings validation',
                   'ROB timestamps and consumption derivation unconfirmed',
                   'Blank cells are not observed zeros; selected sums do not prove completeness'],
    }


def review(path: Path) -> dict:
    return review_cells(read_cells(path), hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbook', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = review(args.workbook)
    except (ValueError, KeyError, IndexError, OSError, BadZipFile, ET.ParseError) as exc:
        parser.exit(2, f'AB-LOG review failed: {exc}\n')
    content = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        # Do not overwrite the source or an existing review artifact.
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(content)
    else:
        print(content, end='')


if __name__ == '__main__':
    main()
