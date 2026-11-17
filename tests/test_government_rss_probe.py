import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from scripts import probe_government_rss as probe


class FakeOpener:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.urls = []

    def open(self, request, timeout):
        self.urls.append(request.full_url)
        response = next(self.replies)
        if isinstance(response, Exception):
            raise response
        return io.BytesIO(response)


class ProbeTest(unittest.TestCase):
    def test_valid_feed(self):
        opener = FakeOpener([b'User-agent: *\nDisallow: /private\n',
            b'<rss><channel><item><title>A</title><link>https://government.ru/a</link></item></channel></rss>'])
        self.assertEqual(probe.check(opener), (True, 'rss-validated'))
        self.assertEqual(len(opener.urls), 2)

    def test_denied_robots_stops_without_feed_request(self):
        opener = FakeOpener([b'User-agent: *\nDisallow: /\n'])
        self.assertEqual(probe.check(opener), (False, 'robots-disallowed'))
        self.assertEqual(len(opener.urls), 1)

    def test_http_error_on_robots_stops_without_feed_request(self):
        opener = FakeOpener([HTTPError('https://government.ru/robots.txt', 403, 'Forbidden', {}, None)])
        self.assertEqual(probe.check(opener), (False, 'http-403'))
        self.assertEqual(len(opener.urls), 1)

    def test_doctype_rejected(self):
        opener = FakeOpener([b'User-agent: *\nDisallow: /private\n', b'<!DOCTYPE rss><rss/>'])
        self.assertEqual(probe.check(opener), (False, 'xml-dtd-rejected'))

    def test_requires_explicit_opt_in(self):
        with patch('sys.argv', ['probe']), patch.object(probe, 'check') as check:
            self.assertEqual(probe.main(), 2)
            check.assert_not_called()


if __name__ == '__main__':
    unittest.main()
