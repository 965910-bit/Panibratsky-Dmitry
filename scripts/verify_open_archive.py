#!/usr/bin/env python3
"""Verify one raw open-data bundle without network or writes."""
import argparse
import json
from pathlib import Path
from open_logistics_data import verify_archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify_archive(args.bundle), ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError) as error:
        parser.exit(1, f'Archive verification failed: {error}\n')


if __name__ == '__main__':
    main()
