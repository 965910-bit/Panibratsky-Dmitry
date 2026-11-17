#!/usr/bin/env python3
"""Read-only quality review of saved open-logistics snapshots; prints JSON to stdout.

Does not fetch, archive, publish, interpolate, or establish provider revisions.
"""
import argparse
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re

SOURCES = {
    'world_bank': {'indicator': 'LP.LPI.OVRL.XQ', 'geography': 'RUS', 'unit': 'LPI score (1–5)',
                   'methodology': 'https://databank.worldbank.org/metadataglossary/world-development-indicators/series/LP.LPI.OVRL.XQ',
                   'terms': 'https://www.worldbank.org/ext/en/legal/terms-conditions/datasets'},
    'eurostat': {'indicator': 'ROAD_GO_TA_TOTT', 'geography': 'DE registered vehicles', 'unit': 'thousand tonnes',
                 'methodology': 'https://ec.europa.eu/eurostat/cache/metadata/en/road_go_esms.htm',
                 'terms': 'https://ec.europa.eu/eurostat/help/copyright-notice'},
}


def no_constant(value):
    raise ValueError('Non-finite JSON number: ' + value)


def load_snapshot(path):
    raw = Path(path).read_bytes()
    if len(raw) > 1024 * 1024:
        raise ValueError('Snapshot exceeds size limit')
    data = json.loads(raw, parse_constant=no_constant)
    if not isinstance(data, dict) or data.get('schema_version') != 1 or type(data.get('schema_version')) is not int:
        raise ValueError('Unsupported snapshot schema')
    saved = data.get('saved_on')
    if not isinstance(saved, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', saved):
        raise ValueError('Invalid saved_on')
    date.fromisoformat(saved)
    indicators = data.get('indicators')
    if not isinstance(indicators, dict) or set(indicators) - set(SOURCES):
        raise ValueError('Invalid indicator set')
    for key, observation in indicators.items():
        if observation is None:
            continue
        if not isinstance(observation, dict):
            raise ValueError(f'{key}: invalid observation')
        period, value = observation.get('period'), observation.get('value')
        if not isinstance(period, str) or not re.fullmatch(r'[0-9]{4}', period) or period == '0000':
            raise ValueError(f'{key}: invalid period')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'{key}: invalid value')
        if not (1 <= value <= 5 if key == 'world_bank' else value >= 0):
            raise ValueError(f'{key}: value outside permitted range')
        for field in ('status', 'provider_updated'):
            val = observation.get(field)
            if val is not None and (not isinstance(val, str) or len(val) > 80):
                raise ValueError(f'{key}: invalid {field}')
    return data, hashlib.sha256(raw).hexdigest()


def review(current_path, previous_path=None):
    current, current_hash = load_snapshot(current_path)
    previous, previous_hash = load_snapshot(previous_path) if previous_path else (None, None)
    if previous and previous['saved_on'] > current['saved_on']:
        raise ValueError('Previous snapshot saved_on is later than current snapshot')
    output = {'schema_version': 1, 'current': {'saved_on': current['saved_on'], 'sha256': current_hash},
              'previous': {'saved_on': previous['saved_on'], 'sha256': previous_hash} if previous else None,
              'limitations': 'Saved snapshots only; no inference about missing years, upstream revisions, statistical comparability or freshness.',
              'indicators': {}}
    for key, metadata in SOURCES.items():
        now = current['indicators'].get(key)
        before = previous['indicators'].get(key) if previous else None
        if now is None:
            state = 'missing_current'
        elif not previous:
            state = 'no_previous_snapshot'
        elif before is None:
            state = 'missing_previous'
        elif now['period'] < before['period']:
            state = 'period_regression'
        elif now['period'] > before['period']:
            state = 'new_period'
        elif (now['value'], now.get('status')) != (before['value'], before.get('status')):
            state = 'same_period_changed'
        else:
            state = 'unchanged_observation'
        output['indicators'][key] = {'source': metadata, 'current': now, 'previous': before, 'comparison': state}
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('current', type=Path, help='current saved JSON snapshot')
    parser.add_argument('--previous', type=Path, help='older saved JSON snapshot, if available')
    parser.add_argument('--require-complete', action='store_true', help='fail if either current observation is missing')
    parser.add_argument('--reject-regression', action='store_true', help='fail if a saved observation period moves backwards')
    args = parser.parse_args()
    try:
        report = review(args.current, args.previous)
        if args.require_complete and any(item['current'] is None for item in report['indicators'].values()):
            raise ValueError('A current observation is missing')
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
        if args.reject_regression and any(item['comparison'] == 'period_regression' for item in report['indicators'].values()):
            raise ValueError('An observation period moved backwards; review before publication')
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError) as error:
        parser.exit(1, f'Snapshot review failed: {error}\n')


if __name__ == '__main__':
    main()
