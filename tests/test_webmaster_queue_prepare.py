import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from webmaster_queue import Queue
from webmaster_actions import BASE
import webmaster_queue_prepare as prep

A='a'*40; B='b'*40
URL=BASE+'wiki.html'
class Tests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory();self.path=os.path.join(self.dir.name,'queue.sqlite');self.q=Queue(self.path)
    def tearDown(self):self.q.close();self.dir.cleanup()
    def fetch(self, *, head=B, build=B, repo_id=prep.REPOSITORY_ID, advance=False):
        refs=[]
        def call(url,token):
            self.assertEqual(token,'private')
            if url.endswith('/git/ref/heads/main'):
                refs.append(1);data={'object':{'sha':A if advance and len(refs)>1 else head}}
            elif url.endswith('/pages/builds/latest'):data={'status':'built','commit':build}
            else:data={'id':repo_id}
            return 200,{},json.dumps(data).encode()
        return call
    def run_prepare(self,**kwargs):
        args={'git':lambda *a:B,'fetch':self.fetch(),'validate':lambda urls:None,
              'ancestor':lambda x,y:(x,y)==(A,B),'changed':lambda a,b:[URL]}
        args.update(kwargs)
        return prep.prepare(self.q,'owner/repo','private',A,**args)
    def test_persistent_preparation_no_claim_and_idempotence(self):
        result=self.run_prepare();self.assertEqual(result['mode'],'prepare_only');self.assertEqual(result['pending'],[URL]);self.assertEqual(self.q.items()[0][3],'pending')
        self.q.close();self.q=Queue(self.path)
        result=self.run_prepare(changed=lambda *a:self.fail('unexpected diff'))
        self.assertEqual(result['deployment']['count'],0);self.assertEqual(result['pending'],[URL])
        self.assertNotIn('private',str(result))
    def test_stale_or_unsafe_preconditions_no_mutation(self):
        for opts in ({'fetch':self.fetch(head=A)}, {'fetch':self.fetch(build=A)}, {'fetch':self.fetch(repo_id=1)}, {'fetch':self.fetch(advance=True)}, {'validate':lambda u:(_ for _ in ()).throw(ValueError('bad live'))}):
            with self.assertRaises(Exception):self.run_prepare(**opts)
            self.assertIsNone(self.q.cursor());self.assertEqual(self.q.items(),[])
    def test_baseline_required_first_time(self):
        with self.assertRaises(Exception):prep.prepare(self.q,'a/b','private',None,git=lambda *a:B,fetch=self.fetch(),validate=lambda u:None,ancestor=lambda a,b:True,changed=lambda a,b:[URL])
        self.assertIsNone(self.q.cursor())
    def test_uncertain_claim_remains_blocked(self):
        self.run_prepare();self.q.claim();self.q.finish(URL,B,'uncertain')
        result=self.run_prepare();self.assertEqual(result['blocked'],1);self.assertEqual(result['pending'],[])
        self.assertEqual(self.q.items()[0][3],'uncertain')
    def test_stale_cursor_stops_before_any_sending(self):
        self.q.enqueue_deployment('c'*40,A,ancestor=lambda a,b:True,changed=lambda a,b:[URL])
        with self.assertRaises(prep.PreparationError):
            self.run_prepare(ancestor=lambda old,new: (old,new)==(B,'c'*40))
        self.assertEqual(self.q.cursor(),'c'*40)
        self.assertEqual(self.q.items()[0][3],'pending')
    def test_invalid_identity_no_fetch(self):
        def bad(*a,**kw):self.fail('unexpected request')
        for repo,token in [('https://evil/','t'),('a/b',''),('a/b','x\ny')]:
            with self.assertRaises(prep.PreparationError):prep.prepare(self.q,repo,token,A,fetch=bad)

if __name__=='__main__':unittest.main()
