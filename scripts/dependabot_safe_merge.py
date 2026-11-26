#!/usr/bin/env python3
"""Select only tightly constrained Dependabot updates and ask GitHub to merge.

Runs from trusted main, never checks out or executes pull-request code. GitHub's
active ruleset remains authoritative; failures are not bypassed. Only one
review-free, patch-level playwright-core update can be merged per execution.
"""
import base64
import copy
import json
import os
import re
import subprocess
import sys

from publication_pr import api, policy

DEP = 'playwright-core'
FILES = {'package.json', 'package-lock.json'}
VERSION = re.compile(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)\Z')


def allowed_change(base_package, new_package, base_lock, new_lock):
    """Reject all changes except an exact patch upgrade of one dev dependency."""
    before = base_package.get('devDependencies', {}).get(DEP)
    after = new_package.get('devDependencies', {}).get(DEP)
    a, b = VERSION.fullmatch(before or ''), VERSION.fullmatch(after or '')
    if not a or not b:
        return False
    old, new = tuple(map(int, a.groups())), tuple(map(int, b.groups()))
    if old[:2] != new[:2] or new[2] <= old[2]:
        return False
    old_package, next_package = copy.deepcopy(base_package), copy.deepcopy(new_package)
    del old_package['devDependencies'][DEP]
    del next_package['devDependencies'][DEP]
    if old_package != next_package:
        return False
    old_lock, next_lock = copy.deepcopy(base_lock), copy.deepcopy(new_lock)
    try:
        old_root = old_lock['packages']['']['devDependencies'].pop(DEP)
        new_root = next_lock['packages']['']['devDependencies'].pop(DEP)
        old_entry = old_lock['packages'].pop('node_modules/' + DEP)
        new_entry = next_lock['packages'].pop('node_modules/' + DEP)
    except (KeyError, TypeError):
        return False
    if old_root != before or new_root != after or old_lock != next_lock:
        return False
    expected_url = f'https://registry.npmjs.org/playwright-core/-/playwright-core-{after}.tgz'
    if not (old_entry.get('version') == before and old_entry.get('dev') is True
            and new_entry.get('version') == after and new_entry.get('dev') is True
            and new_entry.get('resolved') == expected_url and isinstance(new_entry.get('integrity'), str)
            and new_entry['integrity'].startswith('sha512-')):
        return False
    # A patch may change only the version, tarball URL and integrity. A new
    # install hook, dependency or engine requirement always needs human review.
    for entry in (old_entry, new_entry):
        for key in ('version', 'resolved', 'integrity'):
            entry.pop(key, None)
    return old_entry == new_entry


def read_json_at(repo, path, sha):
    content = api(f'repos/{repo}/contents/{path}?ref={sha}')
    if content.get('encoding') != 'base64' or content.get('type') != 'file':
        raise ValueError('Unexpected GitHub content response')
    raw = base64.b64decode(content['content'], validate=False)
    if len(raw) > 3 * 1024 * 1024:
        raise ValueError('Dependency file too large')
    return json.loads(raw)


def eligible(repo, pr):
    head = pr.get('head') or {}
    base = pr.get('base') or {}
    if (pr.get('state') != 'open' or pr.get('draft') is not False
            or pr.get('user', {}).get('login') != 'dependabot[bot]'
            or base.get('ref') != 'main' or head.get('repo', {}).get('full_name') != repo
            or pr.get('mergeable') is not True or pr.get('mergeable_state') != 'clean'):
        return False
    base_sha, head_sha = base.get('sha', ''), head.get('sha', '')
    if not all(re.fullmatch(r'[0-9a-f]{40}', s) for s in (base_sha, head_sha)):
        return False
    if api(f'repos/{repo}/branches/main')['commit']['sha'] != base_sha:
        return False
    pages = api(f'repos/{repo}/pulls/{pr["number"]}/files?per_page=100', '--paginate', '--slurp')
    files = [entry for page in pages for entry in page]
    if len(files) != 2 or {item.get('filename') for item in files} != FILES:
        return False
    if any(item.get('status') != 'modified' for item in files):
        return False
    old_package = read_json_at(repo, 'package.json', base_sha)
    new_package = read_json_at(repo, 'package.json', head_sha)
    old_lock = read_json_at(repo, 'package-lock.json', base_sha)
    new_lock = read_json_at(repo, 'package-lock.json', head_sha)
    return allowed_change(old_package, new_package, old_lock, new_lock)


def main():
    try:
        repo = os.environ['GITHUB_REPOSITORY']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) or not os.environ.get('GH_TOKEN'):
            raise ValueError('Missing repository or app token')
        policy(repo)
        pages = api(f'repos/{repo}/pulls?state=open&per_page=100', '--paginate', '--slurp')
        for item in (item for page in pages for item in page):
            if item.get('user', {}).get('login') != 'dependabot[bot]':
                continue
            number = item.get('number')
            if type(number) is not int or number <= 0:
                raise ValueError('Invalid PR number')
            pr = api(f'repos/{repo}/pulls/{number}')
            if not eligible(repo, pr):
                continue
            head = pr['head']['sha']
            policy(repo)
            # Explicit PR number and head match. GitHub still enforces all branch rules.
            subprocess.run(['gh', 'pr', 'merge', str(number), '--merge', '--match-head-commit', head,
                            '--repo', repo], check=True)
            print(f'GitHub merged eligible Dependabot PR #{number}.')
            return 0
        print('No eligible, fully checked Dependabot patch PRs.')
        return 0
    except (KeyError, ValueError, TypeError, AttributeError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f'Dependabot reconciliation failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
