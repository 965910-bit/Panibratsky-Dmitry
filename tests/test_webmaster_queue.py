import os
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from webmaster_queue import Queue, QueueError
from webmaster_actions import BASE, PAGES

URL = BASE + next(iter(PAGES))
A = 'a'*40
B = 'b'*40

class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.path=os.path.join(self.temp.name,'queue.sqlite');self.q=Queue(self.path)
    def tearDown(self):self.q.close();self.temp.cleanup()
    def test_persists_quota_exhausted(self):
        self.q.enqueue([URL],A);self.assertEqual(self.q.claim(),(URL,A));self.q.finish(URL,A,'quota_exhausted');self.q.close();self.q=Queue(self.path)
        self.assertEqual(self.q.claim(),(URL,A))
    def test_unknown_not_retried_after_crash(self):
        self.q.enqueue([URL],A);self.q.claim();self.q.close();self.q=Queue(self.path);self.q.recover_after_stop()
        self.assertIsNone(self.q.claim());self.assertEqual(self.q.items()[0][3],'uncertain')
        self.q.reconcile(URL,A,False);self.assertEqual(self.q.claim(),(URL,A))
    def test_changed_during_claim_is_not_lost(self):
        self.q.enqueue([URL],A);self.q.claim();self.q.enqueue([URL],B);self.q.finish(URL,A,'accepted','task')
        self.assertEqual(self.q.claim(),(URL,B))
    def test_uncertain_updated_revision_waits_for_reconciliation(self):
        self.q.enqueue([URL],A);self.q.claim();self.q.finish(URL,A,'uncertain');self.q.enqueue([URL],B)
        self.assertIsNone(self.q.claim());self.q.reconcile(URL,A,True);self.assertEqual(self.q.claim(),(URL,B))
    def test_same_revision_does_not_resubmit_done(self):
        self.q.enqueue([URL],A);self.q.claim();self.q.finish(URL,A,'accepted','task');self.q.enqueue([URL],A)
        self.assertIsNone(self.q.claim());self.q.enqueue([URL],B);self.assertEqual(self.q.claim(),(URL,B))
    def test_duplicate_already_added_is_not_confirmation_of_revision(self):
        self.q.enqueue([URL],A);self.q.claim();self.q.finish(URL,A,'already_added')
        self.assertEqual(self.q.items()[0][3],'uncertain');self.assertIsNone(self.q.claim())
    def test_two_connections_cannot_claim_same(self):
        self.q.enqueue([URL],A);other=Queue(self.path)
        try:self.assertEqual(self.q.claim(),(URL,A));self.assertIsNone(other.claim())
        finally:other.close()
    def test_wrong_claim_and_invalid_input(self):
        with self.assertRaises(Exception):self.q.enqueue(['https://example.org/'],A)
        self.q.enqueue([URL],A);self.q.claim()
        with self.assertRaises(QueueError):self.q.finish(URL,B,'already_added')
        with self.assertRaises(QueueError):self.q.finish(URL,A,'accepted')
        self.assertEqual(self.q.items()[0][3],'in_flight')

if __name__=='__main__':unittest.main()
