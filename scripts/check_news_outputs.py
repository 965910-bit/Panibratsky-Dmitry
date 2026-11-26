#!/usr/bin/env python3
"""Check that the public RSS and HTML snapshot match the committed news data.

Generation happens in a temporary directory, never in the checkout. This is a
consistency check, not a verification of the source, truthfulness, or safety of
all surrounding HTML.
"""
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

import generate_news_pages
import generate_rss

ROOT = Path(__file__).resolve().parent.parent
FILES = ('data/news.json', 'rss.xml', 'trends.html')


def check_outputs(root):
    root = Path(root)
    with tempfile.TemporaryDirectory(prefix='news-output-check-') as directory:
        temporary = Path(directory)
        (temporary / 'data').mkdir()
        for name in FILES:
            shutil.copyfile(root / name, temporary / name)
        old_snapshot_root, old_rss_root = generate_news_pages.ROOT, generate_rss.ROOT
        try:
            generate_news_pages.ROOT = generate_rss.ROOT = temporary
            generate_news_pages.generate()
            generate_rss.generate_rss()
        finally:
            generate_news_pages.ROOT, generate_rss.ROOT = old_snapshot_root, old_rss_root
        return [name for name in ('trends.html', 'rss.xml')
                if (root / name).read_bytes() != (temporary / name).read_bytes()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='checkout to inspect')
    args = parser.parse_args()
    try:
        mismatches = check_outputs(args.root)
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as error:
        print(f'News output check failed: {error}', file=sys.stderr)
        return 1
    if mismatches:
        print('News outputs do not match data/news.json: ' + ', '.join(mismatches), file=sys.stderr)
        return 1
    print('News snapshot and RSS match data/news.json.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
