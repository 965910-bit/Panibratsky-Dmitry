#!/usr/bin/env python3
"""Compare historical World Bank observations in two verified raw archive vintages."""
import argparse
from datetime import datetime
import json
from pathlib import Path

from open_logistics_data import verify_archive


def history(archive):
    archive = Path(archive)
    verify_archive(archive)
    manifest = json.loads((archive / 'manifest.json').read_text(encoding='utf-8'))
    timestamp = datetime.fromisoformat(manifest['captured_at_utc'])
    data = json.loads((archive / 'world_bank.json').read_bytes())
    # verify_archive has validated all non-null rows, years and uniqueness.
    values = {row['date']: row['value'] for row in data[1] if row['value'] is not None}
    return timestamp, values


def compare(before, after):
    """Missing only means a previously observed value disappeared, not an annual gap."""
    records = []
    for year in sorted(set(before) | set(after)):
        old, new = before.get(year), after.get(year)
        state = ('added' if year not in before else 'removed' if year not in after
                 else 'revised' if old != new else 'unchanged')
        records.append({'period': year, 'previous': old, 'current': new, 'status': state})
    return records


def report(current, history_dir):
    current = Path(current)
    current_at, after = history(current)
    candidates = []
    for path in sorted(Path(history_dir).iterdir()) if Path(history_dir).exists() else []:
        if path.resolve() == current.resolve():
            continue
        captured, values = history(path)
        if captured < current_at:
            candidates.append((captured, path.name, values))
    if not candidates:
        return {'current_archive': current.name, 'baseline': None, 'records': [],
                'note': 'No earlier verified archive; no historical comparison.'}
    captured, name, before = max(candidates, key=lambda item: (item[0], item[1]))
    return {'current_archive': current.name, 'baseline': name,
            'baseline_captured_at': captured.isoformat(), 'records': compare(before, after),
            'note': 'Missing means a previously observed value disappeared; changes may be revisions or corrections. Eurostat full history is not captured.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('current', type=Path)
    parser.add_argument('--history-dir', required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(report(args.current, args.history_dir), ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError) as error:
        parser.exit(1, f'History review failed: {error}\n')


if __name__ == '__main__':
    main()
