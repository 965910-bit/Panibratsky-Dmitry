import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class NewsTests(unittest.TestCase):
    def test_merge_preserves_existing_deduplicates_and_sorts_chronologically(self):
        module = load('news_utils')
        now = datetime(2026, 11, 16, tzinfo=timezone.utc)
        existing = [{'link': 'https://example.com/old', 'pubDate': 'Sun, 15 Nov 2026 00:00:00 +0000', 'dead': True},
                    {'link': 'https://example.com/expired', 'pubDate': 'Thu, 01 Oct 2026 00:00:00 +0000'},
                    {'link': 'https://example.com/undated', 'pubDate': 'bad'}]
        incoming = [{'link': 'https://example.com/new', 'pubDate': 'Mon, 16 Nov 2026 00:00:00 +0000'},
                    {'link': 'https://example.com/old', 'pubDate': 'Mon, 16 Nov 2026 00:00:00 +0000'},
                    {'link': 'javascript:alert(1)', 'pubDate': ''}]
        result = module.merge_news(existing, incoming, now=now)
        self.assertEqual([x['link'] for x in result], ['https://example.com/new', 'https://example.com/old', 'https://example.com/undated'])
        self.assertTrue(result[1]['dead'])

    def test_static_snapshot_escapes_data_and_skips_unsafe_urls(self):
        module = load('generate_news_pages')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'data').mkdir()
            (root / 'trends.html').write_text('<div><!-- NEWS_SNAPSHOT_START --><!-- NEWS_SNAPSHOT_END --></div>')
            news = [{'link': 'https://example.com/?a=1&b=2', 'title': '<img onerror="bad">', 'description': 'a & b'},
                    {'link': 'javascript:alert(1)', 'title': 'bad'},
                    {'link': 'https://example.com/?a=1&b=2', 'title': 'duplicate'}]
            (root / 'data/news.json').write_text(json.dumps(news), encoding='utf-8')
            module.ROOT = root
            module.generate()
            result = (root / 'trends.html').read_text(encoding='utf-8')
            self.assertIn('&lt;img', result)
            self.assertIn('a=1&amp;b=2', result)
            self.assertNotIn('javascript:', result)
            self.assertNotIn('duplicate', result)
            module.generate()
            self.assertEqual(result, (root / 'trends.html').read_text(encoding='utf-8'))

if __name__ == '__main__':
    unittest.main()
