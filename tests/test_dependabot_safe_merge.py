import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import dependabot_safe_merge as module
from dependabot_safe_merge import allowed_change


class DependabotSafeMergeTests(unittest.TestCase):
    def setUp(self):
        self.old_package = {'devDependencies': {'playwright-core': '1.65.1', 'axe-core': '4.14.1'}, 'scripts': {'test': 'safe'}}
        self.new_package = copy.deepcopy(self.old_package)
        self.new_package['devDependencies']['playwright-core'] = '1.65.2'
        self.old_lock = {'lockfileVersion': 3, 'packages': {'': {'devDependencies': {'playwright-core': '1.65.1'}},
                         'node_modules/playwright-core': {'version': '1.65.1', 'dev': True}}}
        self.new_lock = copy.deepcopy(self.old_lock)
        self.new_lock['packages']['']['devDependencies']['playwright-core'] = '1.65.2'
        self.new_lock['packages']['node_modules/playwright-core'] = {'version': '1.65.2', 'dev': True,
            'resolved': 'https://registry.npmjs.org/playwright-core/-/playwright-core-1.65.2.tgz', 'integrity': 'sha512-fixture'}

    def check(self):
        return allowed_change(self.old_package, self.new_package, self.old_lock, self.new_lock)

    def test_matching_patch_only_is_allowed(self):
        self.assertTrue(self.check())

    def test_minor_major_prerelease_and_downgrade_denied(self):
        for version in ('1.66.0', '2.0.0', '1.65.0', '1.65.2-beta.1', '^1.65.2'):
            with self.subTest(version=version):
                self.setUp()
                self.new_package['devDependencies']['playwright-core'] = version
                self.assertFalse(self.check())

    def test_unrelated_changes_and_untrusted_registry_denied(self):
        self.new_package['scripts']['test'] = 'unexpected'
        self.assertFalse(self.check())
        self.setUp()
        self.new_lock['packages']['']['devDependencies']['other'] = '1.0.0'
        self.assertFalse(self.check())
        self.setUp()
        self.new_lock['packages']['node_modules/playwright-core']['resolved'] = 'https://example.invalid/package.tgz'
        self.assertFalse(self.check())
        self.setUp()
        self.new_lock['packages']['node_modules/playwright-core']['hasInstallScript'] = True
        self.assertFalse(self.check())

    def test_eligibility_requires_real_bot_current_base_and_clean_checks(self):
        from unittest.mock import patch
        base, head = 'a' * 40, 'b' * 40
        pr = {'number': 12, 'state': 'open', 'draft': False, 'user': {'login': 'dependabot[bot]'},
              'base': {'ref': 'main', 'sha': base}, 'head': {'sha': head, 'repo': {'full_name': 'owner/repo'}},
              'mergeable': True, 'mergeable_state': 'clean'}
        def fake_api(endpoint, *args):
            if endpoint.endswith('/branches/main'):
                return {'commit': {'sha': base}}
            if '/files?' in endpoint:
                return [[{'filename': 'package.json', 'status': 'modified'},
                         {'filename': 'package-lock.json', 'status': 'modified'}]]
            raise AssertionError(endpoint)
        def fake_read(repo, path, sha):
            return {('package.json', base): self.old_package, ('package.json', head): self.new_package,
                    ('package-lock.json', base): self.old_lock, ('package-lock.json', head): self.new_lock}[(path, sha)]
        with patch.object(module, 'api', side_effect=fake_api), patch.object(module, 'read_json_at', side_effect=fake_read):
            self.assertTrue(module.eligible('owner/repo', pr))
            for field, value in [('mergeable_state', 'blocked'), ('mergeable', False), ('draft', True)]:
                candidate = copy.deepcopy(pr)
                candidate[field] = value
                self.assertFalse(module.eligible('owner/repo', candidate))
            candidate = copy.deepcopy(pr)
            candidate['user']['login'] = 'someone-else'
            self.assertFalse(module.eligible('owner/repo', candidate))
            candidate = copy.deepcopy(pr)
            candidate['head']['repo']['full_name'] = 'fork/repo'
            self.assertFalse(module.eligible('owner/repo', candidate))
        with patch.object(module, 'api', return_value={'commit': {'sha': 'c' * 40}}):
            self.assertFalse(module.eligible('owner/repo', pr))

    def test_workflow_never_executes_pr_code_and_uses_scoped_app(self):
        text = (Path(__file__).resolve().parents[1] / '.github/workflows/dependabot-safe-merge.yml').read_text()
        self.assertIn('ref: main', text)
        self.assertIn('persist-credentials: false', text)
        self.assertIn('permission-contents: write', text)
        self.assertIn('permission-pull-requests: write', text)
        self.assertNotIn('pull_request_target:', text)
        self.assertNotIn('--auto', text)


if __name__ == '__main__':
    unittest.main()
