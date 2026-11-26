#!/usr/bin/env python3
"""Offline, fail-closed path/history check for a proposed data-only Git commit.

This is a building block, not a publisher: it never pushes, opens or merges a
PR, or reads credentials. It does not validate content, source or freshness.
Run only trusted code, not a copy supplied by an untrusted candidate commit.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

NEWS = {'data/news.json', 'trends.html', 'sitemap.xml', 'rss.xml'}
ARCHIVE = re.compile(r'data/open-logistics-archives/[0-9a-f]{64}/(?:manifest|world_bank|eurostat)\.json\Z')


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=True)
    return result.stdout


def commit_oid(repo, value):
    if not re.fullmatch(r'[0-9a-f]{40}', value):
        raise ValueError('Commit must be a full lowercase 40-character SHA')
    result = git(repo, 'rev-parse', '--verify', value + '^{commit}').decode('ascii').strip()
    if result != value:
        raise ValueError('Expected a commit SHA, not a tag')
    return result


def mode(repo, oid, path):
    result = git(repo, 'ls-tree', '-z', oid, '--', path)
    if not result:
        return None
    records = result.rstrip(b'\0').split(b'\0')
    if len(records) != 1:
        raise ValueError('Ambiguous tree entry')
    meta, found_path = records[0].split(b'\t', 1)
    if found_path.decode('utf-8') != path:
        raise ValueError('Unexpected tree entry')
    parts = meta.split(b' ')
    return (parts[0], parts[1])


def check(repo, base, candidate, kind):
    if kind not in ('news', 'open-data'):
        raise ValueError('Unknown publication kind')
    base = commit_oid(repo, base)
    candidate = commit_oid(repo, candidate)
    parents = git(repo, 'rev-list', '--parents', '-n', '1', candidate).decode('ascii').split()
    if parents != [candidate, base]:
        raise ValueError('Candidate must have exactly the expected base as its sole parent')
    parts = git(repo, 'diff-tree', '--no-commit-id', '--name-status', '-r', '--no-renames', '-z',
                base, candidate).split(b'\0')
    if parts[-1] != b'':
        raise ValueError('Invalid diff output')
    parts.pop()
    if not parts or len(parts) % 2:
        raise ValueError('Candidate must contain changes')
    changed = []
    for index in range(0, len(parts), 2):
        status = parts[index].decode('ascii')
        path = parts[index + 1].decode('utf-8')
        if kind == 'news':
            if path not in NEWS or status != 'M':
                raise ValueError('Unexpected news change: ' + path)
        elif path == 'data/open-logistics.json':
            if status != 'M':
                raise ValueError('Unexpected snapshot change')
        elif not ARCHIVE.fullmatch(path) or status != 'A':
            raise ValueError('Unexpected open-data change: ' + path)
        if mode(repo, candidate, path) != (b'100644', b'blob'):
            raise ValueError('Candidate contains a non-regular or executable file: ' + path)
        if status == 'M' and mode(repo, base, path) != (b'100644', b'blob'):
            raise ValueError('Base contains a non-regular or executable file: ' + path)
        changed.append(path)
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--base', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--kind', required=True, choices=['news', 'open-data'])
    args = parser.parse_args()
    try:
        paths = check(args.repo, args.base, args.candidate, args.kind)
    except (ValueError, UnicodeError, OSError, subprocess.CalledProcessError) as error:
        print(f'Publication candidate rejected: {error}', file=sys.stderr)
        return 1
    print(f'Candidate path/history check passed for {len(paths)} file(s); content is not verified.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
