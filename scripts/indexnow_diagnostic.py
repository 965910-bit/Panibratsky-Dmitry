#!/usr/bin/env python3
"""Read-only IndexNow deployment diagnostic: no submission, no credentials in output."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error

from generate_sitemap import PAGES
from indexnow_key import KEY
import indexnow_submit as indexnow


def diagnose(repo, token, fetch=indexnow.request):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Invalid repository')
    api = 'https://api.github.com/repos/' + repo
    _, _, data = fetch(api + '/git/ref/heads/main', token=token)
    sha = json.loads(data)['object']['sha']
    if not re.fullmatch(r'[a-f0-9]{40}', sha):
        raise ValueError('Invalid main SHA')
    _, _, data = fetch(api + '/pages/builds/latest', token=token)
    build = json.loads(data)
    if build.get('status') != 'built' or build.get('commit') != sha:
        raise ValueError('Latest Pages build is not built from current main')
    _, _, data = fetch(api + '/actions/runs?branch=main&event=dynamic&status=success&per_page=20', token=token)
    runs = json.loads(data)['workflow_runs']
    candidates = [r for r in runs if r.get('name') == 'pages build and deployment'
                  and r.get('head_sha') == sha and r.get('head_branch') == 'main'
                  and r.get('conclusion') == 'success']
    if not candidates:
        raise ValueError('No matching successful Pages run among the latest 20 dynamic runs')
    current = max(candidates, key=lambda r: (r['created_at'], int(r['id'])))
    wid = current['workflow_id']
    if type(wid) is not int or wid <= 0:
        raise ValueError('Invalid workflow id')
    _, _, data = fetch(api + '/actions/workflows/' + str(wid), token=token)
    workflow = json.loads(data)
    if workflow.get('name') != 'pages-build-deployment' or workflow.get('path') != 'dynamic/pages/pages-build-deployment':
        raise ValueError('Workflow identity mismatch')
    previous = indexnow.find_previous_deployment({'workflow_run': current}, api, token, fetch=fetch)
    if not previous:
        raise ValueError('No earlier deployment in diagnostic search window')
    before = previous['head_sha']
    if not re.fullmatch(r'[a-f0-9]{40}', before):
        raise ValueError('Invalid previous SHA')
    subprocess.run(['git', 'merge-base', '--is-ancestor', before, sha], cwd=indexnow.ROOT, check=True, capture_output=True)
    # Obtain exact committed bytes, not this diagnostic branch's local edits.
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name in [KEY + '.txt'] + [p or 'index.html' for p in PAGES]:
            if name.startswith('/') or '..' in Path(name).parts:
                raise ValueError('Unsafe page path')
            data = subprocess.run(['git', 'show', f'{sha}:{name}'], cwd=indexnow.ROOT, check=True, capture_output=True).stdout
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        indexnow.validate_live([indexnow.BASE + p for p in PAGES], fetch=fetch, root=root)
    _, _, data = fetch(api + '/git/ref/heads/main', token=token)
    if json.loads(data)['object']['sha'] != sha:
        raise ValueError('Main changed during diagnostic')
    return current['id'], previous['id'], len(PAGES)


def main():
    stage = 'starting'
    # Log only fixed URLs, status codes and error class. Never echo response
    # bodies, Authorization or tokens into public Actions annotations.
    def safe_fetch(url, **kwargs):
        nonlocal stage
        stage = ('GitHub API' if url.startswith('https://api.github.com/') else
                 'public key' if url.endswith(KEY + '.txt') else
                 'public sitemap' if url.endswith('/sitemap.xml') else 'public canonical page')
        return indexnow.request(url, **kwargs)
    try:
        current, previous, count = diagnose(os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_TOKEN'], fetch=safe_fetch)
        print(f'::notice title=IndexNow read-only diagnostic::Current Pages run {current}; prior run {previous}; {count} live canonical pages match source. No submission sent.')
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError, urllib.error.URLError) as exc:
        detail = str(exc) if type(exc) is ValueError else type(exc).__name__
        detail = detail.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')[:250]
        print(f'::error title=IndexNow read-only diagnostic::{stage}: {detail}. No submission sent.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
