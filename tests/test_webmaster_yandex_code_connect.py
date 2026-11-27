import sys
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urlsplit, parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_yandex_code_connect as w

CID='a'*32
class Tests(unittest.TestCase):
    def test_fixed_official_authorization_pkce(self):
        v,c=w.pkce();url=w.build_auth_url(CID,c);p=urlsplit(url);q=parse_qs(p.query)
        self.assertEqual((p.scheme,p.netloc,p.path),('https','oauth.yandex.ru','/authorize'))
        self.assertEqual(q['code_challenge_method'],['S256']);self.assertEqual(q['scope'],[w.SCOPES])
        self.assertEqual(q['redirect_uri'],[w.REDIRECT]);self.assertNotIn(v,url)
        with self.assertRaises(w.SetupError):w.build_auth_url('https://evil.test/',c)
    def test_exchange_uses_verifier_not_client_secret(self):
        def request(url,fields):
            self.assertEqual(url,w.TOKEN);self.assertEqual(fields['grant_type'],'authorization_code')
            self.assertEqual(fields['code_verifier'],'verifier');self.assertNotIn('client_secret',fields)
            return {'access_token':'test-token','scope':w.SCOPES}
        self.assertEqual(w.exchange(CID,'test-code','verifier',request=request),'test-token')
    def test_insufficient_permissions_and_error_are_safe(self):
        for response in ({'access_token':'t','scope':'webmaster:hostinfo'}, {'error':'invalid_grant','error_description':'private'}, {'error':'secret text'}):
            with self.assertRaises(w.SetupError) as exc:w.exchange(CID,'code','v',request=lambda *a:response)
            self.assertNotIn('private',str(exc.exception));self.assertNotIn('secret text',str(exc.exception))
    def test_invalid_code_fails_without_network(self):
        req=mock.Mock()
        with self.assertRaises(w.SetupError):w.exchange(CID,'http://evil/','v',request=req)
        req.assert_not_called()
    def test_decline_no_calls(self):
        with mock.patch('builtins.input',return_value='нет'),mock.patch('builtins.print'),mock.patch.object(w,'gh_check') as check:
            self.assertEqual(w.main(),0);check.assert_not_called()
    def test_full_flow_mocks(self):
        with mock.patch('builtins.input',side_effect=['ДА',CID]),mock.patch('builtins.print'),mock.patch.object(w,'gh_check',return_value='owner/repo'),mock.patch.object(w.webbrowser,'open',return_value=True),mock.patch.object(w.getpass,'getpass',return_value='one-time-code'),mock.patch.object(w,'exchange',return_value='token') as exchange,mock.patch.object(w,'verify_site') as verify,mock.patch.object(w,'gh_store') as store:
            self.assertEqual(w.main(),0);exchange.assert_called_once();verify.assert_called_once_with('token');store.assert_called_once_with('owner/repo','token')
    def test_failure_does_not_store(self):
        with mock.patch('builtins.input',side_effect=['ДА',CID]),mock.patch('builtins.print'),mock.patch.object(w,'gh_check',return_value='owner/repo'),mock.patch.object(w.webbrowser,'open',return_value=True),mock.patch.object(w.getpass,'getpass',return_value='code'),mock.patch.object(w,'exchange',side_effect=w.SetupError('rejected')),mock.patch.object(w,'gh_store') as store:
            self.assertEqual(w.main(),1);store.assert_not_called()

if __name__=='__main__':unittest.main()
