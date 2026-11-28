import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import analytics_private_snapshot_alert as alert

class Tests(unittest.TestCase):
    def env(self, status='success'):
        return {'GITHUB_EVENT_NAME': 'schedule', 'GITHUB_REF': 'refs/heads/main',
                'GITHUB_REPOSITORY_ID': '1102759388', 'GITHUB_REPOSITORY': 'a/b',
                'GITHUB_RUN_ID': '123', 'GITHUB_TOKEN': 'token', 'SNAPSHOT_JOB_STATUS': status}

    def test_success_and_failure_are_forwarded_without_report_data(self):
        for status in ('success', 'failure'):
            with self.subTest(status=status), patch.dict(os.environ, self.env(status), clear=True), patch.object(alert, 'sync', return_value='clear') as sync:
                self.assertEqual(alert.main(), 0)
                self.assertEqual(sync.call_args.args, ('a/b', '123', 'token', status))
                self.assertNotIn('token', alert.BODY)

    def test_uncertain_cancelled_and_untrusted_cannot_change_issue(self):
        for status in ('cancelled', '', 'pending'):
            with self.subTest(status=status), patch.dict(os.environ, self.env(status), clear=True), patch.object(alert, 'sync') as sync:
                self.assertEqual(alert.main(), 1); sync.assert_not_called()
        env = self.env(); env['GITHUB_REF'] = 'refs/heads/other'
        with patch.dict(os.environ, env, clear=True), patch.object(alert, 'sync') as sync:
            self.assertEqual(alert.main(), 1); sync.assert_not_called()

    def test_alert_error_does_not_claim_success(self):
        with patch.dict(os.environ, self.env(), clear=True), patch.object(alert, 'sync', side_effect=RuntimeError('private')):
            self.assertEqual(alert.main(), 1)
