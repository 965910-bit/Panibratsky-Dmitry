import json
import os
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import webmaster_readonly as w

START, END = date(2026, 1, 1), date(2026, 1, 28)

class TestWebmaster(unittest.TestCase):
    def test_google_exact_property_aggregate_and_missing_row(self):
        calls = []
        def req(url, token, scheme, body=None):
            calls.append((url, scheme, body))
            if url.endswith('/sites'): return {'siteEntry': [{'siteUrl': w.DOMAIN_PROPERTY}]}
            if url.endswith('/sitemaps'): return {'sitemap': [{'path': w.SITE + 'sitemap.xml', 'errors': '0'}]}
            return {}
        r = w.google_snapshot('token', START, END, req)
        self.assertEqual(r['property'], w.DOMAIN_PROPERTY)
        self.assertIsNone(r['performance'])
        self.assertEqual(r['sitemap'][0]['errors'], '0')
        self.assertEqual(calls[-1][2]['dataState'], 'final')
        self.assertNotIn('dimensions', calls[-1][2])
        self.assertTrue(all(scheme == 'Bearer' for _, scheme, _ in calls))

    def test_yandex_selects_only_exact_verified_host_and_encodes_id(self):
        calls = []
        def req(url, token, scheme, body=None):
            calls.append((url, scheme))
            if url.endswith('/user'): return {'user_id': 123}
            if url.endswith('/hosts'): return {'hosts': [{'ascii_host_url': w.SITE, 'host_id': 'https:scm-news.ru:443', 'verified': True}]}
            if 'user-added-sitemaps' in url: return {'count': 1, 'sitemaps': [{'sitemap_url': w.SITE + 'sitemap.xml'}]}
            return {'indicators': {'TOTAL_CLICKS': [{'date': '2026-01-01', 'value': 1}]}}
        result = w.yandex_snapshot('token', START, END, req)
        self.assertTrue(result['sitemap_in_first_100'])
        self.assertTrue(any('https%3Ascm-news.ru%3A443' in url for url, _ in calls))
        self.assertTrue(all(scheme == 'OAuth' for _, scheme in calls))
        self.assertNotIn('user_id', result)

    def test_missing_or_unverified_not_reported_as_zero(self):
        out = w.snapshot({}, START, END)
        self.assertEqual(out['sources']['google']['status'], 'not_connected')
        def req(url, token, scheme, body=None):
            if url.endswith('/user'): return {'user_id': 1}
            return {'hosts': [{'ascii_host_url': w.SITE, 'host_id': 'id', 'verified': False}]}
        out = w.snapshot({'yandex': 'secret'}, START, END, req)
        self.assertEqual(out['sources']['yandex']['status'], 'error')
        self.assertNotIn('secret', json.dumps(out))

    def test_refuses_unexpected_hosts_and_header_injection(self):
        with self.assertRaises(w.SnapshotError): w.request_json('https://evil.test/', 'secret', 'Bearer')
        with self.assertRaises(w.SnapshotError): w.request_json(w.GOOGLE_API + '/sites', 'x\r\nBad: x', 'Bearer')

    def test_no_credentials_no_network(self):
        with mock.patch.object(w, 'request_json', side_effect=AssertionError('unexpected network')):
            # Explicitly inject because defaults are bound when functions are defined.
            r = w.snapshot({}, START, END, w.request_json)
        self.assertEqual(r['sources']['yandex']['status'], 'not_connected')

    def test_fails_when_any_provider_not_configured(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch('builtins.print'):
            self.assertEqual(w.main([]), 1)

if __name__ == '__main__': unittest.main()
