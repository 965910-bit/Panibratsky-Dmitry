import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_yandex_issue_health as h

class Tests(unittest.TestCase):
    def check(self,sm,site):
        alert=mock.Mock(return_value='synced')
        value=h.sync_health('private','a/b','123','private',sitemap=lambda t:sm,problems=lambda t:site,alert=alert)
        return value,alert
    def test_confirmed_problems(self):
        result,alert=self.check({'state':'found','errors':1,'access_date':'2026-10-08'}, {'ERRORS_IN_SITEMAPS':'PRESENT','DOCUMENTS_MISSING_DESCRIPTION':'PRESENT'})
        self.assertEqual(result,('synced','synced'))
        self.assertEqual([c.args[3] for c in alert.call_args_list],['failure','failure'])
    def test_confirmed_recovery(self):
        result,alert=self.check({'state':'found','errors':0,'access_date':'2026-11-01'}, {'ERRORS_IN_SITEMAPS':'ABSENT','DOCUMENTS_MISSING_DESCRIPTION':'ABSENT'})
        self.assertEqual(result,('synced','synced'));self.assertEqual([c.args[3] for c in alert.call_args_list],['success','success'])
    def test_unknown_never_closes_or_creates(self):
        for sm,site in [({'state':'not_found_in_first_page'}, {'ERRORS_IN_SITEMAPS':'ABSENT','DOCUMENTS_MISSING_DESCRIPTION':'UNKNOWN_STATE'}),({'state':'found','errors':0,'access_access':'unknown'}, {'ERRORS_IN_SITEMAPS':'ABSENT','DOCUMENTS_MISSING_DESCRIPTION':'NOT_REPORTED'})]:
            result,alert=self.check(sm,site);self.assertEqual(result,('unknown','unknown'));alert.assert_not_called()
    def test_failed_read_no_issue_mutation(self):
        alert=mock.Mock()
        with self.assertRaises(RuntimeError):h.sync_health('x','a/b','123','x',sitemap=lambda t:{'state':'found','errors':1},problems=mock.Mock(side_effect=RuntimeError()),alert=alert)
        alert.assert_not_called()
    def test_no_secret_leak(self):
        with mock.patch.dict('os.environ',{'SCM_WM_YANDEX_ACCESS_TOKEN':'secret','GITHUB_TOKEN':'secret'},clear=True),mock.patch.object(h,'sync_health',side_effect=RuntimeError('secret')),mock.patch('builtins.print') as p:
            self.assertEqual(h.main(),1);self.assertNotIn('secret',str(p.call_args_list))
if __name__=='__main__':unittest.main()
