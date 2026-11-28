import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_d1_seed_queue as s
from webmaster_d1_queue_sql import SCHEMA
from webmaster_d1_initialize import META_SQL,INSERT_SQL
from webmaster_actions import BASE
A='a'*32;OLD='a'*40;HEAD='b'*40;ID='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';URL='https://api.cloudflare.com/client/v4/accounts/'+A+'/d1/database/'+ID+'/query';PAGE=BASE+'wiki.html'
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=sqlite3.connect(os.path.join(self.tmp.name,'q.db'));self.db.row_factory=sqlite3.Row
        for sql in (*SCHEMA,META_SQL,INSERT_SQL):self.db.execute(sql)
        self.db.commit();self.batches=0
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def gh(self,advance=False):
        refs=[]
        def fetch(url,token):
            if url.endswith('/git/ref/heads/main'):
                refs.append(1);v={'object':{'sha':OLD if advance and len(refs)>1 else HEAD}}
            elif url.endswith('/pages/builds/latest'):v={'status':'built','commit':HEAD}
            else:v={'id':s.REPOSITORY_ID}
            return 200,{},json.dumps(v).encode()
        return fetch
    def cloud(self,url,token,body):
        self.assertEqual(url,URL)
        def statement(item):
            cur=self.db.execute(item['sql'],item.get('params',[]));rows=[dict(x) for x in cur.fetchall()]
            return {'success':True,'results':rows}
        if 'batch' in body:
            self.batches+=1
            with self.db:results=[statement(item) for item in body['batch']]
            return {'success':True,'result':results}
        return {'success':True,'result':[statement(body)]}
    def run_seed(self,**kwargs):
        args={'git':lambda *a:HEAD,'gh_fetch':self.gh(),'live':lambda u:None,'ancestor':lambda a,b:True,
              'changed':lambda a,b:[PAGE],'cf':self.cloud,'locate_db':lambda a,t,fetch:URL}
        args.update(kwargs)
        return s.seed(A,'secret','a/b','github-secret',OLD,**args)
    def test_seed_and_repeated_event_do_not_duplicate(self):
        self.assertEqual(self.run_seed(),{'status':'seeded','queued':1});self.assertEqual(self.batches,1)
        self.assertEqual(self.db.execute('SELECT revision FROM wm_cursor').fetchone()[0],HEAD)
        self.assertEqual(tuple(self.db.execute('SELECT url,revision,state FROM wm_queue').fetchone()),(PAGE,HEAD,'pending'))
        self.assertEqual(self.run_seed(),{'status':'already_current','queued':None});self.assertEqual(self.batches,1)
    def test_preflight_failure_does_not_touch_d1(self):
        cf=mock.Mock(side_effect=AssertionError('D1 called'))
        for options in ({'gh_fetch':self.gh(advance=True),'cf':cf},{'live':mock.Mock(side_effect=ValueError()),'cf':cf},{'ancestor':lambda a,b:False,'cf':cf},{'changed':lambda a,b:['https://evil/'],'cf':cf}):
            with self.assertRaises(Exception):self.run_seed(**options)
        cf.assert_not_called()
    def test_existing_queue_or_other_cursor_stops(self):
        self.db.execute("INSERT INTO wm_queue(url,revision,state) VALUES(?,?,'pending')",(PAGE,OLD));self.db.commit()
        with self.assertRaises(s.SeedError):self.run_seed()
        self.assertEqual(self.batches,0)
    def test_unknown_batch_never_retried(self):
        def uncertain(url,token,body):
            result=self.cloud(url,token,body)
            if 'batch' in body:raise TimeoutError('secret')
            return result
        with self.assertRaises(s.UnknownOutcome):self.run_seed(cf=uncertain)
        self.assertEqual(self.batches,1);self.assertEqual(self.db.execute('SELECT count(*) FROM wm_queue').fetchone()[0],1)
    def test_bad_schema_never_writes(self):
        self.db.execute('CREATE TABLE unrelated(x)');self.db.commit()
        with self.assertRaises(s.SeedError):self.run_seed()
        self.assertEqual(self.batches,0)
    def test_bad_endpoint_never_queries(self):
        cf=mock.Mock()
        with self.assertRaises(s.SeedError):self.run_seed(cf=cf,locate_db=lambda a,t,fetch:'https://evil.test/query')
        cf.assert_not_called()
    def test_error_redacted(self):
        env={'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main','GITHUB_RUN_ATTEMPT':'1','GITHUB_REPOSITORY_ID':'1102759388','CONFIRMATION':'SEED_VERIFIED_QUEUE','CLOUDFLARE_ACCOUNT_ID':A,'CLOUDFLARE_API_TOKEN':'secret','GITHUB_TOKEN':'github-secret'}
        with mock.patch.dict(os.environ,env,clear=True),mock.patch.object(s,'seed',side_effect=s.UnknownOutcome('secret')),mock.patch('builtins.print') as p:
            self.assertEqual(s.main(),1);self.assertNotIn('secret',str(p.call_args_list));self.assertNotIn(A,str(p.call_args_list))
if __name__=='__main__':unittest.main()
