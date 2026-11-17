import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hh_auth_probe', ROOT / 'scripts/hh_auth_probe.py')
hh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hh)


class FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self.payload = payload
        self.read_size = None

    def read(self, size):
        self.read_size = size
        return self.payload[:size]


class ProbeTests(unittest.TestCase):
    def check(self, response):
        calls = []
        class Connection:
            def __init__(self, host, timeout):
                calls.append(('connect', host, timeout))
            def request(self, method, path, headers):
                calls.append(('request', method, path, headers))
            def getresponse(self):
                return response
            def close(self):
                calls.append(('close',))
        result = hh.probe('TEST_TOKEN', Connection)
        self.assertEqual(calls[0], ('connect', 'api.hh.ru', 20))
        self.assertEqual(len([call for call in calls if call[0] == 'request']), 1)
        request = calls[1]
        self.assertEqual(request[1], 'GET')
        self.assertTrue(request[2].startswith('/vacancies?'))
        self.assertNotIn('TEST_TOKEN', request[2])
        self.assertEqual(request[3]['Authorization'], 'Bearer TEST_TOKEN')
        self.assertEqual(calls[-1], ('close',))
        self.assertEqual(response.read_size, hh.MAX_BODY + 1)
        return result

    def test_valid_response_makes_one_request_without_returning_data(self):
        response = FakeResponse(200, b'{"items":[{"name":"private"}],"found":1}')
        self.assertEqual(self.check(response), 'ok')

    def test_error_and_redirect_do_not_expose_body_or_follow(self):
        body = json.dumps({'errors': [{'type': 'captcha_required', 'captcha_url': 'secret'}]}).encode()
        self.assertEqual(self.check(FakeResponse(403, body)), 'http=403 api_error=captcha_required')
        self.assertEqual(self.check(FakeResponse(302, b'secret')), 'http=302')
        self.assertEqual(self.check(FakeResponse(403, b'{"errors":[{"type":"secret"}]}')), 'http=403')
        self.assertEqual(self.check(FakeResponse(403, b' ' * (hh.MAX_BODY + 1))), 'http=403')

    def test_invalid_json_large_body_and_network_errors_fail_closed(self):
        self.assertEqual(self.check(FakeResponse(200, b'not json secret')), 'invalid_response')
        self.assertEqual(self.check(FakeResponse(200, b' ' * (hh.MAX_BODY + 1))), 'invalid_response')
        self.assertEqual(self.check(FakeResponse(200, b'{"items":[],"found":true}')), 'invalid_response')
        def fail(*args, **kwargs): raise RuntimeError('secret')
        self.assertEqual(hh.probe('TEST_TOKEN', fail), 'network_error')
        self.assertEqual(hh.probe('not a token\n', fail), 'invalid_token_format')

    def test_confirmation_is_required_before_prompt_or_request(self):
        with patch.object(hh.sys, 'argv', ['script']), patch.object(hh.getpass, 'getpass') as prompt, patch.object(hh, 'probe') as probe, patch.object(hh.sys, 'stderr', io.StringIO()):
            self.assertEqual(hh.main(), 2)
            prompt.assert_not_called()
            probe.assert_not_called()

    def test_hidden_prompt_does_not_print_token(self):
        with patch.object(hh.sys, 'argv', ['script', '--confirm-read-only']), patch.dict(hh.os.environ, {}, clear=True), patch.object(hh.getpass, 'getpass', return_value='TEST_TOKEN'), patch.object(hh, 'probe', return_value='ok') as probe, patch.object(hh.sys, 'stdout', new_callable=io.StringIO) as out:
            self.assertEqual(hh.main(), 0)
            probe.assert_called_once_with('TEST_TOKEN')
            self.assertNotIn('TEST_TOKEN', out.getvalue())


if __name__ == '__main__':
    unittest.main()
