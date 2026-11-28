import contextlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from webmaster_queue import Queue
from webmaster_actions import BASE
import webmaster_queue_cycle as c

SHA='a'*40; URL=BASE+'wiki.html'
class Tests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.db=os.path.join(self.temp.name,'queue.db')
    def tearDown(self):self.temp.cleanup()
    def prep(self,queue,*args):
        queue.enqueue([URL],SHA)
        return {'mode':'prepare_only','deployment':{'target':SHA},'blocked':0,'pending':[URL]}
    def test_prepare_only_default_never_drains(self):
        with mock.patch.object(c,'drain',side_effect=AssertionError('send')):
            result=c.cycle(self.db,'x/y','private',SHA,prepare_queue=self.prep,drain_queue=lambda *a,**kw:self.fail('drained'))
        self.assertEqual(result['mode'],'prepare_only');self.assertNotIn('private',str(result))
        q=Queue(self.db)
        try:self.assertEqual(q.items()[0][3],'pending')
        finally:q.close()
    def test_nonbool_or_missing_token_stops_before_queue(self):
        for apply,token in [('yes','x'),(True,''),(True,'x\ny')]:
            with self.assertRaises(c.CycleError):c.cycle(self.db,'x/y','g',SHA,token,apply=apply)
        self.assertFalse(os.path.exists(self.db))
    def test_preflight_called_for_each_write(self):
        calls=[]
        def fake_drain(queue,token,validate):
            validate([URL]);return {'status':'ok','results':[]}
        result=c.cycle(self.db,'x/y','private',SHA,'y',apply=True,prepare_queue=self.prep,drain_queue=fake_drain,preflight=lambda *a:calls.append(a))
        self.assertEqual(result['result']['status'],'ok');self.assertEqual(calls,[('x/y','private',SHA,[URL])])
    def test_unknown_queue_blocks_without_drain(self):
        def prep(queue,*args):return {'mode':'prepare_only','deployment':{'target':SHA},'blocked':1}
        result=c.cycle(self.db,'x/y','g',SHA,'y',apply=True,prepare_queue=prep,drain_queue=lambda *a,**k:self.fail('drained'))
        self.assertEqual(result['status'],'blocked')
    def test_ambiguous_provider_write_survives_restart_and_blocks(self):
        from webmaster_queue_worker import drain
        writes=[]
        def send(*args):writes.append(1);raise TimeoutError('unknown provider outcome')
        def draining(queue,token,validate):return drain(queue,token,validate=validate,action=send)
        first=c.cycle(self.db,'x/y','g',SHA,'y',apply=True,prepare_queue=self.prep,drain_queue=draining,preflight=lambda *a:None)
        self.assertEqual(first['result']['status'],'uncertain');self.assertEqual(writes,[1])
        def prepared(queue,*args):return {'mode':'prepare_only','deployment':{'target':SHA},'blocked':sum(row[3] in ('uncertain','in_flight') for row in queue.items())}
        second=c.cycle(self.db,'x/y','g',SHA,'y',apply=True,prepare_queue=prepared,drain_queue=draining,preflight=lambda *a:None)
        self.assertEqual(second['status'],'blocked');self.assertEqual(writes,[1])
    def test_failed_preflight_releases_claim_without_provider_write(self):
        from webmaster_queue_worker import drain
        send=mock.Mock()
        def draining(queue,token,validate):return drain(queue,token,validate=validate,action=send)
        def reject(*args):raise ValueError('live changed')
        result=c.cycle(self.db,'x/y','g',SHA,'y',apply=True,prepare_queue=self.prep,drain_queue=draining,preflight=reject)
        self.assertEqual(result['result']['status'],'preflight_failed');send.assert_not_called()
        q=Queue(self.db)
        try:self.assertEqual(q.items()[0][3],'pending')
        finally:q.close()
    def test_lock_prevents_second_process_and_releases(self):
        command=[sys.executable,'-c','import sys;sys.path.insert(0,sys.argv[1]);from webmaster_queue_cycle import exclusive_lock;\nwith exclusive_lock(sys.argv[2]): print("locked")',str(Path(__file__).resolve().parents[1]/'scripts'),self.db]
        with c.exclusive_lock(self.db):
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,0);self.assertIn('locked',result.stdout)
    def test_symlinks_and_relative_paths_rejected(self):
        os.symlink(os.path.join(self.temp.name,'target'),self.db)
        with self.assertRaises(c.CycleError):
            with c.exclusive_lock(self.db):pass
        with self.assertRaises(c.CycleError):
            with c.exclusive_lock('relative.db'):pass
    def test_preflight_fails_when_main_changes(self):
        refs=[]
        def fetch(url,token):
            if url.endswith('/git/ref/heads/main'):
                refs.append(1);data={'object':{'sha':SHA if len(refs)==1 else 'b'*40}}
            elif url.endswith('/pages/builds/latest'):data={'status':'built','commit':SHA}
            else:data={'id':c.REPOSITORY_ID}
            return 200,{},json.dumps(data).encode()
        with self.assertRaises(c.CycleError):c.verify_before_write('x/y','g',SHA,[URL],git=lambda *a:SHA,fetch=fetch,validate=lambda u:None)
if __name__=='__main__':unittest.main()
