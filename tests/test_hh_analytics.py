import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hh_analytics', ROOT / 'scripts/hh_analytics.py')
hh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hh)


class HHAnalyticsTests(unittest.TestCase):
    def test_only_ruble_salaries_are_used_in_regional_and_overall_stats(self):
        vacancies = [
            {'id': '1', 'area': {'name': 'Сургут'}, 'salary': {'from': 100000, 'currency': 'RUR'}},
            {'id': '2', 'area': {'name': 'Сургут'}, 'salary': {'from': 1000, 'currency': 'USD'}},
        ]
        with patch.object(hh, 'fetch_hh_data', return_value=vacancies):
            result = hh.collect_analytics(['склад'], 'test.json')
        self.assertEqual(result['total_vacancies'], 2)
        self.assertEqual(result['salary_stats']['avg'], 100000)
        self.assertEqual(result['salary_sample_size'], 1)
        self.assertEqual(result['source'], 'hh.ru API')
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['avg_salary_by_region']['Сургут'], 100000)

    def test_missing_salary_is_not_zero_and_skills_do_not_overwrite_metadata(self):
        vacancies = [{'id': '1', 'key_skills': [{'name': 'total_vacancies'}], 'salary': None}]
        with patch.object(hh, 'fetch_hh_data', return_value=vacancies):
            result = hh.collect_analytics(['склад'], 'test.json')
        self.assertEqual(result['total_vacancies'], 1)
        self.assertEqual(result['salary_sample_size'], 0)
        self.assertIsNone(result['salary_stats']['avg'])
        self.assertEqual(result['top_skills'], [{'skill': 'total_vacancies', 'count': 1}])
        self.assertEqual(result['experience_distribution']['no_experience'], 0)

    def test_empty_or_failed_collection_does_not_return_a_successful_result(self):
        with patch.object(hh, 'fetch_hh_data', return_value=[]):
            with self.assertRaises(RuntimeError):
                hh.collect_analytics(['склад'], 'test.json')
        with patch.object(hh, 'fetch_hh_data', side_effect=RuntimeError('network')):
            with self.assertRaises(RuntimeError):
                hh.collect_analytics(['склад'], 'test.json')

    def test_pagination_stops_at_reported_last_page_and_rejects_partial_results(self):
        class Page:
            def __init__(self, pages):
                self.pages = pages
                self.calls = 0
            def goto(self, *args, **kwargs):
                self.calls += 1
                return types.SimpleNamespace(status=200)
            def evaluate(self, script):
                return self.pages[self.calls - 1]
        def collect(pages):
            page = Page(pages)
            browser = types.SimpleNamespace(new_context=lambda **kwargs: types.SimpleNamespace(new_page=lambda: page), close=lambda: None)
            class Playwright:
                def __enter__(self): return types.SimpleNamespace(chromium=types.SimpleNamespace(launch=lambda **kwargs: browser))
                def __exit__(self, *args): pass
            module = types.ModuleType('playwright.sync_api')
            module.sync_playwright = Playwright
            with patch.dict(sys.modules, {'playwright': types.ModuleType('playwright'), 'playwright.sync_api': module}), patch.object(hh.time, 'sleep'):
                result = hh.fetch_hh_data('склад')
            return page.calls, result
        calls, result = collect([{'pages': 2, 'items': [{'id': '1'}]}, {'pages': 2, 'items': [{'id': '2'}]}])
        self.assertEqual(calls, 2)
        self.assertEqual(len(result), 2)
        with self.assertRaises(RuntimeError):
            collect([{'pages': 2, 'items': [{'id': '1'}]}, {'pages': 2, 'items': []}])

    def test_second_collection_failure_preserves_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / 'data'
            data.mkdir()
            (data / 'hh_warehouse.json').write_text('old warehouse')
            (data / 'hh_transport.json').write_text('old transport')
            import os
            old = os.getcwd()
            try:
                os.chdir(directory)
                with patch.object(hh, 'collect_analytics', side_effect=[{'total_vacancies': 1}, RuntimeError('failed')]):
                    with self.assertRaises(RuntimeError):
                        hh.main()
                self.assertEqual((data / 'hh_warehouse.json').read_text(), 'old warehouse')
                self.assertEqual((data / 'hh_transport.json').read_text(), 'old transport')
            finally:
                os.chdir(old)


if __name__ == '__main__':
    unittest.main()
