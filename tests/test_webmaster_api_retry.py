import io
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import webmaster_actions as w

URL=w.YANDEX_API+'/user'

class RetryTests(unittest.TestCase):
    def test_network_get_retries_bounded_then_succeeds(self):
        with mock.patch.object(w,'_api_once',side_effect=[w.NetworkError('x'),w.ApiError(503),{'user_id':1}]) as req, mock.patch.object(w.time,'sleep') as sleep:
            self.assertEqual(w.api(URL,'t','OAuth'),{'user_id':1});self.assertEqual(req.call_count,3)
            self.assertEqual(sleep.call_args_list,[mock.call(1),mock.call(2)])
    def test_get_fails_after_three(self):
        with mock.patch.object(w,'_api_once',side_effect=w.NetworkError('x')) as req, mock.patch.object(w.time,'sleep'):
            with self.assertRaises(w.NetworkError):w.api(URL,'t','OAuth')
            self.assertEqual(req.call_count,3)
    def test_no_retry_writes_including_quota_error(self):
        for method in ('POST','PUT'):
            for error in (w.NetworkError('x'),w.ApiError(503),w.ApiError(429,'QUOTA_EXCEEDED')):
                with self.subTest(method=method,error=error),mock.patch.object(w,'_api_once',side_effect=error) as req,mock.patch.object(w.time,'sleep') as sleep:
                    with self.assertRaises(w.ActionError):w.api(URL,'t','OAuth',method,{})
                    self.assertEqual(req.call_count,1);sleep.assert_not_called()
    def test_no_retry_auth_or_malformed_json(self):
        for error in (w.ApiError(403),w.ActionError('invalid response')):
            with mock.patch.object(w,'_api_once',side_effect=error) as req,mock.patch.object(w.time,'sleep') as sleep:
                with self.assertRaises(w.ActionError):w.api(URL,'t','OAuth')
                self.assertEqual(req.call_count,1);sleep.assert_not_called()
    def test_honor_short_delay_skip_long_or_unparseable(self):
        with mock.patch.object(w,'_api_once',side_effect=[w.ApiError(429,retry_after=5),{}]),mock.patch.object(w.time,'sleep') as sleep:
            w.api(URL,'t','OAuth');sleep.assert_called_once_with(5)
        for delay in (6,-1):
            with mock.patch.object(w,'_api_once',side_effect=w.ApiError(503,retry_after=delay)) as req,mock.patch.object(w.time,'sleep') as sleep:
                with self.assertRaises(w.ApiError):w.api(URL,'t','OAuth')
                self.assertEqual(req.call_count,1);sleep.assert_not_called()
    def test_get_with_body_never_retries(self):
        with mock.patch.object(w,'_api_once',side_effect=w.NetworkError('x')) as req,mock.patch.object(w.time,'sleep') as sleep:
            with self.assertRaises(w.NetworkError):w.api(URL,'t','OAuth',body={'x':1})
            self.assertEqual(req.call_count,1);sleep.assert_not_called()
    def test_http_header_parsing_and_secret_not_in_error(self):
        for raw,expected in [('3',3),('Wed, 21 Oct 2015 07:28:00 GMT',-1),('9999999',-1)]:
            err=urllib.error.HTTPError(URL,503,'private',{'Retry-After':raw},io.BytesIO(b'{"sensitive":"secret"}'))
            with mock.patch.object(w.urllib.request,'build_opener') as opener:
                opener.return_value.open.side_effect=err
                with self.assertRaises(w.ApiError) as raised:w._api_once(URL,'secret','OAuth')
                self.assertEqual(raised.exception.retry_after,expected);self.assertNotIn('secret',str(raised.exception))
    def test_invalid_response_is_not_network(self):
        response=mock.MagicMock();response.__enter__.return_value.read.return_value=b'not json'
        with mock.patch.object(w.urllib.request,'build_opener') as opener,mock.patch.object(w.time,'sleep') as sleep:
            opener.return_value.open.return_value=response
            with self.assertRaises(w.ActionError):w.api(URL,'t','OAuth')
            self.assertEqual(opener.return_value.open.call_count,1);sleep.assert_not_called()

if __name__=='__main__':unittest.main()
