#!/usr/bin/env python3
"""Check archived public captures and their correspondence to a saved snapshot.

No network or writes. Hash consistency does not prove authenticity or freshness.
"""
import argparse
import re
import sys
from pathlib import Path

from open_data_review import load_snapshot
from open_logistics_data import verify_archive

ROOT = Path(__file__).resolve().parent.parent
FILES = {'manifest.json', 'world_bank.json', 'eurostat.json'}


def check(snapshot, archive_root):
    snapshot = load_snapshot(snapshot)[0]
    archive_root = Path(archive_root)
    if archive_root.is_symlink() or not archive_root.is_dir():
        raise ValueError('Archive directory missing or is a symlink')
    bundles = list(archive_root.iterdir())
    if not bundles:
        raise ValueError('No archived captures')
    matching = False
    for bundle in sorted(bundles):
        if bundle.is_symlink() or not bundle.is_dir() or not re.fullmatch(r'[0-9a-f]{64}', bundle.name):
            raise ValueError('Invalid archive entry: ' + bundle.name)
        entries = list(bundle.iterdir())
        if {item.name for item in entries} != FILES:
            raise ValueError('Unexpected archive files: ' + bundle.name)
        if any(item.is_symlink() or not item.is_file() for item in entries):
            raise ValueError('Archive must contain only regular files: ' + bundle.name)
        observations = verify_archive(bundle)
        if observations == snapshot['indicators']:
            matching = True
    if not matching:
        raise ValueError('Snapshot does not match any verified capture')
    return len(bundles)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=ROOT / 'data/open-logistics.json')
    parser.add_argument('--archives', type=Path, default=ROOT / 'data/open-logistics-archives')
    args = parser.parse_args()
    try:
        count = check(args.snapshot, args.archives)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError, OverflowError) as error:
        print(f'Open-data archive check failed: {error}', file=sys.stderr)
        return 1
    print(f'{count} capture(s) verified; snapshot matches a capture. Freshness and authenticity not established.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
