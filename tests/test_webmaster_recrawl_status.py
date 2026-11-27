import os
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from webmaster_queue import Queue,QueueError
from webmaster_actions import BASE,PAGES,SITE,ActionError
from webmaster_recrawl_status import check_receipts

URL=BASE+next(iter(PAGES));REV='a'*40;TASK='c7fe80c0-36e3-11e6-8b2d-df96aa592c0a';TASK2='d7fe80c0-36e3-11e6-8b2d-df96aa592c0a'

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.q=Queue(os.path.join(self.tmp.name,'q.db'))
        self.q.enqueue([URL],REV);self.q.claim();self.q.finish(URL,REV,'accepted',TASK)
    def tearDown(self):self.q.close();self.tmp.cleanup()
    def request(self,state='DONE',url=URL,task=TASK):
        def f(path,token,scheme):
            self.assertEqual(scheme,'OAuth')
            if path.endswith('/user'):return {'user_id':1}
            if path.endswith('/hosts'):return {'hosts':[{'ascii_host_url':SITE,'verified':True,'host_id':'https:scm-news.ru:443'}]}
            self.assertIn('https%3Ascm-news.ru%3A443',path)
            return {'task_id':task,'url':url,'state':state}
        return f
    def test_done_is_crawl_not_index(self):
        result=check_receipts(self.q,'token',request=self.request())
        self.assertEqual(result['tasks'][0]['status'],'DONE');self.assertFalse(result['indexing_guaranteed'])
        self.assertEqual(self.q.receipts()[0][3],'DONE');self.assertEqual(check_receipts(self.q,'token',request=lambda *a:self.fail())['tasks'],[])
    def test_pending_then_failed(self):
        self.assertEqual(check_receipts(self.q,'t',request=self.request('IN_PROGRESS'))['tasks'][0]['status'],'IN_PROGRESS')
        self.assertEqual(check_receipts(self.q,'t',request=self.request('FAILED'))['tasks'][0]['status'],'FAILED')
    def test_mismatch_and_timeout_unknown_no_false_failure(self):
        self.assertEqual(check_receipts(self.q,'t',request=self.request(url='https://evil.test/'))['tasks'][0]['status'],'UNKNOWN')
        self.assertIsNone(self.q.receipts()[0][3]);self.assertIsNotNone(self.q.receipts()[0][4])
        def req(path,*args):
            if path.endswith('/user') or path.endswith('/hosts'):return self.request()(path,*args)
            raise TimeoutError('secret')
        self.assertEqual(check_receipts(self.q,'t',request=req)['status'],'partial')
    def test_bad_host_stops(self):
        def req(path,*a):return {'user_id':1} if path.endswith('/user') else {'hosts':[]}
        with self.assertRaises(ActionError):check_receipts(self.q,'t',request=req)
        self.assertIsNone(self.q.receipts()[0][4])
    def test_history_survives_new_revision(self):
        self.q.enqueue([URL],'b'*40);self.q.claim();self.q.finish(URL,'b'*40,'accepted',TASK2)
        self.assertEqual(len(self.q.receipts()),2)
    def test_duplicate_task_rejected_atomically(self):
        self.q.enqueue([URL],'b'*40);self.q.claim()
        with self.assertRaises(QueueError):self.q.finish(URL,'b'*40,'accepted',TASK)
        self.assertEqual(self.q.items()[0][3],'in_flight')
    def test_legacy_receipt_backfill(self):
        self.q.db.execute('DROP TABLE recrawl_receipts')
        self.q.close();self.q=Queue(os.path.join(self.tmp.name,'q.db'))
        self.assertEqual(self.q.receipts()[0][:3],(TASK,URL,REV))
    def test_error_after_progress_does_not_erase_observation(self):
        check_receipts(self.q,'t',request=self.request('IN_PROGRESS'))
        check_receipts(self.q,'t',request=self.request('NEW_STATE'))
        self.assertEqual(self.q.receipts()[0][3],'IN_PROGRESS')
    def test_invalid_token_or_limit(self):
        with self.assertRaises(ActionError):check_receipts(self.q,'')
        with self.assertRaises(QueueError):check_receipts(self.q,'t',limit=51)

if __name__=='__main__':unittest.main()
