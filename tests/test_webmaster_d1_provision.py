import os
import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_d1_provision as p
A='a'*32

def listing(entries=(),total=2):return {'success':True,'result':list(entries),'result_info':{'page':1,'per_page':100,'count':len(entries),'total_count':total}}
class Tests(unittest.TestCase):
    def test_existing_never_creates(self):
        post=mock.Mock();self.assertEqual(p.provision(A,'secret',read=lambda *a:listing([{'name':p.NAME}]),post=post),'already_exists');post.assert_not_called()
    def test_valid_empty_creates_only_once(self):
        post=mock.Mock(return_value='created');self.assertEqual(p.provision(A,'secret',read=lambda *a:listing(),post=post),'created');post.assert_called_once_with(A,'secret')
    def test_bad_inventory_never_creates(self):
        for data in (listing(total=9),listing(total=True),{'success':True,'result':[],'result_info':{}},listing([{'name':'x'}],total=0)):
            post=mock.Mock()
            with self.assertRaises(p.ProvisionError):p.provision(A,'secret',read=lambda *a:data,post=post)
            post.assert_not_called()
    def test_unknown_post_is_not_repeated(self):
        post=mock.Mock(side_effect=p.UnknownOutcome('secret'))
        with self.assertRaises(p.UnknownOutcome):p.provision(A,'secret',read=lambda *a:listing(),post=post)
        post.assert_called_once()
    def test_block_reruns_and_wrong_confirmation(self):
        for attempt,confirm in [('2','CREATE_SEPARATE_QUEUE'),('1','wrong')]:
            env={'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main','GITHUB_RUN_ATTEMPT':attempt,'GITHUB_REPOSITORY_ID':'1102759388','CONFIRMATION':confirm}
            with mock.patch.dict(os.environ,env,clear=True),mock.patch.object(p,'provision') as call,mock.patch('builtins.print'):
                self.assertEqual(p.main(),1);call.assert_not_called()
    def test_exceptions_are_sanitized_and_unknown(self):
        env={'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main','GITHUB_RUN_ATTEMPT':'1','GITHUB_REPOSITORY_ID':'1102759388','CONFIRMATION':'CREATE_SEPARATE_QUEUE','CLOUDFLARE_ACCOUNT_ID':A,'CLOUDFLARE_API_TOKEN':'secret'}
        with mock.patch.dict(os.environ,env,clear=True),mock.patch.object(p,'provision',side_effect=RuntimeError('secret')),mock.patch('builtins.print') as out:
            self.assertEqual(p.main(),1);self.assertIn('unknown_outcome_do_not_retry',str(out.call_args_list));self.assertNotIn('secret',str(out.call_args_list));self.assertNotIn(A,str(out.call_args_list))
if __name__=='__main__':unittest.main()
