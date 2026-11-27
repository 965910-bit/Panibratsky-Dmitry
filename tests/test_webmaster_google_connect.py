import base64
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_google_connect as w

class GoogleConnectTests(unittest.TestCase):
    def test_pkce_and_scope(self):
        verifier, challenge = w.pkce()
        expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        self.assertEqual(challenge, expected)
        url = w.auth_url('client','http://127.0.0.1:123/callback','state',challenge)
        self.assertIn('code_challenge_method=S256',url)
        self.assertIn('auth%2Fwebmasters',url)
        self.assertNotIn(verifier,url)
    def test_callback_state_and_path(self):
        self.assertEqual(w.parse_callback('/callback?state=s&code=c','s'),'c')
        for path in ['/other?state=s&code=c','/callback?state=wrong&code=c','/callback?state=s&state=s&code=c','http://evil/callback?state=s&code=c']:
            self.assertIsNone(w.parse_callback(path,'s'))
        with self.assertRaises(w.SetupError):w.parse_callback('/callback?state=s&error=access_denied','s')
    def test_desktop_client_fixed_endpoints(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'client.json'
            p.write_text(json.dumps({'installed':{'client_id':'id','client_secret':'secret','auth_uri':w.AUTH,'token_uri':w.TOKEN}}))
            self.assertEqual(w.load_desktop_client(p),('id','secret'))
            p.write_text(json.dumps({'installed':{'client_id':'id','client_secret':'secret','auth_uri':'https://evil.test','token_uri':w.TOKEN}}))
            with self.assertRaises(w.SetupError):w.load_desktop_client(p)
    def test_secrets_sent_only_stdin_no_shell(self):
        with mock.patch.object(w.subprocess,'run') as run:
            w.gh_store('owner/repository','private-id','private-secret','private-refresh')
        self.assertEqual(len(run.call_args_list),3)
        for c in run.call_args_list:
            self.assertNotIn('private',str(c.args[0]))
            self.assertIsInstance(c.kwargs['input'],bytes)
            self.assertNotIn('shell',c.kwargs)
    def test_existing_secret_prevents_overwrite(self):
        p=mock.Mock(stdout=w.SECRET_NAMES[0]+'\tdate\n')
        repo=mock.Mock(stdout='owner/repository\n')
        with mock.patch.object(w.subprocess,'run',side_effect=[repo,p]):
            with self.assertRaises(w.SetupError):w.gh_check()
    def test_decline_never_connects(self):
        with mock.patch('builtins.input',return_value='нет'),mock.patch('builtins.print'),mock.patch.object(w,'gh_check') as check:
            self.assertEqual(w.main(['client.json']),0)
            check.assert_not_called()

if __name__=='__main__':unittest.main()
