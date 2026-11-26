import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/check_news_outputs.py'


class NewsOutputConsistencyTests(unittest.TestCase):
    def run_check(self, root):
        return subprocess.run([sys.executable, str(SCRIPT), '--root', str(root)],
                              capture_output=True, text=True)

    def test_detects_stale_outputs_without_modifying_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data').mkdir()
            (root / 'data/news.json').write_text(json.dumps([{
                'title': 'First item', 'link': 'https://example.org/one',
                'description': 'Example', 'pubDate': '2026-01-01T00:00:00Z'
            }]))
            (root / 'trends.html').write_text('<html><!-- NEWS_SNAPSHOT_START --><!-- NEWS_SNAPSHOT_END --></html>')
            (root / 'rss.xml').write_text('<rss/>')
            result = self.run_check(root)
            self.assertEqual(1, result.returncode)
            self.assertIn('trends.html', result.stderr)
            self.assertIn('rss.xml', result.stderr)
            self.assertEqual('<rss/>', (root / 'rss.xml').read_text())
            subprocess.run([sys.executable, '-c',
                            'import sys; from pathlib import Path; '
                            'sys.path.insert(0, sys.argv[1]); '
                            'import generate_news_pages as p, generate_rss as r; '
                            'p.ROOT = r.ROOT = Path(sys.argv[2]); p.generate(); r.generate_rss()',
                            str(ROOT / 'scripts'), str(root)], check=True)
            before = {name: (root / name).read_bytes() for name in ('data/news.json', 'trends.html', 'rss.xml')}
            self.assertEqual(0, self.run_check(root).returncode)
            self.assertEqual(before, {name: (root / name).read_bytes() for name in before})
            (root / 'data/news.json').write_text('[]')
            result = self.run_check(root)
            self.assertEqual(1, result.returncode)
            self.assertIn('rss.xml', result.stderr)
            self.assertIn('trends.html', result.stderr)

    def test_invalid_input_fails_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'data').mkdir()
            (root / 'data/news.json').write_text('{invalid')
            (root / 'rss.xml').write_text('<rss/>')
            (root / 'trends.html').write_text('<!-- NEWS_SNAPSHOT_START --><!-- NEWS_SNAPSHOT_END -->')
            result = self.run_check(root)
            self.assertEqual(1, result.returncode)
            self.assertIn('News output check failed', result.stderr)
            self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
