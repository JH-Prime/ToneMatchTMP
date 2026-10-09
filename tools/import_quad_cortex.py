"""Read the official factual inventory; emit JSON to stdout for reviewed import.

Never runs at application startup. No accounts, licenses or hardware are accessed.
"""
from html.parser import HTMLParser
import argparse
from datetime import date
import hashlib
import json
import re
from urllib.request import urlopen

SOURCE_URL = 'https://neuraldsp.com/device-list'


class _Tables(HTMLParser):
    def __init__(self):
        """공식 표의 셀과 구역 이름만 수집하는 파서를 초기화한다."""
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.section = None
        self.rows = []
        self.row = []
        self.cell = None
        self.header = False

    def handle_starttag(self, tag, attrs):
        """표·행·셀의 시작을 추적한다."""
        if tag == 'table':
            self.section = dict(attrs).get('aria-label')
            self.rows = []
        elif self.section and tag == 'tr':
            self.row = []
        elif self.section and tag in ('th', 'td'):
            self.cell = []
            self.header = tag == 'th'

    def handle_data(self, data):
        """현재 셀 안의 텍스트만 모은다."""
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        """완성된 셀과 행을 정리하고 표를 보관한다."""
        if self.section and tag in ('th', 'td') and self.cell is not None:
            text = ''.join(self.cell).strip()
            if self.header:
                text = text.removesuffix('i').strip()
            self.row.append(re.sub(r'\s+', ' ', text))
            self.cell = None
        elif self.section and tag == 'tr' and self.row:
            self.rows.append(self.row)
        elif tag == 'table' and self.section:
            self.tables.append((self.section, self.rows))
            self.section = None


def parse_device_list(html):
    """공식 목록을 검증하여 네이티브·캡처·플러그인·미출시 항목으로 나눈다."""
    parser = _Tables()
    parser.feed(html)
    records, seen = [], set()
    for section, rows in parser.tables:
        announced = section == 'Announced devices that have not yet been released'
        if announced and rows:
            rows[0] = [{'Device Category': 'Device category', 'Based On': 'Based on', 'Device Name': 'Name'}.get(h, h) for h in rows[0]] + ['Added in CorOS']
            rows[1:] = [cells + [''] for cells in rows[1:]]
        if not rows or not {'Name', 'Added in CorOS'} <= set(rows[0]):
            raise ValueError(f'Unsupported inventory headers: {section}')
        kind = 'announced' if announced else 'plugin' if section == 'Plugin devices' else 'capture_v2' if section == 'Neural Captures V2' else 'capture_v1' if section == 'Neural Captures V1' else 'native'
        for cells in rows[1:]:
            if len(cells) != len(rows[0]):
                raise ValueError(f'Incomplete inventory row: {section}')
            row = dict(zip(rows[0], cells))
            category = row.get('Device category', section)
            name, version = row['Name'], row['Added in CorOS']
            required = row.get('Required plugin', '')
            if not name or not category or (not announced and not re.fullmatch(r'\d+\.\d+\.\d+', version)) or (kind == 'plugin' and not required):
                raise ValueError(f'Invalid inventory row: {section}/{name}')
            identity = '\x1f'.join((kind, category, name, required))
            if identity in seen:
                raise ValueError(f'Duplicate inventory row: {section}/{name}')
            seen.add(identity)
            records.append(dict(id=hashlib.sha256(identity.encode()).hexdigest()[:16],
                                kind=kind, category=category, name=name,
                                based_on=row.get('Based on', ''), added_in=version or None,
                                previous_name=row.get('Previous name', ''),
                                updated_in=row.get('Updated in CorOS', ''),
                                replaces=row.get('Replaces', ''), required_plugin=required))
    if not records:
        raise ValueError('No device inventory found')
    return records


if __name__ == '__main__':
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument('--retrieved', required=True, type=date.fromisoformat,
                           help='Reviewed retrieval date in the user timezone (YYYY-MM-DD)')
    options = arguments.parse_args()
    with urlopen(SOURCE_URL, timeout=30) as response:
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise ValueError('Inventory response exceeds import limit')
    print(json.dumps(dict(schema='tonematch-qc-catalog/v1', source_url=SOURCE_URL,
                          retrieved=options.retrieved.isoformat(), source_sha256=hashlib.sha256(raw).hexdigest(),
                          devices=parse_device_list(raw.decode('utf-8'))), ensure_ascii=True, indent=2))
