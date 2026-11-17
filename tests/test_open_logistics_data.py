import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('open_logistics_data', ROOT / 'scripts/open_logistics_data.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def bank():
    def row(year, value):
        return {'date': year, 'value': value, 'countryiso3code': 'RUS', 'indicator': {'id': 'LP.LPI.OVRL.XQ'}}
    return [{'pages': 1, 'lastupdated': '2026-11-11'}, [row('2025', None), row('2018', 2.76), row('2022', 2.6)]]


def euro():
    dimensions = {key: {'category': {'index': {value: 0}}} for key, value in {
        'freq': 'A', 'tra_type': 'TOTAL', 'tra_oper': 'TOTAL', 'unit': 'THS_T', 'geo': 'DE', 'time': '2025'}.items()}
    return {'class': 'dataset', 'extension': {'id': 'ROAD_GO_TA_TOTT'},
            'id': list(dimensions), 'size': [1] * 6, 'dimension': dimensions,
            'value': {'0': 2804335}, 'updated': '2026-07-30T23:00:00+0200'}


class OpenLogisticsTests(unittest.TestCase):
    def test_valid_results_use_latest_real_observation(self):
        wb = module.parse_world_bank(bank())
        self.assertEqual((wb['period'], wb['value']), ('2022', 2.6))
        result = module.parse_eurostat(euro())
        self.assertEqual((result['period'], result['value'], result['status']), ('2025', 2804335, None))
        flagged = euro(); flagged['status'] = {'0': 'p'}
        self.assertEqual(module.parse_eurostat(flagged)['status'], 'p')

    def test_unexpected_shapes_or_values_are_rejected(self):
        wrong = bank(); wrong[1][0]['countryiso3code'] = 'USA'
        with self.assertRaises(ValueError): module.parse_world_bank(wrong)
        wrong = bank(); wrong[0]['pages'] = 2
        with self.assertRaises(ValueError): module.parse_world_bank(wrong)
        wrong = bank(); wrong[1][2]['value'] = float('nan')
        with self.assertRaises(ValueError): module.parse_world_bank(wrong)
        wrong = euro(); wrong['dimension']['geo']['category']['index'] = {'FR': 0}
        with self.assertRaises(ValueError): module.parse_eurostat(wrong)
        wrong = euro(); wrong['value'] = {}
        with self.assertRaises(ValueError): module.parse_eurostat(wrong)
        wrong = euro(); wrong['size'] = [1, 1, 1, 1, 1, 2]
        with self.assertRaises(ValueError): module.parse_eurostat(wrong)

    def test_failure_before_save_preserves_snapshot_and_check_is_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'snapshot.json'; target.write_text('old', encoding='utf-8')
            with self.assertRaises(ValueError):
                module.collect(lambda url: bank() if url == module.WORLD_BANK else {})
            self.assertEqual(target.read_text(), 'old')
            with patch.object(module, 'collect', return_value={'test': 1}), patch.object(module, 'save') as save:
                with patch('sys.argv', ['script', '--check']): self.assertEqual(module.main(), 0)
                save.assert_not_called()

    def test_snapshot_only_changes_when_observations_change(self):
        result = module.collect(lambda url: bank() if url == module.WORLD_BANK else euro())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'snapshot.json'
            self.assertTrue(module.save(result, target, datetime(2026, 11, 17, tzinfo=timezone.utc)))
            before = target.read_bytes()
            self.assertFalse(module.save(result, target, datetime(2026, 12, 1, tzinfo=timezone.utc)))
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(json.loads(before)['saved_on'], '2026-11-17')

    def test_fetch_is_bounded_and_never_follows_redirects(self):
        redirect = module.NoRedirect()
        self.assertIsNone(redirect.redirect_request(None, None, 302, '', {}, 'https://example.com'))

        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, size):
                self.size = size
                return b'x' * size
        response = Response()
        with patch.object(module, 'build_opener') as opener:
            opener.return_value.open.return_value = response
            with self.assertRaises(ValueError): module.fetch_json(module.WORLD_BANK)
            self.assertEqual(response.size, module.MAX_BYTES + 1)
            args, kwargs = opener.return_value.open.call_args
            self.assertEqual(args[0].full_url, module.WORLD_BANK)
            self.assertEqual(kwargs['timeout'], 20)

    def test_workflow_scopes_writes_and_paused_news_remains_paused(self):
        workflow = (ROOT / '.github/workflows/open_logistics_data.yml').read_text()
        self.assertIn('python scripts/open_logistics_data.py --check', workflow)
        self.assertIn('git add data/open-logistics.json', workflow)
        self.assertIn("if: github.ref == 'refs/heads/main'", workflow)
        self.assertNotIn('telegram', workflow.lower())
        self.assertIn('SOURCES = []', (ROOT / 'scripts/fetch_news.py').read_text())


if __name__ == '__main__': unittest.main()
