import json
import io
from unittest import mock
from pathlib import Path
import sys
import unittest
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import live_seo_check as monitor


class LiveSEOTests(unittest.TestCase):
    pages = ['', 'about.html']

    def responses(self):
        sitemap = ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
                   ''.join(f'<url><loc>{monitor.BASE}{p}</loc></url>' for p in self.pages) + '</urlset>').encode()
        result = {monitor.BASE + 'sitemap.xml': (200, {}, sitemap),
                  monitor.BASE + 'robots.txt': (200, {}, f'Sitemap: {monitor.BASE}sitemap.xml\n'.encode())}
        for p in self.pages:
            result[monitor.BASE + p] = (200, {},
                f'<html><head><meta name="description" content="Unique description {p or "home"}"><link rel="canonical" href="{monitor.BASE}{p}"><script type="application/ld+json">{{"@type":"WebPage"}}</script></head></html>'.encode())
        return result

    def test_valid_fixed_urls(self):
        items = self.responses(); calls = []
        def fake(url): calls.append(url); return items[url]
        result = monitor.check(fake, self.pages)
        self.assertEqual(result['findings'], [])
        self.assertEqual(len(calls), 4)
        self.assertEqual(set(calls), set(items))

    def test_sitemap_robots_canonical_noindex_json_and_network_failures(self):
        cases = {
            'sitemap.xml': (200, {}, b'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>'),
            'robots.txt': (200, {}, b'User-agent: *\nAllow: /'),
            '': (200, {'X-Robots-Tag': 'googlebot: noindex'}, b'<html><head><link rel="canonical" href="https://elsewhere/"><meta name="robots" content="noindex"><script type="application/ld+json">not json</script></head></html>'),
        }
        items = self.responses()
        for path, result in cases.items(): items[monitor.BASE + path] = result
        findings = monitor.check(lambda url: items[url], self.pages)['findings']
        for fragment in ('URL set differs', 'sitemap directive', 'canonical mismatch', 'meta robots', 'X-Robots-Tag', 'JSON-LD'):
            self.assertTrue(any(fragment in line for line in findings), (fragment, findings))
        items = self.responses(); items[monitor.BASE] = (302, {}, b'')
        self.assertTrue(any('HTTP 302' in x for x in monitor.check(lambda url: items[url], self.pages)['findings']))
        def failed(url): raise urllib.error.URLError('test')
        self.assertEqual(len(monitor.check(failed, self.pages)['findings']), 4)

    def test_missing_or_duplicated_live_descriptions(self):
        items=self.responses()
        items[monitor.BASE] = (200, {}, f'<html><head><link rel="canonical" href="{monitor.BASE}"></head></html>'.encode())
        findings=monitor.check(lambda u:items[u],self.pages)['findings']
        self.assertTrue(any('missing or duplicate meta description' in line for line in findings))
        items=self.responses()
        for p in self.pages:
            items[monitor.BASE+p] = (200, {}, f'<html><head><meta name="description" content="same"><link rel="canonical" href="{monitor.BASE}{p}"></head></html>'.encode())
        findings=monitor.check(lambda u:items[u],self.pages)['findings']
        self.assertTrue(any('meta description duplicates' in line for line in findings))

    def test_xml_dtd_and_oversized_content_rejected(self):
        items = self.responses(); items[monitor.BASE + 'sitemap.xml'] = (200, {}, b'<!DOCTYPE foo><foo/>')
        self.assertIn('invalid or unsupported XML', monitor.check(lambda url: items[url], self.pages)['findings'][0])
        items = self.responses(); items[monitor.BASE] = (200, {}, b'a' * (monitor.MAX_BYTES + 1))
        self.assertTrue(any('too large' in x for x in monitor.check(lambda url: items[url], self.pages)['findings']))

    def test_generic_robots_block_and_groups(self):
        self.assertTrue(monitor.generic_root_disallow(['User-agent: *','Disallow: /']))
        self.assertTrue(monitor.generic_root_disallow(['User-agent: A','User-agent: *','Disallow: /','User-agent: B','Allow: /']))
        self.assertFalse(monitor.generic_root_disallow(['User-agent: specific','Disallow: /','User-agent: *','Allow: /']))
        self.assertFalse(monitor.generic_root_disallow(['User-agent: *','Disallow: /','Allow: /allowed']))
        items=self.responses();items[monitor.BASE+'robots.txt']=(200,{},f'Sitemap: {monitor.BASE}sitemap.xml\nUser-agent: *\nDisallow: /\n'.encode())
        self.assertTrue(any('wildcard user-agent' in f for f in monitor.check(lambda u:items[u],self.pages)['findings']))
    def test_transient_get_retried_once(self):
        response=mock.MagicMock();response.__enter__.return_value.status=200;response.__enter__.return_value.headers={};response.__enter__.return_value.read.return_value=b'ok'
        for error in (urllib.error.URLError('network'),urllib.error.HTTPError(monitor.BASE,503,'down',{},io.BytesIO(b''))):
            with self.subTest(error=error),mock.patch.object(monitor.urllib.request,'build_opener') as opener,mock.patch.object(monitor.time,'sleep') as sleep:
                opener.return_value.open.side_effect=[error,response]
                self.assertEqual(monitor.fetch(monitor.BASE)[2],b'ok');self.assertEqual(opener.return_value.open.call_count,2)
                sleep.assert_called_once_with(2)
    def test_unsafe_retries_are_never_attempted(self):
        for status,headers in ((302,{}),(403,{}),(429,{}),(503,{'Retry-After':'30'})):
            error=urllib.error.HTTPError(monitor.BASE,status,'failure',headers,io.BytesIO(b''))
            with self.subTest(status=status,headers=headers),mock.patch.object(monitor.urllib.request,'build_opener') as opener,mock.patch.object(monitor.time,'sleep') as sleep:
                opener.return_value.open.side_effect=error
                with self.assertRaises(urllib.error.HTTPError):monitor.fetch(monitor.BASE)
                self.assertEqual(opener.return_value.open.call_count,1);sleep.assert_not_called()
    def test_no_more_than_two_attempts(self):
        with mock.patch.object(monitor.urllib.request,'build_opener') as opener,mock.patch.object(monitor.time,'sleep') as sleep:
            opener.return_value.open.side_effect=urllib.error.URLError('offline')
            with self.assertRaises(urllib.error.URLError):monitor.fetch(monitor.BASE)
            self.assertEqual(opener.return_value.open.call_count,2);sleep.assert_called_once_with(2)

    def test_redirect_handler_refuses_redirect(self):
        self.assertIsNone(monitor.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com'))


if __name__ == '__main__': unittest.main()
