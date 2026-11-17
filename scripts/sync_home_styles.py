#!/usr/bin/env python3
"""Synchronise the homepage's inline CSS with its canonical stylesheet."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- HOME_STYLES_START -->'
END = '<!-- HOME_STYLES_END -->'

def expected():
    css = (ROOT / 'css/executive.css').read_text(encoding='utf-8')
    if '</style' in css.lower():
        raise ValueError('CSS cannot safely be embedded in a style element')
    return f'{START}\n<style>\n{css}\n</style>\n{END}'

def sync(check=False):
    path = ROOT / 'index.html'
    html = path.read_text(encoding='utf-8')
    if html.count(START) != 1 or html.count(END) != 1:
        raise ValueError('Expected exactly one pair of home style markers')
    before, rest = html.split(START, 1)
    _, after = rest.split(END, 1)
    updated = before + expected() + after
    if check:
        if updated != html:
            raise SystemExit('Homepage CSS is out of sync; run python3 scripts/sync_home_styles.py')
        print('Homepage CSS is in sync')
    elif updated != html:
        path.write_text(updated, encoding='utf-8')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    sync(parser.parse_args().check)
