import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_reports_connect as a
class Tests(unittest.TestCase):
    def test_scope_and_secret_isolation(self):
        self.assertEqual(a.SCOPE,'https://www.googleapis.com/auth/analytics.readonly')
        self.assertTrue(all(n.startswith('SCM_GA4_REPORT_') for n in a.SECRET_NAMES))
    def test_decline_does_nothing(self):
        with mock.patch('builtins.input',return_value='нет'),mock.patch.object(a.google,'gh_store') as store:
            self.assertEqual(a.main(['file']),0);store.assert_not_called()
    def test_success_and_globals_restored(self):
        g=a.google; old=(g.SCOPE,g.SECRET_NAMES)
        with mock.patch('builtins.input',return_value='да'),mock.patch.object(g,'load_desktop_client',return_value=('id','secret')),mock.patch.object(g,'gh_check',return_value='a/b'),mock.patch.object(g,'pkce',return_value=('v','c')),mock.patch.object(g,'receive_code',return_value=('code','redirect')),mock.patch.object(g,'exchange',return_value='refresh'),mock.patch.object(g,'gh_store') as store:
            self.assertEqual(a.main(['file']),0);store.assert_called_once_with('a/b','id','secret','refresh')
        self.assertEqual((g.SCOPE,g.SECRET_NAMES),old)
    def test_no_secrets_in_errors(self):
        with mock.patch('builtins.input',return_value='да'),mock.patch.object(a.google,'load_desktop_client',side_effect=a.google.SetupError('private')),mock.patch('builtins.print') as out:
            self.assertEqual(a.main(['file']),1);self.assertNotIn('private',str(out.call_args_list))
if __name__=='__main__':unittest.main()
