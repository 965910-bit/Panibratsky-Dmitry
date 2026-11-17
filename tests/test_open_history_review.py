import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import open_history_review as review
import open_logistics_data as collector


class HistoryReviewTests(unittest.TestCase):
    def test_states_and_absence_are_explicit(self):
        result = review.compare({'2010': 2.1, '2012': 2.4, '2018': 2.7},
                                {'2010': 2.2, '2018': 2.7, '2022': 2.6})
        self.assertEqual([row['status'] for row in result], ['revised', 'removed', 'unchanged', 'added'])
        self.assertIsNone(result[1]['current'])

    def test_real_bundle_and_absent_history(self):
        archive = next((ROOT / 'data/open-logistics-archives').iterdir())
        timestamp, values = review.history(archive)
        self.assertIsNotNone(timestamp.utcoffset())
        self.assertEqual(values['2022'], 2.6)
        with tempfile.TemporaryDirectory() as tmp:
            report = review.report(archive, tmp)
            self.assertIsNone(report['baseline'])
            self.assertEqual(report['records'], [])

    def test_earlier_vintage_selected_and_corruption_rejected(self):
        archive = next((ROOT / 'data/open-logistics-archives').iterdir())
        originals = {url: (archive / (key + '.json')).read_bytes() for key, url in collector.SOURCES.items()}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = json.loads(originals[collector.WORLD_BANK])
            for row in data[1]:
                if row['date'] == '2018': row['value'] = 2.5
            prior = dict(originals, **{collector.WORLD_BANK: json.dumps(data).encode()})
            result = collector.collect(lambda url: json.loads(prior[url]))
            collector.archive_capture(prior, result, root, datetime(2026, 11, 1, tzinfo=timezone.utc))
            report = review.report(archive, root)
            year = next(item for item in report['records'] if item['period'] == '2018')
            self.assertEqual((year['previous'], year['current'], year['status']), (2.5, 2.76, 'revised'))
            (next(root.iterdir()) / 'world_bank.json').write_bytes(b'damaged')
            with self.assertRaises(ValueError): review.report(archive, root)


if __name__ == '__main__':
    unittest.main()
