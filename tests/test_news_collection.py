import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch, mock_open

ROOT = Path(__file__).resolve().parents[1]


def load_collector():
    spec = importlib.util.spec_from_file_location('news_utils', ROOT / 'scripts/news_utils.py')
    utils = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(utils)
    spec = importlib.util.spec_from_file_location('fetch_news', ROOT / 'scripts/fetch_news.py')
    collector = importlib.util.module_from_spec(spec)
    requests = types.ModuleType('requests')
    bs4 = types.ModuleType('bs4')
    bs4.BeautifulSoup = lambda *args: None
    with patch.dict(sys.modules, {'requests': requests, 'bs4': bs4, 'news_utils': utils}):
        spec.loader.exec_module(collector)
    return collector


class NewsCollectionTests(unittest.TestCase):
    def test_restricted_source_is_not_scheduled_for_collection(self):
        module = load_collector()
        self.assertEqual(module.SOURCES, [])

    def test_all_sources_unavailable_fails_without_touching_feed(self):
        module = load_collector()
        with tempfile.TemporaryDirectory() as folder:
            news = Path(folder) / 'news.json'
            original = '[{"link":"https://example.com/a","title":"old"}]'
            news.write_text(original)
            with patch.object(module, 'SOURCES', [{'name':'fixture', 'url':'https://example.org/map', 'type':'sitemap'}]), patch.object(module, 'fetch_rss', return_value=None), patch.object(module, 'fetch_from_sitemap', return_value=None), patch.object(module, 'load_google_alerts') as alerts:
                with self.assertRaisesRegex(RuntimeError, 'источники недоступны'):
                    module.main(str(news))
                alerts.assert_not_called()
            self.assertEqual(news.read_text(), original)

    def test_paused_sources_preserve_existing_feed_without_network_or_alerts(self):
        module = load_collector()
        with tempfile.TemporaryDirectory() as folder:
            news = Path(folder) / 'news.json'
            original = '[{"link":"https://example.com/old","title":"old"}]'
            news.write_text(original)
            with patch.object(module, 'fetch_rss') as rss, patch.object(module, 'fetch_from_sitemap') as sitemap, patch.object(module, 'load_google_alerts') as alerts, patch('builtins.print') as output:
                module.main(str(news))
                rss.assert_not_called()
                sitemap.assert_not_called()
                alerts.assert_not_called()
                self.assertTrue(any('лента не обновлялась' in str(call) for call in output.call_args_list))
            self.assertEqual(news.read_text(), original)

    def test_scheduled_workflow_does_not_invoke_paused_optional_collectors(self):
        workflow = (ROOT / '.github/workflows/update_news.yml').read_text(encoding='utf-8')
        for entry in ('ATIStatsCollector', 'collectors.ati_stats',
                      'GovRuCollector', 'collectors.gov_ru', 'data/gov_news.json'):
            self.assertNotIn(entry, workflow)

    def test_partial_failure_keeps_successful_items_and_warns(self):
        module = load_collector()
        item = {'link': 'https://example.com/new', 'title': 'new', 'pubDate': ''}
        with tempfile.TemporaryDirectory() as folder:
            news = Path(folder) / 'news.json'
            news.write_text('[]')
            with patch.object(module, 'SOURCES', [{'name':'fixture RSS', 'url':'https://example.org/feed', 'type':'rss'}, {'name':'fixture sitemap', 'url':'https://example.org/map', 'type':'sitemap'}]), patch.object(module, 'fetch_rss', return_value=[item]), patch.object(module, 'fetch_from_sitemap', return_value=None), patch.object(module, 'load_google_alerts', return_value=[]), patch('builtins.print') as output:
                module.main(str(news))
            self.assertEqual(json.loads(news.read_text())[0]['link'], item['link'])
            self.assertTrue(any('::warning::' in str(call) for call in output.call_args_list))

    def test_empty_success_is_not_an_outage(self):
        module = load_collector()
        with tempfile.TemporaryDirectory() as folder:
            news = Path(folder) / 'news.json'
            original = '[{"link":"https://example.com/a","title":"old"}]'
            news.write_text(original)
            with patch.object(module, 'SOURCES', [{'name':'fixture RSS', 'url':'https://example.org/feed', 'type':'rss'}, {'name':'fixture sitemap', 'url':'https://example.org/map', 'type':'sitemap'}]), patch.object(module, 'fetch_rss', return_value=[]), patch.object(module, 'fetch_from_sitemap', return_value=None), patch.object(module, 'load_google_alerts', return_value=[]):
                module.main(str(news))
            self.assertEqual(news.read_text(), original)

    def test_alert_email_date_is_not_claimed_as_publication_date(self):
        module = load_collector()
        data = {'alerts': [{'link': 'https://example.com/news', 'subject': 'Новость', 'keyword': 'склад', 'date': '2026-11-16T10:00:00Z'}]}
        with patch.object(module.os.path, 'exists', return_value=True), patch('builtins.open', mock_open(read_data=json.dumps(data))):
            result = module.load_google_alerts(set())
        self.assertEqual(result[0]['pubDate'], '')

    def test_invalid_rss_is_a_failure_but_empty_channel_is_success(self):
        module = load_collector()
        source = {'name': 'Test', 'url': 'https://example.com/feed', 'lang': 'ru', 'cat': 'test'}
        class Response:
            def __init__(self, content): self.content = content
            def raise_for_status(self): pass
        with patch.object(module.requests, 'get', create=True, return_value=Response(b'<invalid/>')):
            self.assertIsNone(module.fetch_rss(source))
        with patch.object(module.requests, 'get', create=True, return_value=Response(b'<rss><channel/></rss>')):
            self.assertEqual(module.fetch_rss(source), [])

    def test_undated_articles_expire_by_collection_time_but_keep_publication_date_empty(self):
        module = load_collector()
        items = [
            {'link': 'https://example.com/old', 'pubDate': '', 'collected_at': '2026-10-01T00:00:00+00:00'},
            {'link': 'https://example.com/new', 'pubDate': '', 'collected_at': '2026-11-15T00:00:00+00:00'},
            {'link': 'https://example.com/legacy', 'pubDate': ''},
        ]
        result = module.merge_news([], items, now=datetime(2026, 11, 16, tzinfo=timezone.utc))
        self.assertEqual([i['link'] for i in result], ['https://example.com/new', 'https://example.com/legacy'])
        self.assertEqual(result[0]['pubDate'], '')

    def test_sitemap_article_without_publication_date_is_not_given_collection_date(self):
        module = load_collector()
        date = datetime.now()
        ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
        sitemap = f'https://example.com/sitemap-{date.month:02d}-{date.year}.xml'
        index = f'<sitemapindex xmlns="{ns}"><sitemap><loc>{sitemap}</loc></sitemap></sitemapindex>'
        entries = f'<urlset xmlns="{ns}"><url><loc>https://example.com/news/1</loc></url></urlset>'
        class Response:
            def __init__(self, content): self.content = content.encode(); self.text = content
            def raise_for_status(self): pass
        def get(url, **kwargs):
            return Response(index if url.endswith('/sitemap.xml') else entries if url == sitemap else '<html/>')
        class Soup:
            def find(self, tag=None, *args, **kwargs):
                if tag == 'h1': return types.SimpleNamespace(text='Новость')
                return None
        source = {'name': 'Test', 'url': 'https://example.com/sitemap.xml', 'lang': 'ru', 'cat': 'test'}
        with patch.object(module.requests, 'get', create=True, side_effect=get), patch.object(module, 'BeautifulSoup', return_value=Soup()):
            result = module.fetch_from_sitemap(source)
        self.assertEqual(result[0]['pubDate'], '')
        self.assertTrue(result[0]['collected_at'])

    def test_iso_news_dates_sort_and_rss_dates_are_valid(self):
        module = load_collector()
        date = module.merge_news([], [{'link': 'https://example.com/a', 'pubDate': '2026-11-15T12:00:00+03:00'}], now=datetime(2026, 11, 16, tzinfo=timezone.utc))
        self.assertEqual(len(date), 1)
        spec = importlib.util.spec_from_file_location('generate_rss', ROOT / 'scripts/generate_rss.py')
        rss = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rss)
        self.assertEqual(rss.rss_date('2026-11-15T12:00:00+03:00'), 'Sun, 15 Nov 2026 09:00:00 +0000')
        self.assertIsNone(rss.rss_date(''))
        self.assertIsNone(rss.rss_date('not a date'))


if __name__ == '__main__':
    unittest.main()
