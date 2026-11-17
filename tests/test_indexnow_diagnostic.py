import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import indexnow_diagnostic as diagnostic


class DiagnosticTests(unittest.TestCase):
    def test_read_only_diagnostic_checks_deployment_and_never_submits(self):
        current, before = 'a' * 40, 'b' * 40
        run = {'id': 99, 'workflow_id': 9, 'name': 'pages build and deployment', 'head_sha': current,
               'head_branch': 'main', 'conclusion': 'success', 'created_at': '2026-11-17T12:00:00Z'}
        previous = {'id': 98, 'head_sha': before, 'head_branch': 'main', 'conclusion': 'success', 'created_at': '2026-11-17T11:00:00Z'}
        visited = []
        def fetch(url, **kwargs):
            self.assertNotIn('body', kwargs, 'Diagnostic must never post')
            visited.append(url)
            if url.endswith('/git/ref/heads/main'): value = {'object': {'sha': current}}
            elif url.endswith('/pages/builds/latest'): value = {'status': 'built', 'commit': current}
            elif '/actions/runs?' in url: value = {'workflow_runs': [run]}
            elif url.endswith('/actions/workflows/9'): value = {'name': 'pages-build-deployment', 'path': 'dynamic/pages/pages-build-deployment'}
            elif '/runs?' in url: value = {'workflow_runs': [run, previous]}
            else: raise AssertionError(url)
            return 200, {}, json.dumps(value).encode()
        def run_git(args, **kwargs):
            return subprocess.CompletedProcess(args, 0, stdout=b'fixture', stderr=b'')
        with patch.object(diagnostic.subprocess, 'run', side_effect=run_git), patch.object(diagnostic.indexnow, 'validate_live') as validate:
            self.assertEqual(diagnostic.diagnose('owner/repo', 'token', fetch=fetch), (99, 98, len(diagnostic.PAGES)))
            self.assertEqual(len(validate.call_args.args[0]), len(diagnostic.PAGES))
        self.assertNotIn(diagnostic.indexnow.ENDPOINT, visited)

    def test_stale_build_is_rejected_before_external_validation(self):
        sha = 'a' * 40
        def fetch(url, **kwargs):
            if url.endswith('/git/ref/heads/main'): value = {'object': {'sha': sha}}
            elif url.endswith('/pages/builds/latest'): value = {'status': 'built', 'commit': 'b' * 40}
            else: raise AssertionError('unexpected request')
            return 200, {}, json.dumps(value).encode()
        with patch.object(diagnostic.indexnow, 'validate_live') as validate:
            with self.assertRaisesRegex(ValueError, 'not built from current main'):
                diagnostic.diagnose('owner/repo', 'token', fetch=fetch)
            validate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
