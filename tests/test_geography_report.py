import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import geography_report as geo


class GeographyTests(unittest.TestCase):
    def test_supported_exports_and_no_file_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'countries.csv'
            path.write_text('Страна,Клики,Показы,CTR\nРоссия,7,100,7%\nГермания,2,20,10%\n', encoding='utf-8')
            before = path.read_bytes()
            result = geo.read_export(path)
            self.assertEqual((result['clicks'], result['impressions']), (9, 120))
            self.assertEqual(result['countries'][0]['country'], 'Россия')
            self.assertEqual(before, path.read_bytes())
            path.write_text('Country,Clicks,Impressions\nFrance,0,8\n', encoding='utf-8')
            self.assertEqual(geo.read_export(path)['countries'][0]['country'], 'France')

    def test_rejects_query_exports_bad_numbers_and_duplicate_labels(self):
        examples = ['Query,Clicks,Impressions\nfoo,1,2\n',
                    'Country,Clicks,Impressions\nhttps://x,1,2\n',
                    'Country,Clicks,Impressions\nFrance,-1,2\n',
                    'Country,Clicks,Impressions\nFrance,1,2\nfrance,1,2\n',
                    'Country,Clicks,Clicks,Impressions\nFrance,1,1,2\n']
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input.csv'
            for data in examples:
                path.write_text(data, encoding='utf-8')
                with self.subTest(data=data), self.assertRaises(ValueError): geo.read_export(path)

    def test_cli_requires_valid_ordered_period(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'countries.csv'
            path.write_text('Country,Clicks,Impressions\nFrance,1,2\n')
            cmd = [sys.executable, str(ROOT / 'scripts/geography_report.py'), str(path), '--start', '2026-01-01', '--end', '2026-01-31']
            result = subprocess.run(cmd, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['summary']['impressions'], 2)
            result = subprocess.run(cmd[:-1] + ['2025-01-01'], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__': unittest.main()
