import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from publication_pr import validate_policy


class PublicationPRPolicyTests(unittest.TestCase):
    def setUp(self):
        self.repo = {'allow_auto_merge': True, 'default_branch': 'main'}
        self.rules = [
            {'ruleset_id': 17, 'type': 'pull_request', 'parameters': {'required_approving_review_count': 0}},
            {'ruleset_id': 17, 'type': 'required_status_checks', 'parameters': {
                'strict_required_status_checks_policy': True,
                'required_status_checks': [{'context': 'validate', 'integration_id': 15368}]}},
        ]
        self.details = {17: {'enforcement': 'active', 'current_user_can_bypass': 'never', 'bypass_count': 0}}

    def test_complete_policy_passes(self):
        validate_policy(self.repo, self.rules, self.details)

    def test_rejects_each_missing_safety_condition(self):
        for change in ('disabled', 'bypass', 'loose', 'wrong_app', 'no_pr', 'disabled_auto', 'wrong_branch', 'requires_review', 'unknown_bypass', 'app_bypass'):
            with self.subTest(change=change):
                self.setUp()
                if change == 'disabled': self.details[17]['enforcement'] = 'disabled'
                if change == 'bypass': self.details[17]['bypass_count'] = 1
                if change == 'unknown_bypass': self.details[17]['bypass_count'] = None
                if change == 'app_bypass': self.details[17]['current_user_can_bypass'] = 'always'
                if change == 'loose': self.rules[1]['parameters']['strict_required_status_checks_policy'] = False
                if change == 'wrong_app': self.rules[1]['parameters']['required_status_checks'][0]['integration_id'] = 42
                if change == 'no_pr': self.rules.pop(0)
                if change == 'disabled_auto': self.repo['allow_auto_merge'] = False
                if change == 'wrong_branch': self.repo['default_branch'] = 'other'
                if change == 'requires_review': self.rules[0]['parameters']['required_approving_review_count'] = 1
                with self.assertRaises(ValueError):
                    validate_policy(self.repo, self.rules, self.details)


class PublicationPRIntegrationTests(unittest.TestCase):
    def test_success_path_with_fake_github(self):
        import contextlib
        import io
        import os
        import subprocess
        import tempfile
        from unittest.mock import patch
        import publication_pr as publisher

        with tempfile.TemporaryDirectory() as tmp:
            def git(*args):
                return subprocess.run(['git', '-C', tmp, *args], check=True, capture_output=True, text=True).stdout.strip()
            git('init', '-q')
            git('config', 'user.name', 'Fixture')
            git('config', 'user.email', 'fixture@example.invalid')
            for name in publisher.PATHS['news']:
                path = Path(tmp, name)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('old')
            git('add', '.')
            git('commit', '-qm', 'base')
            base = git('rev-parse', 'HEAD')
            Path(tmp, 'data/news.json').write_text('new')
            calls = []
            def fake_api(endpoint, *args):
                calls.append(('api', endpoint))
                if endpoint == 'repos/owner/repo':
                    return {'allow_auto_merge': True, 'default_branch': 'main'}
                if endpoint.endswith('/rules/branches/main'):
                    return [{'ruleset_id': 17, 'type': 'pull_request', 'parameters': {'required_approving_review_count': 0}},
                            {'ruleset_id': 17, 'type': 'required_status_checks', 'parameters': {
                                'strict_required_status_checks_policy': True,
                                'required_status_checks': [{'context': 'validate', 'integration_id': 15368}]}}]
                if endpoint.endswith('/rulesets/17'):
                    return {'enforcement': 'active', 'current_user_can_bypass': 'never', 'node_id': 'ruleset-node'}
                if endpoint == 'repos/owner/repo/branches/main':
                    return {'commit': {'sha': base}, 'protected': True}
                if '?state=open' in endpoint:
                    return [[]]
                if endpoint == 'repos/owner/repo/pulls':
                    return {'user': {'login': publisher.APP_LOGIN}, 'head': {'sha': git('rev-parse', 'HEAD')},
                            'base': {'ref': 'main'}, 'node_id': 'fixture-node', 'html_url': 'https://example.invalid/pr'}
                if endpoint == 'graphql' and any('bypassActors' in arg for arg in args):
                    return {'data': {'node': {'bypassActors': {'totalCount': 0}}}}
                if endpoint == 'graphql':
                    return {'data': {'enablePullRequestAutoMerge': {'pullRequest': {'autoMergeRequest': {'enabledAt': 'now'}}}}}
                raise AssertionError(endpoint)
            real_command = publisher.command
            def fake_command(*args, **kwargs):
                if args[:2] == ('git', 'push') or args[:2] == ('gh', 'auth'):
                    calls.append(('command', args))
                    return ''
                return real_command(*args, **kwargs)
            env = {'GITHUB_REPOSITORY': 'owner/repo', 'GITHUB_SHA': base, 'GITHUB_RUN_ID': '123',
                   'GITHUB_RUN_ATTEMPT': '1', 'GITHUB_REF': 'refs/heads/main', 'GH_TOKEN': 'fixture'}
            old = os.getcwd()
            try:
                os.chdir(tmp)
                with patch.dict(os.environ, env), patch.object(sys, 'argv', ['publication_pr', '--kind', 'news']), \
                     patch.object(publisher, 'api', side_effect=fake_api), patch.object(publisher, 'command', side_effect=fake_command), \
                     contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(0, publisher.main())
                self.assertTrue(any(call[0] == 'command' and call[1][:2] == ('git', 'push') for call in calls))
                self.assertIn(('api', 'graphql'), calls)
                self.assertEqual('data/news.json', git('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD'))
                # A disabled policy must fail before creating a commit or sending a push.
                git('reset', '--hard', base)
                Path(tmp, 'data/news.json').write_text('new')
                calls.clear()
                def disabled_api(endpoint, *args):
                    if endpoint.endswith('/rules/branches/main'):
                        return []
                    return fake_api(endpoint, *args)
                with patch.dict(os.environ, env), patch.object(sys, 'argv', ['publication_pr', '--kind', 'news']), \
                     patch.object(publisher, 'api', side_effect=disabled_api), patch.object(publisher, 'command', side_effect=fake_command), \
                     contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(1, publisher.main())
                self.assertEqual(base, git('rev-parse', 'HEAD'))
                self.assertFalse(any(call[0] == 'command' and call[1][:2] == ('git', 'push') for call in calls))
                self.assertNotIn(('api', 'graphql'), calls)
                # A main branch advancing after generation must not be pushed.
                calls.clear()
                branch_lookups = []
                def stale_api(endpoint, *args):
                    if endpoint == 'repos/owner/repo/branches/main':
                        branch_lookups.append(1)
                        return {'commit': {'sha': base if len(branch_lookups) == 1 else 'f' * 40}, 'protected': True}
                    return fake_api(endpoint, *args)
                with patch.dict(os.environ, env), patch.object(sys, 'argv', ['publication_pr', '--kind', 'news']), \
                     patch.object(publisher, 'api', side_effect=stale_api), patch.object(publisher, 'command', side_effect=fake_command), \
                     contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(1, publisher.main())
                self.assertFalse(any(call[0] == 'command' and call[1][:2] == ('git', 'push') for call in calls))
                self.assertFalse(any(call[0] == 'command' and call[1][:2] == ('git', 'push') for call in calls))
            finally:
                os.chdir(old)


if __name__ == '__main__':
    unittest.main()
