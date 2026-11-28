import os
import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_yandex_pipeline_alert as a

class Tests(unittest.TestCase):
    def test_only_all_success_closes(self):
        self.assertEqual(a.classify(['success']*4),'success')
        for bad in ('failure','skipped','cancelled',''):
            for idx in range(4):
                stages=['success']*4;stages[idx]=bad
                self.assertEqual(a.classify(stages),'failure')
    def test_invalid_is_not_success(self):
        for stages in ([],['success']*3,['success']*4+['failure'],['success']*3+['unexpected']):
            with self.assertRaises(ValueError):a.classify(stages)
    def test_main_alert_failure(self):
        env={'GITHUB_TOKEN':'secret','GITHUB_REPOSITORY':'a/b','GITHUB_RUN_ID':'1','ACCESS_OUTCOME':'success','SITEMAP_OUTCOME':'failure','DIAGNOSTICS_OUTCOME':'skipped','ISSUES_OUTCOME':'skipped'}
        with mock.patch.dict(os.environ,env,clear=True),mock.patch.object(a,'sync',return_value='created') as sync:
            self.assertEqual(a.main(),0)
            self.assertEqual(sync.call_args.args[3],'failure')
    def test_failure_redacts_secrets(self):
        with mock.patch.dict(os.environ,{'GITHUB_TOKEN':'secret'},clear=True),mock.patch.object(a,'sync',side_effect=ValueError('secret')),mock.patch('builtins.print') as out:
            self.assertEqual(a.main(),1);self.assertNotIn('secret',str(out.call_args_list))
if __name__=='__main__':unittest.main()
