import importlib.util
import contextlib
import io
import os
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

    def test_failure_annotation_is_bounded_and_never_includes_raw_exceptions(self):
        failure = hh.HHCollectionError('http_error', page=2, status=403)
        self.assertEqual(hh.failure_annotation(failure), '::error title=HH analytics::reason=http_error page=2 http=403')
        self.assertEqual(hh.failure_annotation(RuntimeError('secret\n::error::unsafe')), '::error title=HH analytics::reason=other_error')
        with patch.object(hh, 'main', side_effect=failure), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(hh.cli(), 1)
        self.assertIn('reason=http_error page=2 http=403', out.getvalue())
        self.assertNotIn('secret', out.getvalue())

    def test_api_error_classification_is_allowlisted_and_never_exposes_body(self):
        def response(body): return types.SimpleNamespace(body=lambda: body)
        for error in ('captcha_required', 'bad_authorization', 'token_expired', 'api_access_payment'):
            payload = json.dumps({'errors': [{'type': error, 'value': 'secret', 'captcha_url': 'https://secret.invalid'}]}).encode()
            category = hh.classify_api_error(response(payload))
            self.assertEqual(category, error)
            annotation = hh.failure_annotation(hh.HHCollectionError('http_error', 1, 403, category))
            self.assertIn('api_error=' + error, annotation)
            self.assertNotIn('secret', annotation)
        for body in (b'not json', b'{"errors":[{"type":"secret"}]}', b'[]', b'x' * 16385):
            self.assertIsNone(hh.classify_api_error(response(body)))
        self.assertNotIn('secret', hh.failure_annotation(hh.HHCollectionError('http_error', 1, 403, 'secret')))
        self.assertIsNone(hh.classify_api_error(types.SimpleNamespace(body=lambda: 1 / 0)))

    def test_diagnostic_mode_does_not_write_data_even_if_collection_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'data').mkdir()
            for name in ('hh_warehouse.json','hh_transport.json'):
                (root/'data'/name).write_text('old',encoding='utf8')
            old=os.getcwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ, {'HH_DIAGNOSTIC_ONLY':'1'}), patch.object(hh,'collect_analytics',return_value={'total_vacancies':1}):
                    hh.main()
                self.assertEqual((root/'data'/'hh_warehouse.json').read_text(),'old')
                self.assertEqual((root/'data'/'hh_transport.json').read_text(),'old')
                self.assertEqual(sorted(p.name for p in (root/'data').iterdir()), ['hh_transport.json','hh_warehouse.json'])
            finally:
                os.chdir(old)

    def test_http_failure_is_reported_without_response_body_or_partial_success(self):
        class BrowserPage:
            def goto(self, *args, **kwargs): return types.SimpleNamespace(status=403, body=lambda: b'{"errors":[{"type":"captcha_required","captcha_url":"https://secret.invalid"}]}')
        browser=types.SimpleNamespace(new_context=lambda **kwargs: types.SimpleNamespace(new_page=lambda: BrowserPage()),close=lambda:None)
        class Playwright:
            def __enter__(self): return types.SimpleNamespace(chromium=types.SimpleNamespace(launch=lambda **kwargs: browser))
            def __exit__(self,*args): pass
        module=types.ModuleType('playwright.sync_api'); module.sync_playwright=Playwright
        with patch.dict(sys.modules, {'playwright':types.ModuleType('playwright'),'playwright.sync_api':module}):
            with self.assertRaises(hh.HHCollectionError) as caught:
                hh.fetch_hh_data('do not include this text')
        self.assertEqual(hh.failure_annotation(caught.exception),'::error title=HH analytics::reason=http_error page=1 http=403 api_error=captcha_required')

    def test_workflow_restricts_writes_to_main_and_non_main_is_diagnostic(self):
        workflow=(ROOT/'.github/workflows/hh_analytics.yml').read_text(encoding='utf-8')
        self.assertIn("HH_DIAGNOSTIC_ONLY: ${{ github.ref != 'refs/heads/main' && '1' || '0' }}",workflow)
        self.assertIn("if: github.ref == 'refs/heads/main'",workflow)
        self.assertIn("persist-credentials: ${{ github.ref == 'refs/heads/main' }}",workflow)
        self.assertIn("format('hh-diagnostic-{0}', github.ref)",workflow)

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
