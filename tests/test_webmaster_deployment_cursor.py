import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from webmaster_queue import Queue,QueueError
from webmaster_actions import BASE,PAGES
import webmaster_deployment_cursor as d

A='a'*40; B='b'*40; C='c'*40; D='d'*40
URL=BASE+next(iter(PAGES))
def ancestor(a,b):return (a,b) in {(A,B),(A,C),(B,C)}

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=os.path.join(self.tmp.name,'q.db');self.q=Queue(self.path)
    def tearDown(self):self.q.close();self.tmp.cleanup()
    def advance(self,target,baseline=A,changed=lambda a,b:[URL]):return self.q.enqueue_deployment(target,baseline,ancestor=ancestor,changed=changed)
    def test_catchup_and_persistence(self):
        r=self.advance(C);self.assertEqual(r['count'],1);self.q.close();self.q=Queue(self.path)
        self.assertEqual(self.q.cursor(),C);self.assertEqual(self.q.items()[0][1],C)
    def test_stale_event_does_not_overwrite(self):
        self.advance(C);r=self.advance(B);self.assertEqual(r['status'],'stale');self.assertEqual(self.q.cursor(),C);self.assertEqual(self.q.items()[0][1],C)
    def test_duplicate_event_does_not_enqueue_again(self):
        self.advance(B);self.q.claim();self.q.finish(URL,B,'already_added')
        r=self.advance(B,changed=lambda a,b:self.fail('unexpected diff'))
        self.assertEqual(r['count'],0);self.assertEqual(self.q.items()[0][3],'done')
    def test_diverged_or_bad_baseline_fails_without_state(self):
        for base in (None,D,'bad'):
            with self.assertRaises(QueueError):self.advance(B,base)
            self.assertIsNone(self.q.cursor());self.assertEqual(self.q.items(),[])
    def test_invalid_or_failing_diff_rolls_back(self):
        self.advance(B)
        for diff in (lambda a,b:[URL,'https://evil.test/'],lambda a,b:[URL,URL],lambda a,b:1/0):
            with self.assertRaises(Exception):self.advance(C,changed=diff)
            self.assertEqual(self.q.cursor(),B);self.assertEqual(self.q.items()[0][1],B)
    def test_no_changes_advances(self):
        self.assertEqual(self.advance(B,changed=lambda a,b:[])['count'],0);self.assertEqual(self.q.cursor(),B)
    def test_inflight_update_remains_pending_when_accepted(self):
        self.advance(B);self.q.claim();self.advance(C);self.q.finish(URL,B,'accepted','task')
        self.assertEqual(self.q.claim(),(URL,C))
    def test_other_connection_stale_cannot_reverse(self):
        self.advance(B);other=Queue(self.path)
        try:
            other.enqueue_deployment(C,None,ancestor=ancestor,changed=lambda a,b:[URL])
            self.assertEqual(self.advance(B)['status'],'stale');self.assertEqual(self.q.cursor(),C)
        finally:other.close()
    def test_git_adapter_errors_not_treated_as_not_ancestor(self):
        with mock.patch.object(d.subprocess,'run',return_value=mock.Mock(returncode=128)):
            with self.assertRaises(RuntimeError):d.is_ancestor(A,B)
    def test_git_diff_restricts_to_canonical(self):
        with mock.patch.object(d.subprocess,'run',return_value=mock.Mock(stdout='wiki.html\nREADME.md\n')):
            self.assertEqual(d.changed_canonical(A,B),[BASE+'wiki.html'])

if __name__=='__main__':unittest.main()
