#!/usr/bin/env python3
"""Fetch two fixed official indicators; never mix statistics into the news feed."""
import json
import math
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'data' / 'open-logistics.json'
WORLD_BANK = 'https://api.worldbank.org/v2/country/RUS/indicator/LP.LPI.OVRL.XQ?format=json&per_page=100'
EUROSTAT = ('https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/'
            'road_go_ta_tott?lang=en&geo=DE&unit=THS_T&tra_type=TOTAL&tra_oper=TOTAL&freq=A&lastTimePeriod=1')
MAX_BYTES = 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_json(url):
    req = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'SCM-News-DataHub/1.0'})
    with build_opener(NoRedirect).open(req, timeout=20) as response:
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError('Response exceeds size limit')
    return json.loads(payload)


def parse_world_bank(data):
    if (not isinstance(data, list) or len(data) != 2 or not isinstance(data[0], dict)
            or data[0].get('pages') != 1 or not isinstance(data[1], list)):
        raise ValueError('Unexpected World Bank response')
    results = []
    for row in data[1]:
        if not isinstance(row, dict):
            raise ValueError('Invalid World Bank record')
        if row.get('countryiso3code') != 'RUS' or row.get('indicator', {}).get('id') != 'LP.LPI.OVRL.XQ':
            raise ValueError('Unexpected World Bank country or indicator')
        value, year = row.get('value'), row.get('date')
        if value is None:
            continue
        if (not isinstance(year, str) or not year.isdigit() or len(year) != 4
                or isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not 1 <= value <= 5):
            raise ValueError('Invalid World Bank observation')
        results.append((int(year), value))
    if not results or len({year for year, _ in results}) != len(results):
        raise ValueError('No valid or unique World Bank observations')
    year, value = max(results)
    return {'period': str(year), 'value': value, 'provider_updated': data[0].get('lastupdated')}


def parse_eurostat(data):
    if (not isinstance(data, dict) or data.get('class') != 'dataset'
            or data.get('extension', {}).get('id') != 'ROAD_GO_TA_TOTT'):
        raise ValueError('Unexpected Eurostat dataset')
    ids = data.get('id')
    required = {'freq': 'A', 'tra_type': 'TOTAL', 'tra_oper': 'TOTAL', 'unit': 'THS_T', 'geo': 'DE'}
    if (not isinstance(ids, list) or set(ids) != set(required) | {'time'}
            or len(ids) != 6 or data.get('size') != [1] * 6):
        raise ValueError('Unexpected Eurostat dimensions')
    dimensions = data.get('dimension', {})
    for key, expected in required.items():
        if dimensions.get(key, {}).get('category', {}).get('index') != {expected: 0}:
            raise ValueError('Unexpected Eurostat dimension: ' + key)
    years = dimensions.get('time', {}).get('category', {}).get('index', {})
    if not isinstance(years, dict) or len(years) != 1:
        raise ValueError('Unexpected Eurostat period')
    year, index = next(iter(years.items()))
    value = data.get('value', {}).get('0')
    status = data.get('status', {}).get('0')
    if (not isinstance(year, str) or len(year) != 4 or not year.isdigit() or index != 0
            or isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0
            or (status is not None and (not isinstance(status, str) or len(status) > 40))):
        raise ValueError('Invalid Eurostat observation')
    return {'period': year, 'value': value, 'status': status, 'provider_updated': data.get('updated')}


def collect(fetch=fetch_json):
    return {'world_bank': parse_world_bank(fetch(WORLD_BANK)),
            'eurostat': parse_eurostat(fetch(EUROSTAT))}


def save(results, path=OUTPUT, now=None):
    # Preserve the date of the saved snapshot if its observations did not change.
    try:
        previous = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        previous = None
    if isinstance(previous, dict) and previous.get('schema_version') == 1 and previous.get('indicators') == results:
        return False
    date = (now or datetime.now(timezone.utc)).date().isoformat()
    content = json.dumps({'schema_version': 1, 'saved_on': date, 'indicators': results}, ensure_ascii=False, indent=2) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as output:
            temp_path = output.name
            output.write(content)
        os.replace(temp_path, path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='validate data without writing files')
    args = parser.parse_args()
    try:
        results = collect()
        if args.check:
            print('Both sources validated; no files written.')
        else:
            print('Snapshot updated.' if save(results) else 'Snapshot unchanged.')
        return 0
    except (OSError, HTTPError, URLError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        print('Collection failed; existing snapshot was not changed.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
