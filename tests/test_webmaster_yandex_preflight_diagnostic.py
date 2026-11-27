import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_yandex_preflight_diagnostic as w
SHA='a'*40
class Tests(unittest.TestCase):
    def fetch(self, main=SHA, build=SHA):
        def f(url,token):return 200,{},json.dumps({'status':'built','commit':build} if url.endswith('latest') else {'object':{'sha':main}}).encode()
        return f
    def test_success(self):self.assertEqual(w.run('x/y','t',git=lambda *a:SHA,fetch=self.fetch(),validate=lambda u:None),'ok')
    def test_fail_closed_at_each_stage(self):
        self.assertEqual(w.run('x/y','',git=lambda *a:SHA),'configuration')
        self.assertEqual(w.run('x/y','t',git=lambda *a:SHA,fetch=self.fetch(main='b'*40)),'main_mismatch')
        self.assertEqual(w.run('x/y','t',git=lambda *a:SHA,fetch=self.fetch(build='b'*40)),'pages_mismatch')
        def bad(u):raise RuntimeError('private response')
        self.assertEqual(w.run('x/y','t',git=lambda *a:SHA,fetch=self.fetch(),validate=bad),'live_preflight_failed')
    def test_never_leak_errors(self):
        def bad(*a,**kw):raise ValueError('token=private')
        self.assertEqual(w.run('x/y','t',git=bad),'github_main_unavailable')
if __name__=='__main__':unittest.main()
