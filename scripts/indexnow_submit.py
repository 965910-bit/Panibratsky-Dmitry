#!/usr/bin/env python3
"""Notify IndexNow of changed, verified sitemap HTML after a successful Pages deploy.

Run only after a Pages event or explicit main-branch recovery. URLs are selected from the
repository allowlist, never from event-supplied text. A failure never submits a
partial batch. The ownership key file is deliberately public, not a secret.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from generate_sitemap import BASE, PAGES, ROOT, PageMetadata
from indexnow_key import KEY
from live_seo_check import has_noindex

ENDPOINT = 'https://api.indexnow.org/indexnow'
MAX_BYTES = 1024 * 1024
NS = '{http://www.sitemaps.org/schemas/sitemap/0.9}'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url, *, token=None, body=None):
    headers = {'User-Agent': 'SCM-News-IndexNow/1.0', 'Accept': 'application/json, text/html, application/xml, text/plain'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
        headers['X-GitHub-Api-Version'] = '2022-11-28'
    if body is not None:
        headers['Content-Type'] = 'application/json; charset=utf-8'
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.build_opener(NoRedirect).open(req, timeout=20) as response:
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError('Response too large')
        return response.status, response.headers, data


def previous_deployment(event, runs):
    """Nearest earlier successful main Pages run, including redeploys of this SHA."""
    current = event['workflow_run']
    now = (current['created_at'], int(current['id']))
    eligible = [run for run in runs
                if run.get('head_branch') == 'main' and run.get('conclusion') == 'success'
                and (run['created_at'], int(run['id'])) < now]
    return max(eligible, key=lambda run: (run['created_at'], int(run['id']))) if eligible else None



def find_previous_deployment(event, api, token, fetch=request):
    """Search bounded small pages: a 100-run response can exceed MAX_BYTES.

    Runs created after a delayed workflow event are skipped, including those in
    intervening pages. Fail closed if the previous run isn't in this window.
    """
    workflow_id = event['workflow_run']['workflow_id']
    for page in range(1, 11):
        url = f'{api}/actions/workflows/{workflow_id}/runs?branch=main&status=success&per_page=20&page={page}'
        _, _, body = fetch(url, token=token)
        runs = json.loads(body)['workflow_runs']
        if not isinstance(runs, list):
            raise ValueError('Invalid workflow runs response')
        previous = previous_deployment(event, runs)
        if previous:
            return previous
        if len(runs) < 20:
            break
    return None


def changed_urls(changed):
    files = set(changed)
    # Do not submit assets, non-canonical aliases, unlisted pages or removals.
    return [BASE + name for name in PAGES if (name or 'index.html') in files]


def validate_live(urls, fetch=request, root=ROOT):
    """Verify ownership, live sitemap and exact deployed bytes before any POST."""
    if not re.fullmatch(r'[a-f0-9]{32}', KEY):
        raise ValueError('Invalid key')
    if (root / (KEY + '.txt')).read_text(encoding='ascii').strip() != KEY:
        raise ValueError('Local key file mismatch')
    status, _, key_body = fetch(BASE + KEY + '.txt')
    if status != 200 or key_body.decode('ascii').strip() != KEY:
        raise ValueError('Published key is unavailable or mismatched')
    status, _, body = fetch(BASE + 'sitemap.xml')
    if status != 200 or b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():
        raise ValueError('Published sitemap unavailable or unsupported')
    doc = ET.fromstring(body)
    actual = [node.text for node in doc.findall(f'{NS}url/{NS}loc')]
    expected = {BASE + page for page in PAGES}
    if doc.tag != NS + 'urlset' or len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError('Published sitemap does not match this deployment')
    if len(urls) != len(set(urls)) or not set(urls).issubset(expected):
        raise ValueError('Unexpected URL set')
    for url in urls:
        status, headers, body = fetch(url)
        name = url[len(BASE):] or 'index.html'
        if status != 200 or body != (root / name).read_bytes():
            raise ValueError('Published page differs from deployed source: ' + url)
        meta = PageMetadata()
        meta.feed(body.decode('utf-8-sig'))
        if meta.canonicals != [url] or meta.canonical_has_variant_attributes or any(map(has_noindex, meta.robots)):
            raise ValueError('Published canonical or robots mismatch: ' + url)
        values = headers.get_all('X-Robots-Tag', []) if hasattr(headers, 'get_all') else [headers.get('X-Robots-Tag', '')]
        if any(map(has_noindex, values)):
            raise ValueError('Published X-Robots-Tag contains noindex: ' + url)


def submit(urls, send=request):
    if not urls:
        return None
    payload = {'host': 'scm-news.ru', 'key': KEY, 'keyLocation': BASE + KEY + '.txt', 'urlList': urls}
    status, _, _ = send(ENDPOINT, body=json.dumps(payload).encode('utf-8'))
    if status not in (200, 202):
        raise ValueError('Unexpected IndexNow status: ' + str(status))
    return status


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()


def run(event, repo, token, fetch=request):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Invalid repository')
    upstream = event['workflow_run']
    if upstream.get('head_branch') != 'main' or upstream.get('conclusion') != 'success':
        raise ValueError('Not a successful main Pages deployment')
    sha = upstream['head_sha']
    if not re.fullmatch(r'[a-f0-9]{40}', sha) or git('rev-parse', 'HEAD') != sha:
        raise ValueError('Checked-out commit differs from deployed commit')
    api = 'https://api.github.com/repos/' + repo
    _, _, body = fetch(api + '/git/ref/heads/main', token=token)
    if json.loads(body)['object']['sha'] != sha:
        print('Main has advanced since this deployment; no submission.')
        return None
    workflow_id = upstream['workflow_id']
    if type(workflow_id) is not int or workflow_id <= 0:
        raise ValueError('Invalid upstream workflow id')
    _, _, body = fetch(api + '/actions/workflows/' + str(workflow_id), token=token)
    workflow = json.loads(body)
    if workflow.get('name') != 'pages-build-deployment' or workflow.get('path') != 'dynamic/pages/pages-build-deployment':
        raise ValueError('Upstream workflow is not GitHub Pages')
    previous = find_previous_deployment(event, api, token, fetch=fetch)
    if not previous:
        print('No earlier successful Pages deployment found; no submission.')
        return None
    before = previous['head_sha']
    if not re.fullmatch(r'[a-f0-9]{40}', before):
        raise ValueError('Invalid previous deployment commit')
    subprocess.run(['git', 'merge-base', '--is-ancestor', before, sha], cwd=ROOT, check=True, capture_output=True)
    changed = git('diff', '--name-only', '--diff-filter=AM', before, sha, '--').splitlines()
    urls = changed_urls(changed)
    if not urls:
        print('No changed canonical HTML pages; no submission.')
        return None
    validate_live(urls, fetch=fetch)
    _, _, body = fetch(api + '/git/ref/heads/main', token=token)
    if json.loads(body)['object']['sha'] != sha:
        print('Main advanced during validation; no submission.')
        return None
    status = submit(urls, send=fetch)
    print(f'IndexNow HTTP {status}: {len(urls)} changed canonical HTML pages submitted; indexing is not guaranteed.')
    return status



def recover(repo, token, baseline, fetch=request):
    """Explicit manual recovery, relative to an operator-selected ancestor.

    This may repeat previously accepted URLs: it has no durable submission log.
    Only current main, a successful Pages build, and verified live pages qualify.
    """
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Invalid repository')
    if not re.fullmatch(r'[a-f0-9]{40}', baseline):
        raise ValueError('Baseline must be a full lowercase commit SHA')
    sha = git('rev-parse', 'HEAD')
    if not re.fullmatch(r'[a-f0-9]{40}', sha):
        raise ValueError('Invalid checked-out commit')
    api = 'https://api.github.com/repos/' + repo
    _, _, body = fetch(api + '/git/ref/heads/main', token=token)
    if json.loads(body)['object']['sha'] != sha:
        raise ValueError('Checkout is not current main')
    _, _, body = fetch(api + '/pages/builds/latest', token=token)
    build = json.loads(body)
    if build.get('status') != 'built' or build.get('commit') != sha:
        raise ValueError('Current main is not the latest successful Pages build')
    subprocess.run(['git', 'merge-base', '--is-ancestor', baseline, sha], cwd=ROOT, check=True, capture_output=True)
    changed = git('diff', '--name-only', '--diff-filter=AM', baseline, sha, '--').splitlines()
    urls = changed_urls(changed)
    if not urls:
        print('No changed canonical HTML pages since baseline; no submission.')
        return None
    validate_live(urls, fetch=fetch)
    _, _, body = fetch(api + '/git/ref/heads/main', token=token)
    if json.loads(body)['object']['sha'] != sha:
        raise ValueError('Main advanced during validation; no submission')
    status = submit(urls, send=fetch)
    print(f'IndexNow recovery HTTP {status}: {len(urls)} verified canonical pages submitted; indexing is not guaranteed.')
    return status


def main():
    try:
        event_name = os.environ.get('GITHUB_EVENT_NAME')
        if event_name == 'workflow_run':
            with open(os.environ['GITHUB_EVENT_PATH'], encoding='utf-8') as source:
                event = json.load(source)
            run(event, os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_TOKEN'])
        elif event_name == 'workflow_dispatch' and os.environ.get('GITHUB_REF') == 'refs/heads/main':
            recover(os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_TOKEN'], os.environ['INDEXNOW_BASE_SHA'])
        else:
            raise ValueError('Unsupported event or branch')
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, ET.ParseError, urllib.error.URLError, subprocess.CalledProcessError):
        print('IndexNow verification or submission failed; inspect deployment, key, upstream status and API availability.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
