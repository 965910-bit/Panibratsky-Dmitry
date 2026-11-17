import json
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
                f'<html><head><link rel="canonical" href="{monitor.BASE}{p}"><script type="application/ld+json">{{"@type":"WebPage"}}</script></head></html>'.encode())
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

    def test_xml_dtd_and_oversized_content_rejected(self):
        items = self.responses(); items[monitor.BASE + 'sitemap.xml'] = (200, {}, b'<!DOCTYPE foo><foo/>')
        self.assertIn('invalid or unsupported XML', monitor.check(lambda url: items[url], self.pages)['findings'][0])
        items = self.responses(); items[monitor.BASE] = (200, {}, b'a' * (monitor.MAX_BYTES + 1))
        self.assertTrue(any('too large' in x for x in monitor.check(lambda url: items[url], self.pages)['findings']))

    def test_redirect_handler_refuses_redirect(self):
        self.assertIsNone(monitor.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com'))


if __name__ == '__main__': unittest.main()
