#!/usr/bin/env python3
"""Summarize a locally supplied Search Console Countries CSV; no network or file writes."""
import argparse
import csv
from datetime import date
import json
from pathlib import Path
import re

MAX_BYTES = 5 * 1024 * 1024
ALIASES = {'country': {'country', 'countries', 'страна', 'страны'},
           'clicks': {'clicks', 'клики'}, 'impressions': {'impressions', 'показы'}}


def read_export(path):
    raw = Path(path).read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError('CSV too large')
    reader = csv.DictReader(raw.decode('utf-8-sig').splitlines())
    headers = reader.fieldnames or []
    names = [item.strip().casefold() for item in headers]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate CSV column names')
    columns = {}
    for key, aliases in ALIASES.items():
        matches = [headers[i] for i, name in enumerate(names) if name in aliases]
        if len(matches) != 1:
            raise ValueError('CSV must contain country, clicks and impressions columns')
        columns[key] = matches[0]
    rows, seen = [], set()
    for row in reader:
        if len(rows) >= 1000 or None in row:
            raise ValueError('Too many or malformed rows')
        country = (row.get(columns['country']) or '').strip()
        # Reject URLs, digits and other data that are not ordinary country labels.
        if not country or len(country) > 100 or any(not (ch.isalpha() or ch in " -.'’()") for ch in country):
            raise ValueError('Invalid country label')
        if country.casefold() in seen:
            raise ValueError('Duplicate country label')
        seen.add(country.casefold())
        numbers = []
        for key in ('clicks', 'impressions'):
            value = (row.get(columns[key]) or '').strip()
            if not re.fullmatch(r'[0-9]+', value):
                raise ValueError('Clicks and impressions must be nonnegative integers')
            numbers.append(int(value))
        rows.append({'country': country, 'clicks': numbers[0], 'impressions': numbers[1]})
    if not rows:
        raise ValueError('Empty country export')
    rows.sort(key=lambda row: (-row['impressions'], row['country'].casefold()))
    return {'clicks': sum(r['clicks'] for r in rows), 'impressions': sum(r['impressions'] for r in rows), 'countries': rows}


def date_arg(value):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError()
        return value
    except ValueError:
        raise argparse.ArgumentTypeError('date must be YYYY-MM-DD')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--start', required=True, type=date_arg)
    parser.add_argument('--end', required=True, type=date_arg)
    args = parser.parse_args()
    if args.start > args.end:
        parser.error('start must not be later than end')
    try:
        result = {'start': args.start, 'end': args.end, 'source': 'Search Console country export supplied by user',
                  'limitations': 'Descriptive export only; geography is not language or evidence of international demand.',
                  'summary': read_export(args.csv)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, UnicodeError, csv.Error) as error:
        parser.exit(1, f'Country export invalid: {error}\n')


if __name__ == '__main__':
    main()
