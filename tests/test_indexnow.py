from email.message import Message
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import indexnow_submit as indexnow


class IndexNowTests(unittest.TestCase):
    def test_select_only_changed_allowlisted_canonical_pages(self):
        self.assertEqual(indexnow.changed_urls(['index.html', 'about.html', 'private.html', 'index.html', 'sitemap.xml']),
                         [indexnow.BASE, indexnow.BASE + 'about.html'])
        self.assertEqual(indexnow.changed_urls(['js/foo.js', 'README.md']), [])

    def test_select_latest_older_successful_deploy(self):
        event = {'workflow_run': {'id': 5, 'created_at': '2026-11-17T12:00:00Z', 'head_sha': 'a' * 40}}
        def run(id, branch, status, sha):
            return {'id': id, 'created_at': '2026-11-17T11:00:00Z', 'head_branch': branch, 'conclusion': status, 'head_sha': sha * 40}
        runs = [run(1, 'main', 'success', 'b'), run(2, 'other', 'success', 'c'), run(3, 'main', 'failure', 'd'), run(4, 'main', 'success', 'e')]
        self.assertEqual(indexnow.previous_deployment(event, runs)['id'], 4)
        self.assertIsNone(indexnow.previous_deployment(event, []))
        runs.append(run(7, 'main', 'success', 'a'))
        self.assertEqual(indexnow.previous_deployment(event, runs)['id'], 7)

    def test_previous_deploy_paginates_and_fails_closed_when_absent(self):
        current = {'workflow_run': {'id': 100, 'created_at': '2026-11-17T12:00:00Z', 'head_sha': 'a' * 40, 'workflow_id': 9}}
        later = [{'id': n, 'created_at': '2026-11-17T13:00:00Z', 'head_branch': 'main', 'conclusion': 'success', 'head_sha': 'c' * 40} for n in range(20)]
        earlier = {'id': 3, 'created_at': '2026-11-17T11:00:00Z', 'head_branch': 'main', 'conclusion': 'success', 'head_sha': 'b' * 40}
        calls = []
        def fetch(url, **kw):
            calls.append(url)
            rows = later if 'page=1' in url else [earlier]
            return 200, {}, json.dumps({'workflow_runs': rows}).encode()
        self.assertEqual(indexnow.find_previous_deployment(current, 'https://api.github.com/repos/a/b', 'token', fetch=fetch), earlier)
        self.assertEqual(len(calls), 2)
        self.assertIn('per_page=20&page=1', calls[0])
        self.assertIn('per_page=20&page=2', calls[1])
        self.assertIsNone(indexnow.find_previous_deployment(current, 'x', 'token', fetch=lambda *a, **kw: (200, {}, b'{"workflow_runs":[]}')))
        calls.clear()
        def no_match(url, **kw):
            calls.append(url)
            return 200, {}, json.dumps({'workflow_runs': later}).encode()
        self.assertIsNone(indexnow.find_previous_deployment(current, 'x', 'token', fetch=no_match))
        self.assertEqual(len(calls), 10)

    def test_live_verification_requires_matching_key_sitemap_and_bytes(self):
        headers = Message()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / (indexnow.KEY + '.txt')).write_text(indexnow.KEY)
            html = ('<html><head><link rel="canonical" href="' + indexnow.BASE + '"></head></html>').encode()
            (root / 'index.html').write_bytes(html)
            sitemap = ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
                       ''.join('<url><loc>' + indexnow.BASE + p + '</loc></url>' for p in indexnow.PAGES) + '</urlset>').encode()
            replies = {indexnow.BASE + indexnow.KEY + '.txt': indexnow.KEY.encode(), indexnow.BASE + 'sitemap.xml': sitemap, indexnow.BASE: html}
            def fetch(url): return 200, headers, replies[url]
            indexnow.validate_live([indexnow.BASE], fetch=fetch, root=root)
            replies[indexnow.BASE] = html + b'changed'
            with self.assertRaisesRegex(ValueError, 'differs'): indexnow.validate_live([indexnow.BASE], fetch=fetch, root=root)
            replies[indexnow.BASE] = html
            headers['X-Robots-Tag'] = 'noindex'
            with self.assertRaisesRegex(ValueError, 'noindex'): indexnow.validate_live([indexnow.BASE], fetch=fetch, root=root)
            headers.replace_header('X-Robots-Tag', 'index')
            replies[indexnow.BASE + indexnow.KEY + '.txt'] = b'wrong'
            with self.assertRaisesRegex(ValueError, 'key'): indexnow.validate_live([indexnow.BASE], fetch=fetch, root=root)

    def test_submit_status_and_no_empty_post(self):
        calls = []
        def send(url, *, body):
            calls.append((url, json.loads(body)))
            return 202, {}, b''
        self.assertIsNone(indexnow.submit([], send=send))
        self.assertEqual(indexnow.submit([indexnow.BASE], send=send), 202)
        self.assertEqual(calls[0][0], indexnow.ENDPOINT)
        self.assertEqual(calls[0][1]['urlList'], [indexnow.BASE])
        with self.assertRaises(ValueError):
            indexnow.submit([indexnow.BASE], send=lambda *a, **kw: (429, {}, b''))

    def test_end_to_end_mocked_run_and_stale_deployment(self):
        sha, previous = 'a' * 40, 'b' * 40
        event = {'workflow_run': {'id': 10, 'head_sha': sha, 'head_branch': 'main', 'conclusion': 'success', 'created_at': '2026-11-17T12:00:00Z', 'workflow_id': 9}}
        calls = []
        def fetch(url, **kwargs):
            calls.append((url, kwargs))
            if url.endswith('/git/ref/heads/main'): return 200, {}, json.dumps({'object': {'sha': sha}}).encode()
            if url.endswith('/actions/workflows/9'): return 200, {}, json.dumps({'name': 'pages-build-deployment', 'path': 'dynamic/pages/pages-build-deployment'}).encode()
            if '/runs?' in url: return 200, {}, json.dumps({'workflow_runs': [{'id': 8, 'head_sha': previous, 'head_branch': 'main', 'conclusion': 'success', 'created_at': '2026-11-17T11:00:00Z'}]}).encode()
            if url == indexnow.ENDPOINT: return 200, {}, b''
            raise AssertionError(url)
        def git(*args): return sha if args[0] == 'rev-parse' else 'index.html\nabout.html\nprivate.html'
        with patch.object(indexnow, 'git', side_effect=git), patch.object(indexnow.subprocess, 'run'), patch.object(indexnow, 'validate_live') as validate:
            self.assertEqual(indexnow.run(event, 'owner/repo', 'token', fetch=fetch), 200)
            self.assertEqual(validate.call_args.args[0], [indexnow.BASE, indexnow.BASE + 'about.html'])
        body = json.loads(calls[-1][1]['body'])
        self.assertEqual(body['urlList'], [indexnow.BASE, indexnow.BASE + 'about.html'])
        with patch.object(indexnow, 'git', return_value=sha), patch.object(indexnow, 'validate_live') as validate:
            stale = lambda *args, **kw: (200, {}, json.dumps({'object': {'sha': previous}}).encode())
            self.assertIsNone(indexnow.run(event, 'owner/repo', 'token', fetch=stale))
            validate.assert_not_called()

    def test_no_changed_pages_and_main_advancing_during_validation_do_not_submit(self):
        sha, previous = 'a' * 40, 'b' * 40
        event = {'workflow_run': {'id': 10, 'head_sha': sha, 'head_branch': 'main', 'conclusion': 'success', 'created_at': '2026-11-17T12:00:00Z', 'workflow_id': 9}}
        requests = []
        ref_checks = []
        def fetch(url, **kwargs):
            requests.append(url)
            if url.endswith('/git/ref/heads/main'):
                ref_checks.append(True)
                return 200, {}, json.dumps({'object': {'sha': sha if len(ref_checks) == 1 else previous}}).encode()
            if url.endswith('/actions/workflows/9'):
                return 200, {}, json.dumps({'name': 'pages-build-deployment', 'path': 'dynamic/pages/pages-build-deployment'}).encode()
            if '/runs?' in url:
                return 200, {}, json.dumps({'workflow_runs': [{'id': 8, 'head_sha': previous, 'head_branch': 'main', 'conclusion': 'success', 'created_at': '2026-11-17T11:00:00Z'}]}).encode()
            raise AssertionError('unexpected request: ' + url)
        def git_no_change(*args): return sha if args[0] == 'rev-parse' else 'js/app.js'
        with patch.object(indexnow, 'git', side_effect=git_no_change), patch.object(indexnow.subprocess, 'run'), patch.object(indexnow, 'validate_live') as validate:
            self.assertIsNone(indexnow.run(event, 'owner/repo', 'token', fetch=fetch))
            validate.assert_not_called()
        ref_checks.clear()
        def git_changed(*args): return sha if args[0] == 'rev-parse' else 'index.html'
        with patch.object(indexnow, 'git', side_effect=git_changed), patch.object(indexnow.subprocess, 'run'), patch.object(indexnow, 'validate_live') as validate:
            self.assertIsNone(indexnow.run(event, 'owner/repo', 'token', fetch=fetch))
            validate.assert_called_once()
        self.assertNotIn(indexnow.ENDPOINT, requests)

    def test_failed_validation_never_posts(self):
        sha, previous = 'a' * 40, 'b' * 40
        event = {'workflow_run': {'id': 10, 'head_sha': sha, 'head_branch': 'main', 'conclusion': 'success', 'created_at': '2026-11-17T12:00:00Z', 'workflow_id': 9}}
        post = []
        def fetch(url, **kwargs):
            if url.endswith('/git/ref/heads/main'): return 200, {}, json.dumps({'object': {'sha': sha}}).encode()
            if url.endswith('/actions/workflows/9'): return 200, {}, json.dumps({'name': 'pages-build-deployment', 'path': 'dynamic/pages/pages-build-deployment'}).encode()
            if '/runs?' in url: return 200, {}, json.dumps({'workflow_runs': [{'id': 8, 'head_sha': previous, 'head_branch': 'main', 'conclusion': 'success', 'created_at': '2026-11-17T11:00:00Z'}]}).encode()
            post.append(url)
            raise AssertionError('unexpected external request')
        def git(*args): return sha if args[0] == 'rev-parse' else 'index.html'
        with patch.object(indexnow, 'git', side_effect=git), patch.object(indexnow.subprocess, 'run'), patch.object(indexnow, 'validate_live', side_effect=ValueError('bad')):
            with self.assertRaises(ValueError): indexnow.run(event, 'owner/repo', 'token', fetch=fetch)
        self.assertEqual(post, [])


if __name__ == '__main__': unittest.main()
