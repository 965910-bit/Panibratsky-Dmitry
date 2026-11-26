import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class PublicationRecoveryTests(unittest.TestCase):
    def test_recovery_is_only_after_failed_publication_and_does_not_expose_private_scratch(self):
        paths = [
            ('update_news.yml', 'publish_news', 'news-publication-failed',
             {'data/news.json', 'trends.html', 'sitemap.xml', 'rss.xml'}),
            ('open_logistics_data.yml', 'publish_indicators', 'open-data-publication-failed',
             {'data/open-logistics.json', 'data/open-logistics-archives/'}),
        ]
        for file, step, name, expected in paths:
            with self.subTest(file=file):
                text = (ROOT / '.github/workflows' / file).read_text()
                self.assertIn(f'id: {step}', text)
                self.assertIn(f"if: ${{{{ failure() && steps.{step}.outcome == 'failure' }}}}", text)
                part = text[text.index(f'name: {name}'):]
                self.assertIn('retention-days: 7', part)
                self.assertIn('if-no-files-found: warn', part)
                block = re.search(r'path: \|\n((?:            [^\n]+\n)+)', part)
                self.assertIsNotNone(block)
                self.assertEqual({line.strip() for line in block.group(1).splitlines()}, expected)
                self.assertNotIn('.local-news', part)
                self.assertNotIn('google_alerts', part)
                self.assertNotIn('continue-on-error: true', part)

if __name__ == '__main__': unittest.main()
