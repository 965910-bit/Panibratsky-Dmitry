"""Offline smoke of actual locked news parsers, without external sources or mail."""
from datetime import datetime
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT))
try:
    import bs4  # noqa: F401
    import requests  # noqa: F401
except ImportError:
    bs4 = None


@unittest.skipIf(bs4 is None, 'install requirements/news.lock for real parser smoke')
class RealNewsParserTests(unittest.TestCase):
    def test_paused_sitemap_parser_extracts_fixture_without_network(self):
        import fetch_news
        now = datetime.now()
        ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
        sitemap = f'https://example.com/sitemap-{now.month:02d}-{now.year}.xml'
        index = f'<sitemapindex xmlns="{ns}"><sitemap><loc>{sitemap}</loc></sitemap></sitemapindex>'
        entries = f'<urlset xmlns="{ns}"><url><loc>https://example.com/news/1</loc></url></urlset>'
        page = '<html><head><meta name="description" content="Обзор поставок"></head><body><h1>Склад &amp; транспорт</h1><time datetime="2026-01-02">Дата</time></body></html>'
        class Response:
            def __init__(self, content): self.content, self.text = content.encode(), content
            def raise_for_status(self): pass
        def get(url, **kwargs):
            return Response(index if url.endswith('/sitemap.xml') else entries if url == sitemap else page)
        source = {'name': 'Fixture', 'url': 'https://example.com/sitemap.xml', 'lang': 'ru', 'cat': 'test'}
        with patch.object(fetch_news.requests, 'get', side_effect=get):
            result = fetch_news.fetch_from_sitemap(source)
        self.assertEqual(result[0]['title'], 'Склад & транспорт')
        self.assertEqual(result[0]['pubDate'], '2026-01-02')
        self.assertEqual(result[0]['description'], 'Обзор поставок')
        self.assertEqual(fetch_news.SOURCES, [])

    def test_google_alert_html_fixture_uses_real_parser_without_mail(self):
        from collectors.google_alerts import GoogleAlertsCollector
        collector = GoogleAlertsCollector('unused', 'unused')
        body = '<a href="https://example.org/news/item?x=1&amp;y=2">Новость</a>'
        self.assertIn('https://example.org/news/item?x=1&y=2', collector._extract_links(body))


if __name__ == '__main__':
    unittest.main()
