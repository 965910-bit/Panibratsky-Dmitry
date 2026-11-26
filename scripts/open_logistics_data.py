#!/usr/bin/env python3
"""Fetch two fixed official indicators; never mix statistics into the news feed."""
import json
import hashlib
import shutil
import math
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from run_summary import report

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'data' / 'open-logistics.json'
WORLD_BANK = 'https://api.worldbank.org/v2/country/RUS/indicator/LP.LPI.OVRL.XQ?format=json&per_page=100'
EUROSTAT = ('https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/'
            'road_go_ta_tott?lang=en&geo=DE&unit=THS_T&tra_type=TOTAL&tra_oper=TOTAL&freq=A&lastTimePeriod=1')
MAX_BYTES = 1024 * 1024
SOURCES = {'world_bank': WORLD_BANK, 'eurostat': EUROSTAT}
TERMS = {'world_bank': 'https://www.worldbank.org/ext/en/legal/terms-conditions/datasets',
         'eurostat': 'https://ec.europa.eu/eurostat/help/copyright-notice'}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_json(url, capture=None):
    req = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'SCM-News-DataHub/1.0'})
    with build_opener(NoRedirect).open(req, timeout=20) as response:
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError('Response exceeds size limit')
    parsed = json.loads(payload)
    if capture is not None:
        capture[url] = payload
    return parsed


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


def verify_archive(path):
    """Rebuild observations from stored raw bytes and verify content hashes; no network/writes."""
    path = Path(path)
    manifest_path = path / 'manifest.json'
    if manifest_path.stat().st_size > MAX_BYTES:
        raise ValueError('Manifest exceeds size limit')
    manifest = json.loads(manifest_path.read_bytes())
    if (not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int
            or manifest['schema_version'] != 1 or manifest.get('transform_version') != 1
            or manifest.get('sources') != SOURCES or manifest.get('terms') != TERMS):
        raise ValueError('Unexpected archive manifest')
    timestamp = datetime.fromisoformat(manifest['captured_at_utc'])
    if timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
        raise ValueError('Archive timestamp must be UTC')
    raw = {}
    for key, url in SOURCES.items():
        source_path = path / (key + '.json')
        if source_path.stat().st_size > MAX_BYTES:
            raise ValueError('Archived response exceeds size limit')
        raw[url] = source_path.read_bytes()
    hashes = {key: hashlib.sha256(raw[url]).hexdigest() for key, url in SOURCES.items()}
    bundle = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if path.name != bundle or manifest.get('hashes') != hashes:
        raise ValueError('Archive hash mismatch')
    observations = collect(lambda url: json.loads(raw[url]))
    if manifest.get('observations') != observations:
        raise ValueError('Archive observations do not match raw responses')
    return observations


def archive_bundle_id(captured):
    hashes = {key: hashlib.sha256(captured[url]).hexdigest() for key, url in SOURCES.items()}
    return hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def archive_capture(captured, results, directory, now=None):
    """Archive exact public API bodies once per distinct pair, without overwriting prior vintages."""
    sources = SOURCES
    terms = TERMS
    if set(captured) != set(sources.values()):
        raise ValueError('Incomplete raw capture')
    # Re-parse the exact archived bytes: do not rely on unrelated caller-supplied observations.
    checked = collect(lambda url: json.loads(captured[url]))
    if checked != results:
        raise ValueError('Raw capture does not match collected observations')
    hashes = {key: hashlib.sha256(captured[url]).hexdigest() for key, url in sources.items()}
    bundle = archive_bundle_id(captured)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / bundle
    if target.exists():
        if verify_archive(target) != results or any((target / (key + '.json')).read_bytes() != captured[url] for key, url in sources.items()):
            raise ValueError('Existing archive differs from capture')
        return False
    temporary = Path(tempfile.mkdtemp(prefix='.capture-', dir=directory))
    try:
        for key, url in sources.items():
            (temporary / (key + '.json')).write_bytes(captured[url])
        timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
        manifest = {'schema_version': 1, 'transform_version': 1, 'captured_at_utc': timestamp, 'sources': sources,
                    'terms': terms, 'hashes': hashes, 'observations': results}
        (temporary / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        # Atomic directory rename; fail rather than alter a competing/existing archive.
        os.rename(temporary, target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='validate data without writing files')
    parser.add_argument('--archive-dir', type=Path, help='archive exact API responses when updating')
    parser.add_argument('--review-history-dir', type=Path, help='compare archived World Bank vintages before saving')
    args = parser.parse_args()
    if args.check and (args.archive_dir or args.review_history_dir):
        parser.error('--check cannot write or review an archive')
    if args.review_history_dir and not args.archive_dir:
        parser.error('--review-history-dir requires --archive-dir')
    try:
        captured = {}
        results = collect(lambda url: fetch_json(url, captured)) if args.archive_dir else collect()
        if args.check:
            report('✅ Открытые данные: оба источника проверены; режим проверки без записи.')
        else:
            if args.archive_dir:
                archived = archive_capture(captured, results, args.archive_dir)
                report('Открытые данные: новый исходный ответ сохранён в архив.' if archived else 'Открытые данные: такой исходный ответ уже есть в архиве.')
                if args.review_history_dir:
                    from open_history_review import report as history_report
                    comparison = history_report(args.archive_dir / archive_bundle_id(captured), args.review_history_dir)
                    print(json.dumps(comparison, ensure_ascii=False))
            changed = save(results)
            report('Открытые данные: снимок изменён; это ещё не подтверждение публикации.' if changed else 'Открытые данные: наблюдения снимка не изменились; новый архив при этом возможен.')
        return 0
    except (OSError, HTTPError, URLError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        report('❌ Открытые данные: сбор или проверка завершились ошибкой; успешная публикация не подтверждена.')
        print('Collection failed; existing snapshot was not changed.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
