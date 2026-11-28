import json
import os
import sqlite3
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_d1_batch_probe as p
import webmaster_d1_initialize as i
A='a'*32; ID='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
URL='https://api.cloudflare.com/client/v4/accounts/'+A+'/d1/database/'+ID+'/query'

class Tests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:'); self.db.row_factory=sqlite3.Row
        for sql in (*i.SCHEMA,i.META_SQL,i.INSERT_SQL): self.db.execute(sql)
        self.db.commit(); self.calls=0
    def tearDown(self): self.db.close()
    def fetch(self,url,token,body):
        cur=self.db.execute(body['sql']); rows=[dict(x) for x in cur.fetchall()]
        return {'success':True,'result':[{'success':True,'results':rows}]}
    def failing(self,url,token,body):
        self.calls+=1
        try:
            self.db.execute('BEGIN')
            with self.db:
                for entry in body['batch']: self.db.execute(entry['sql'])
        except sqlite3.IntegrityError: return
        raise AssertionError('probe did not fail')
    def run_probe(self,**opts):
        args={'fetch':self.fetch,'locate_db':lambda a,t,fetch:URL,'fail':self.failing};args.update(opts)
        return p.probe(A,'secret',**args)
    def test_probe_rolls_back(self):
        self.assertEqual(self.run_probe(),'rollback_observed'); self.assertEqual(self.calls,1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM sqlite_master WHERE name=?",(p.PROBE,)).fetchone()[0],0)
    def test_nonempty_queue_stops_before_probe(self):
        self.db.execute("INSERT INTO wm_cursor VALUES (1,'revision')");self.db.commit()
        with self.assertRaises(p.ProbeError):self.run_probe()
        self.assertEqual(self.calls,0)
    def test_unexpected_schema_stops_before_probe(self):
        self.db.execute('CREATE TABLE unrelated(x)')
        with self.assertRaises(p.ProbeError):self.run_probe()
        self.assertEqual(self.calls,0)
    def test_partial_or_timeout_is_unknown_no_retry(self):
        def partial(url,token,body):
            self.calls+=1; self.db.execute(body['batch'][0]['sql']); self.db.commit()
        with self.assertRaises(p.UnknownOutcome):self.run_probe(fail=partial)
        self.assertEqual(self.calls,1)
        with self.assertRaises(p.ProbeError):self.run_probe()
        self.assertEqual(self.calls,1)
    def test_bad_endpoint_no_query(self):
        fetch=mock.Mock()
        with self.assertRaises(p.ProbeError):self.run_probe(fetch=fetch,locate_db=lambda a,t,fetch:'https://evil.test/')
        fetch.assert_not_called()
    def test_constraint_response_and_ambiguous_error(self):
        class Response:
            def __init__(self, value):self.value=value
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return json.dumps(self.value).encode()
        opener=mock.Mock()
        opener.open.return_value=Response({'success':False,'errors':[{'message':'D1: UNIQUE constraint failed: wm_rest_rollback_probe.id'}]})
        with mock.patch.object(p.urllib.request,'build_opener',return_value=opener):p.failing_request(URL,'secret',p.BATCH)
        opener.open.return_value=Response({'success':False,'errors':[{'message':'not authorized'}]})
        with mock.patch.object(p.urllib.request,'build_opener',return_value=opener):
            with self.assertRaises(p.UnknownOutcome):p.failing_request(URL,'secret',p.BATCH)
    def test_redaction(self):
        env={'GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main','GITHUB_RUN_ATTEMPT':'1','GITHUB_REPOSITORY_ID':'1102759388','CONFIRMATION':'PROBE_DEDICATED_QUEUE_ROLLBACK','CLOUDFLARE_ACCOUNT_ID':A,'CLOUDFLARE_API_TOKEN':'secret'}
        with mock.patch.dict(os.environ,env,clear=True),mock.patch.object(p,'probe',side_effect=p.UnknownOutcome('secret')),mock.patch('builtins.print') as out:
            self.assertEqual(p.main(),1); self.assertNotIn('secret',str(out.call_args_list)); self.assertIn('unknown_outcome',str(out.call_args_list))
if __name__=='__main__':unittest.main()
