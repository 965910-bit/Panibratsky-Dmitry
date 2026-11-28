import os
import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_d1_initialize as i
A='a'*32;ID='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';URL='https://api.cloudflare.com/client/v4/accounts/'+A+'/d1/database/'+ID+'/query'
def response(rows):return {'success':True,'result':[{'success':True,'results':rows}]}
class Tests(unittest.TestCase):
    def fake(self,objects=()):
        state=set(objects);calls=[]
        def fetch(url,token,body=None):
            calls.append(body)
            if 'batch' in body:
                state.update((name,'table') for name in i.EXPECTED)
                return {'success':True,'result':[{'success':True,'results':[]} for x in body['batch']]}
            if body['sql']==i.OBJECT_SQL:return response([{'name':n,'type':t} for n,t in state])
            if body['sql']==i.META_READ:return response([{'marker':i.MARKER}])
            for table,cols in i.COLUMNS.items():
                if body['sql']=='PRAGMA table_info('+table+')':return response([{'name':n,'type':t} for n,t in cols])
            raise AssertionError('unexpected SQL')
        return fetch,calls
    def test_empty_initialized_and_verified(self):
        fetch,calls=self.fake();result=i.initialize(A,'secret',fetch=fetch,locate_db=lambda a,t,fetch:URL)
        self.assertEqual(result,'initialized');self.assertEqual(sum('batch' in x for x in calls),1)
        self.assertEqual([x['sql'] for x in next(x['batch'] for x in calls if 'batch' in x)],list(i.SCHEMA)+[i.META_SQL,i.INSERT_SQL])
    def test_existing_unrelated_schema_never_changes(self):
        fetch,calls=self.fake([('customer','table')])
        with self.assertRaises(i.InitError):i.initialize(A,'secret',fetch=fetch,locate_db=lambda a,t,fetch:URL)
        self.assertFalse(any('batch' in x for x in calls))
    def test_existing_owned_schema_does_not_modify(self):
        fetch,calls=self.fake([(name,'table') for name in i.EXPECTED])
        self.assertEqual(i.initialize(A,'secret',fetch=fetch,locate_db=lambda a,t,fetch:URL),'already_initialized')
        self.assertFalse(any('batch' in x for x in calls))
    def test_existing_wrong_columns_never_modified(self):
        fetch,calls=self.fake([(name,'table') for name in i.EXPECTED])
        def wrong(url,token,body=None):
            if body['sql']=='PRAGMA table_info(wm_queue)':return response([{'name':'unexpected','type':'TEXT'}])
            return fetch(url,token,body)
        with self.assertRaises(i.InitError):i.initialize(A,'secret',fetch=wrong,locate_db=lambda a,t,fetch:URL)
        self.assertFalse(any('batch' in x for x in calls))
    def test_failed_batch_unknown_and_not_retried(self):
        fetch,calls=self.fake()
        def failing(url,token,body=None):
            if 'batch' in body:calls.append(body);raise TimeoutError('secret')
            return fetch(url,token,body)
        with self.assertRaises(i.UnknownOutcome):i.initialize(A,'secret',fetch=failing,locate_db=lambda a,t,fetch:URL)
        self.assertEqual(sum('batch' in x for x in calls),1)
    def test_untrusted_endpoint_prevents_queries(self):
        fetch=mock.Mock()
        with self.assertRaises(i.InitError):i.initialize(A,'secret',fetch=fetch,locate_db=lambda a,t,fetch:'https://evil.test/query')
        fetch.assert_not_called()
    def test_locate_requires_exact_one_uuid(self):
        def fetch(url,token):return {'result':[{'name':i.NAME,'uuid':ID}],'result_info':{'page':1,'per_page':100,'count':1}}
        self.assertEqual(i.locate(A,'secret',fetch=fetch),URL)
        def dup(url,token):return {'result':[{'name':i.NAME,'uuid':ID}]*2,'result_info':{'page':1,'per_page':100,'count':2}}
        with self.assertRaises(i.InitError):i.locate(A,'secret',fetch=dup)
    def test_redacted_unknown(self):
        env={'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main','GITHUB_RUN_ATTEMPT':'1','GITHUB_REPOSITORY_ID':'1102759388','CONFIRMATION':'INIT_SEPARATE_QUEUE','CLOUDFLARE_ACCOUNT_ID':A,'CLOUDFLARE_API_TOKEN':'secret'}
        with mock.patch.dict(os.environ,env,clear=True),mock.patch.object(i,'initialize',side_effect=i.UnknownOutcome('secret')),mock.patch('builtins.print') as p:
            self.assertEqual(i.main(),1);self.assertNotIn('secret',str(p.call_args_list));self.assertIn('unknown_outcome',str(p.call_args_list))
if __name__=='__main__':unittest.main()
