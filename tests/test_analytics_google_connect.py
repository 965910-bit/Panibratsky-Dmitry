import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import analytics_google_connect as a

class Tests(unittest.TestCase):
    def test_decline_makes_no_auth_or_secret_calls(self):
        with mock.patch('builtins.input',return_value='нет'),mock.patch.object(a.google,'gh_check') as check,mock.patch.object(a.google,'gh_store') as store:
            self.assertEqual(a.main(['file']),0);check.assert_not_called();store.assert_not_called()
    def test_distinct_secrets_and_required_scope(self):
        self.assertEqual(a.SCOPE,'https://www.googleapis.com/auth/analytics.edit')
        self.assertTrue(set(a.SECRET_NAMES).isdisjoint({'SCM_WM_GOOGLE_CLIENT_ID','SCM_WM_GOOGLE_CLIENT_SECRET','SCM_WM_GOOGLE_REFRESH_TOKEN'}))
    def test_setup_uses_analytics_scope_and_separate_secrets(self):
        g=a.google
        with mock.patch.object(g,'SCOPE'),mock.patch.object(g,'SECRET_NAMES'),mock.patch('builtins.input',return_value='да'),mock.patch.object(g,'load_desktop_client',return_value=('id','secret')),mock.patch.object(g,'gh_check',return_value='a/b'),mock.patch.object(g,'pkce',return_value=('verifier','challenge')),mock.patch.object(g,'receive_code',return_value=('code','redirect')),mock.patch.object(g,'exchange',return_value='refresh'),mock.patch.object(g,'gh_store') as store:
            self.assertEqual(a.main(['file']),0)
            self.assertEqual(g.SCOPE,a.SCOPE);self.assertEqual(g.SECRET_NAMES,a.SECRET_NAMES)
            store.assert_called_once_with('a/b','id','secret','refresh')
    def test_no_secret_in_error_message(self):
        with mock.patch('builtins.input',return_value='да'),mock.patch.object(a.google,'load_desktop_client',side_effect=a.google.SetupError('secret-value')),mock.patch('builtins.print') as out:
            self.assertEqual(a.main(['file']),1);self.assertNotIn('secret-value',str(out.call_args_list))
if __name__=='__main__':unittest.main()
