import sys
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_yandex_connect as w

class YandexConnectTests(unittest.TestCase):
    def test_device_only_opens_official_url(self):
        def req(endpoint, fields):
            self.assertEqual(endpoint,w.DEVICE);self.assertEqual(fields['scope'],','.join(w.SCOPES.split()))
            return {'device_code':'device','user_code':'abc12345','verification_url':w.VERIFY,'interval':5,'expires_in':300}
        self.assertEqual(w.request_device('cid',req),('device','abc12345',5,300))
        def bad(endpoint,fields):return {'device_code':'d','user_code':'abc12345','verification_url':'https://evil.test/','interval':5,'expires_in':300}
        with self.assertRaises(w.SetupError):w.request_device('cid',bad)
    def test_pending_then_success_and_scopes(self):
        replies=iter([{'error':'authorization_pending'},{'access_token':'SECRET','scope':w.SCOPES}])
        now=[0]; pauses=[]
        def sleep(n):pauses.append(n);now[0]+=n
        token=w.wait_for_token('id','secret','device',5,100,request=lambda *args:next(replies),clock=lambda:now[0],sleep=sleep)
        self.assertEqual(token,'SECRET');self.assertEqual(pauses,[5,5])
    def test_insufficient_scope_fails(self):
        with self.assertRaises(w.SetupError):
            w.wait_for_token('id','s','d',5,100,request=lambda *a:{'access_token':'x','scope':'webmaster:hostinfo'},clock=lambda:0,sleep=lambda n:None)
    def test_verify_only_exact_confirmed_site(self):
        def req(url, token, scheme):
            return {'user_id':1} if url.endswith('/user') else {'hosts':[{'ascii_host_url':w.SITE,'verified':True}]}
        w.verify_site('secret',req)
        def bad(url,token,scheme):return {'user_id':1} if url.endswith('/user') else {'hosts':[{'ascii_host_url':w.SITE,'verified':False}]}
        with self.assertRaises(w.SetupError):w.verify_site('secret',bad)
    def test_existing_secret_is_not_overwritten(self):
        repo=mock.Mock(stdout='owner/repository\n')
        listing=mock.Mock(stdout=w.SECRET_NAME+'\tdate\n')
        with mock.patch.object(w.subprocess,'run',side_effect=[repo,listing]):
            with self.assertRaises(w.SetupError):w.gh_check()
    def test_slow_down_increases_interval(self):
        replies=iter([{'error':'slow_down'},{'access_token':'TOKEN'}])
        now=[0]; pauses=[]
        def sleep(n):pauses.append(n);now[0]+=n
        w.wait_for_token('id','s','d',5,100,request=lambda *a:next(replies),clock=lambda:now[0],sleep=sleep)
        self.assertEqual(pauses,[5,10])
    def test_secret_via_stdin_only(self):
        with mock.patch.object(w.subprocess,'run') as run:w.gh_store('owner/repo','private-token')
        self.assertNotIn('private-token',str(run.call_args.args[0]))
        self.assertEqual(run.call_args.kwargs['input'],b'private-token')
        self.assertNotIn('shell',run.call_args.kwargs)
    def test_decline_does_not_connect(self):
        with mock.patch('builtins.input',return_value='нет'),mock.patch('builtins.print'),mock.patch.object(w,'gh_check') as check:
            self.assertEqual(w.main(),0);check.assert_not_called()

if __name__=='__main__':unittest.main()
