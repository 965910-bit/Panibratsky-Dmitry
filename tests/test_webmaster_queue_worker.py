import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from webmaster_queue import Queue
from webmaster_queue_worker import drain, WorkerError, recrawl_only
from webmaster_actions import BASE, PAGES

URLS = [BASE + p for p in list(PAGES)[:3]]
REV = 'a'*40
TASK = 'c7fe80c0-36e3-11e6-8b2d-df96aa592c0a'

class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.q=Queue(os.path.join(self.temp.name,'q.sqlite'));self.q.enqueue(URLS,REV)
    def tearDown(self):self.q.close();self.temp.cleanup()
    def test_default_adapter_skips_sitemap_management(self):
        with mock.patch('webmaster_queue_worker.yandex_action',return_value={'recrawl':[]}) as action:
            recrawl_only('private',[URLS[0]],True)
            action.assert_called_once_with('private',[URLS[0]],True,manage_sitemap=False)
    def test_individual_claims_and_batch_cap(self):
        called=[]
        def action(token,urls,apply):
            called.append((token,urls,apply));return {'recrawl':[{'url':urls[0],'status':'accepted','task_id':f'00000000-0000-0000-0000-{len(called):012d}'}]}
        result=drain(self.q,'SECRET',limit=2,validate=lambda u:None,action=action)
        self.assertEqual(result['status'],'ok');self.assertEqual(len(called),2)
        self.assertTrue(all(len(item[1]) == 1 and item[2] for item in called))
        self.assertEqual(sum(row[3]=='pending' for row in self.q.items()),1)
        self.assertNotIn('SECRET',str(result))
    def test_quota_stops_without_losing_remaining(self):
        calls=[]
        def action(t,u,a):calls.append(u);return {'recrawl':[{'url':u[0],'status':'quota_exhausted'}]}
        result=drain(self.q,'t',validate=lambda u:None,action=action)
        self.assertEqual(result['status'],'quota_exhausted');self.assertEqual(len(calls),1)
        self.assertTrue(all(row[3]=='pending' for row in self.q.items()))
    def test_preflight_failure_does_not_write(self):
        def validate(urls):raise ValueError('bad page')
        def action(*args):self.fail('write attempted')
        result=drain(self.q,'t',validate=validate,action=action)
        self.assertEqual(result['status'],'preflight_failed');self.assertTrue(all(row[3]=='pending' for row in self.q.items()))
    def test_unknown_does_not_retry(self):
        def action(*args):raise TimeoutError('sensitive server response')
        result=drain(self.q,'t',validate=lambda u:None,action=action)
        self.assertEqual(result['status'],'uncertain');self.assertNotIn('sensitive',str(result))
        self.assertEqual(sum(row[3]=='uncertain' for row in self.q.items()),1)
    def test_uncertainty_blocks_subsequent_runs(self):
        def fail(*args):raise TimeoutError()
        drain(self.q,'t',validate=lambda u:None,action=fail)
        def should_not_send(*args):self.fail('unexpected retry or later write')
        result=drain(self.q,'t',validate=lambda u:None,action=should_not_send)
        self.assertEqual(result['status'],'blocked');self.assertEqual(result['results'],[])
        self.assertEqual(sum(row[3]=='pending' for row in self.q.items()),2)
    def test_invalid_response_unknown(self):
        result=drain(self.q,'t',validate=lambda u:None,action=lambda *a:{'recrawl':[{'url':'wrong','status':'accepted','task_id':'t'}]})
        self.assertEqual(result['status'],'uncertain')
    def test_duplicate_response_is_uncertain_and_blocks(self):
        calls=[]
        def action(t,u,a):
            calls.append(u[0]);return {'recrawl':[{'url':u[0],'status':'already_added'}]}
        result=drain(self.q,'t',validate=lambda u:None,action=action)
        self.assertEqual(result['status'],'uncertain')
        self.assertEqual(result['results'][0]['status'],'already_added_unresolved')
        self.assertEqual(len(calls),1)
        self.assertEqual(sum(row[3]=='uncertain' for row in self.q.items()),1)
        self.assertEqual(drain(self.q,'t',validate=lambda u:None,action=action)['status'],'blocked')
        self.assertEqual(len(calls),1)
    def test_invalid_task_id_is_uncertain_before_persistence(self):
        result=drain(self.q,'t',validate=lambda u:None,action=lambda t,u,a:{'recrawl':[{'url':u[0],'status':'accepted','task_id':'not-a-uuid'}]})
        self.assertEqual(result['status'],'uncertain')
        self.assertEqual(sum(row[3]=='uncertain' for row in self.q.items()),1)
        self.assertEqual(self.q.receipts(),[])
    def test_bad_token_or_limit_before_claim(self):
        for token,limit in [('',5),('x\ny',5),('x',6),('x',True)]:
            with self.assertRaises(WorkerError):drain(self.q,token,limit=limit)
        self.assertTrue(all(row[3]=='pending' for row in self.q.items()))
    def test_persistence_failure_propagates_without_retry(self):
        def fail(*args):raise OSError('disk unavailable')
        self.q.finish=fail
        with self.assertRaises(OSError):drain(self.q,'t',validate=lambda u:None,action=lambda t,u,a:{'recrawl':[{'url':u[0],'status':'accepted','task_id':TASK}]})
        self.assertEqual(sum(row[3]=='in_flight' for row in self.q.items()),1)

if __name__=='__main__':unittest.main()
